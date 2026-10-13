import argparse
import logging
import random
import time
from datetime import datetime, timedelta, timezone

import requests
from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert

from config import OPENAQ_API_KEY
from database import SessionLocal
from models import DimSensor, FactMeasurement


# Configuration

BASE_URL="https://api.openaq.org/v3"

DEFAULT_BACKFILL_DAYS = 60
PAGE_SIZE = 1000
BATCH_SIZE = 500

REQUEST_TIMEOUT = 30

REQUEST_SLEEP_SECONDS = 1.0 # beloew OpenAQ rate limit

MAX_RETRIES = 5

POLLUTANTS = {
    "pm25", "pm10", "no2", "o3", "so2", "co"
}



# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)



# CLI
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Incrementally load OpenAQ hourly measurements"
    )

    parser.add_argument(
        "--backfill-days",
        type=int,
        default=DEFAULT_BACKFILL_DAYS,
        help=(
            "backfill days when sensor has no measures -> default: 60"
        ),
    )

    parser.add_argument(
        "--force-backfill",
        action="store_true",
        help="fetch the full backfill window even for sensors with existing data"
    )

    return parser.parse_args()



# API requests with retry handling
def request_with_retries(
    session: requests.Session,
    url: str,
    params: dict
) -> dict:
    for attempt in range(MAX_RETRIES):

        try:
            response = session.get(
                url,
                headers={"X-API-KEY": OPENAQ_API_KEY},
                params=params,
                timeout=REQUEST_TIMEOUT
            )

            if response.status_code==429:
                retry_after = response.headers.get("Retry-After")

                if retry_after:
                    wait_seconds = float(retry_after)
                else:
                    wait_seconds = min(
                        60,
                        2**attempt
                    )

                logger.warning(
                    "http 429 received, Waiting %.1f seconds", wait_seconds
                )

                time.sleep(wait_seconds)
                continue

            if response.status_code >=500:
                wait_seconds = min(
                    60, 2**attempt
                )

                logger.warning(
                    "http %s received. retry %s/%s in %.1f seconds",
                    response.status_code,
                    attempt + 1,
                    MAX_RETRIES,
                    wait_seconds
                )

                time.sleep(wait_seconds)
                continue

            response.raise_for_status()

            return response.json()

        except requests.RequestException as exc:
            if attempt == MAX_RETRIES - 1:
                raise

            wait_seconds = min(60, (2**attempt)+random.uniform(0,1) )

            logger.warning(
                "Network error: %s. retry %s/%s in %.1f seconds",
                exc,
                attempt+1,
                MAX_RETRIES,
                wait_seconds
            )

            time.sleep(wait_seconds)

    raise RuntimeError("OpenAQ requsts failed after retiries")



# Timestamp helpers
def parse_utc_timestamp(timestamp: str) -> datetime:
    # parse OpenAQ ISO timestamp and return a timezone-aware UTC datetime.

    parsed = datetime.fromisoformat(
        timestamp.replace("Z", "+00:00")
    )

    return parsed.astimezone(timezone.utc)


def format_api_timestamp(timestamp: datetime) -> str:
    # format a utc datetime for OpenAQ api parameters

    return(
        timestamp.astimezone(timezone.utc)
        .isoformat()
        .replace("+00:00","Z")
    )


# get latest stored timestamp
def get_latest_measurement(db, sensor_id: int) -> datetime | None:
    statement = (
        select(FactMeasurement.measured_at)
        .where(FactMeasurement.sensor_id == sensor_id)
        .order_by(FactMeasurement.measured_at.desc())
        .limit(1)
    )

    result = db.execute(statement).scalar_one_or_none()

    if result is None:
        return None

    return result.replace(tzinfo=timezone.utc)



