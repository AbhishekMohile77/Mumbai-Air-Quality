import logging
from datetime import datetime, timezone

import pandas as pd
import requests
from sqlalchemy.dialects.mysql import insert

from config import OPENAQ_API_KEY
from database import SessionLocal
from models import (DimLocation, DimParameter, DimSensor, DimDate)


# _____Configuration_____

BASE_URL = "https://api.openaq.org/v3"

POLLUTANTS = {"pm25", "pm10", "no2", "o3", "so2", "co"}

# multiple centres give us better coverage for mumbai metroplotan region
# OpenAQ limits point/radius searches to 25km
SEACRH_CENTRES = [
    ("Mumbai", 19.0760, 72.8777),
    ("Thane", 19.2183, 72.9781),
    ("Navi Mumbai", 19.0330, 73.0297),
    ("Kalyan", 19.2403, 73.1305),
    ("Vasai-Virar", 19.3919, 72.8397),
    ("Panvel", 18.9894, 73.1175)
]

SEARCH_RADIUS_METERS = 25_000
PAGE_SIZE = 1000


# _____Logging_____

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)



# _____API helper______

"""
get_locations() to retirive all OpenAQ locations within the search radius

Pagination is handles so rest of ETL can work with a single list of locations
"""

def get_locations(
    session: requests.Session,
    latitude: float,
    longitude: float
) -> list[dict]:
    locations = []
    page = 1

    while True:
        params = {
            "coordinates": f"{latitude}, {longitude}",
            "radius": SEARCH_RADIUS_METERS,
            "iso": "IN",
            "limit": PAGE_SIZE,
            "page": page
        }

        response = session.get(
            f"{BASE_URL}/locations",
            headers={"X-API-Key": OPENAQ_API_KEY},
            params=params,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()
        results = data.get("results", [])

        locations.extend(results)

        logger.info(
            "Location search %.4f, %.4f | page %s | received %s",
            latitude,
            longitude,
            page,
            len(results)
        )

        if len(results) < PAGE_SIZE:
            break

        page +=1

    return locations


# _____Location transformation______

def build_location_rows(locations: list[dict]) -> list[dict]:
    """
    convert OpenAQ location responses to dim_location rows
    locality from OpenAQ can null, so we use MMR as safe fallback
    """

    rows = []

    for location in locations:
        coordinates = location.get("coordinates") or {}

        latitude = coordinates.get("latitude")
        longitude = coordinates.get("longitude")

        if latitude is None or longitude is None:
            continue

        country = location.get("country") or {}
        provider = location.get("provider") or {}

        city = location.get("locality") or "Mumbai Metropolitan Region"

        rows.append(
            {
                "location_id": location["id"],
                "name": location.get("name") or "Unknown",
                "city": city,
                "country": country.get("name"),
                "latitude":latitude,
                "longitude": longitude,
                "provider": provider.get("name")
            }
        )
    return rows



# ______parameter and sensor transformation_______
def build_parameter_and_sensor_rows(locations: list[dict]) -> tuple[list[dict], list[dict]]:
    # Extract pollutant parameters and sensors directly from nested structure returned by /locations

    parameters = {}
    sensors = {}

    for location in locations:
        location_id = location["id"]

        for sensor in location.get("sensors", []):
            parameter = sensor.get("parameter") or {}

            parameter_name = parameter.get("name")

            if parameter_name not in POLLUTANTS:
                continue

            parameter_id = parameter.get("id")

            if parameter_id is None:
                continue

            parameters[parameter_id] = {
                "parameter_id": parameter_id,
                "name": parameter_name,
                "display_name": parameter.get("displayName") or parameter_name.upper(),
                "unit": parameter.get("units")
            }

            sensors[sensor["id"]] = {
                "sensor_id": sensor["id"],
                "location_id": location_id,
                "parameter_id": parameter_id
            }

    return list(parameters.values()), list(sensors.values())


# ______Databse upserts______

def upsert_rows(db, model, rows:list[dict], primary_key: str) -> None:
    # insert rows and update existing rows if primary key exists

    if not rows:
        return

    table = model.__table__

    statement = insert(table).values(rows)

    update_columns = {
        column.name: statement.inserted[column.name]
        for column in table.columns
        if column.name != primary_key
    }

    statement = statement.on_duplicate_key_update(**update_columns)

    db.execute(statement)



# ______Date dimension_______
def build_date_dimension(locations: list[dict]) -> list[dict]:
    # Generate dates from the earliest OpenAQ location timestamp through today's UTC date.

    first_dates = []

    for location in locations:
        datetime_first = location.get("datetimeFirst")

        if datetime_first and datetime_first.get("utc"):
            timestamp = pd.to_datetime(
                datetime_first["utc"],
                utc=True
            )

            first_dates.append(timestamp.date())

    today = datetime.now(timezone.utc).date()


    if first_dates:
        start_date = min(first_dates)
    else:
        start_date = today

    dates = pd.date_range(
        start=start_date,
        end=today,
        freq="D"
    )    

    rows = []

    for current_date in dates:
        date_value = current_date.date()

        rows.append(
            {
                "date_id": int(date_value.strftime("%Y%m%d")),
                "date": date_value,
                "year": date_value.year,
                "month": date_value.month,
                "month_name": date_value.strftime("%B"),
                "weekday": date_value.strftime("%A"),
                "is_weekend": date_value.weekday()>=5,
            }
        )

    return rows


# _____Main ETL_____

def main() -> None:
    logger.info("Starting dimension load")

    all_locations = []

    with requests.Session() as api_session:
        for centre_name, latitude, longitude in SEACRH_CENTRES:
            logger.info(
                "Searching OpenAQ around %s",
                centre_name
            )

        locations = get_locations(
            api_session,
            latitude,
            longitude
        )

        all_locations.extend(locations)

    logger.info(
        "Locations returned across all seacrhes: %s",
        len(all_locations)
    )

    # the same station cal fall within multiple 25km search circles hence openAQ location ID is identifier
    unique_locations = {
        location["id"]: location for location in all_locations
    }

    locations = list(unique_locations.values())

    logger.info(
        "unique locations after deduplication: %s",
        len(locations)
    )

    location_rows = build_location_rows(locations)

    parameter_rows, sensor_rows = build_parameter_and_sensor_rows(locations)

    date_rows = build_date_dimension(locations)

    logger.info("Locations to load: %s", len(location_rows))

    logger.info("Parameters to load: %s", len(parameter_rows))

    logger.info("Sensors to load: %s", len(sensor_rows))

    logger.info("Dates to load: %s", len(date_rows))




    with SessionLocal() as db:
        upsert_rows(
            db, DimLocation, location_rows, "location_id"
        )

        upsert_rows(
            db, DimParameter, parameter_rows, "parameter_id"
        )

        upsert_rows(
            db, DimSensor, sensor_rows, "sensor_id"
        )

        upsert_rows(
            db, DimDate, date_rows, "date_id"
        )

        db.commit()

    logger.info("dimension load finished successfully")


if __name__ == "__main__":
    main()