# fetch sensor measurements
def fetch_sensor_measurements(
        api_session: requests.Session,
        sensor_id: int,
        datetime_from: datetime,
        datetime_to: datetime
) -> list[dict]:
    url = f"{BASE_URL}/sensors/{sensor_id}/hours"

    measurements = []
    page = 1

    while True:
        params = {
            "datetime_from": format_api_timestamp(datetime_from),
            "datetime_to": format_api_timestamp(datetime_to),
            "limit": PAGE_SIZE,
            "page": page
        }

        data = request_with_retries(api_session, url, params)

        results = data.get("results", [])

        logger.info(
            "sensor %s | page %s | received %s records",
            sensor_id,
            page,
            len(results)
        )

        measurements.extend(results)

        if len(results) < PAGE_SIZE:
            break

        page += 1

        # avoid api hitting unnecessarily
        time.sleep(REQUEST_SLEEP_SECONDS)

    return measurements



# Transform measurements
def transform_measurements(sensor_id: int, results: list[dict]) -> list[dict]:
    rows = []

    for result in results:
        value = result.get("value")

        period = result.get("period") or {}
        datetime_from = period.get("datetimeFrom") or {}
        timestamp = datetime_from.get("utc")

        # skip missing measures
        if value is None or timestamp is None:
            continue

        try:
            value = float(value)
        except (TypeError, ValueError):
            continue

        # -ve measures not useful
        if value<0:
            continue

        measured_at = parse_utc_timestamp(timestamp)

        rows.append(
            {
                "sensor_id": sensor_id,
                "measured_at": measured_at.replace(tzinfo=None),
                "value": value
            }
        )

    return rows



# upsert measurements
def upsert_measurements(db, rows: list[dict]) -> None:
    if not rows:
        return

    table = FactMeasurement.__table__

    statement = insert(table).values(rows)

    statement = statement.on_duplicate_key_update(value=statement.inserted.value)

    db.execute(statement)



# process one sensor
def process_sensor(
    db,
    api_session: requests.Session,
    sensor_id: int,
    backfill_days: int,
    force_backfill: bool = False
) -> int:
    latest = get_latest_measurement(db, sensor_id)
    now = datetime.now(timezone.utc)

    if force_backfill:
        datetime_from = (now - timedelta(days=backfill_days))

        logger.info(
            "Sensor %s | forced backfill of %s days",
            sensor_id,
            backfill_days
        )

    elif latest is None:
        datetime_from = (now - timedelta(days=backfill_days))

        logger.info(
            "Sensor %s | no existing data | backfilling %s days",
            sensor_id,
            backfill_days
        )
    
    else:
        # start just after latest stored hour
        datetime_from = latest + timedelta(hours=1)

        logger.info(
            "Sensor %s | latest stored: %s | fetching newer data",
            sensor_id,
            latest
        )


    if datetime_from >= now:
        logger.info(
            "Sensor %s | already up to date",
            sensor_id
        )
        return 0


    results = fetch_sensor_measurements(
        api_session,
        sensor_id,
        datetime_from,
        now
    )

    rows = transform_measurements(sensor_id, results)

    if not rows:
        logger.info(
            "Sensor %s | no valid measurement reutrned",
            sensor_id
        )

    # deduplicate within api response
    unique_rows = {
        (
            row["sensor_id"],
            row["measured_at"]
        ): row for row in rows
    }

    rows = list(unique_rows.values())

    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[
            start: start+BATCH_SIZE
        ]

        upsert_measurements(db, batch)

        db.commit()

    logger.info(
        "Sensor %s | loaded %s successfully",
        sensor_id,
        len(rows)
    )

    return len(rows)



# Main
def main() -> None:
    args = parse_args()

    logger.info("starting incremental measurement ETL")

    logger.info("Backfill days: %s", args.backfill_days)

    total_loaded = 0

    with SessionLocal() as db:
        sensor_ids = db.execute( select(DimSensor.sensor_id)).scalars().all()

        logger.info("sensors to process: %s", len(sensor_ids))

        with requests.Session() as api_session:
            for sensor_id in sensor_ids:
                try:
                    loaded = process_sensor(
                        db, api_session, sensor_id, args.backfill_days, args.force_backfill
                    )
                    total_loaded += loaded
                except Exception:
                    logger.exception("sensor %s failed", sensor_id)

                time.sleep(REQUEST_SLEEP_SECONDS)

    logger.info("Measurement ETL completed. Total rows loaded: %s",total_loaded)



if __name__ == "__main__":
    main()