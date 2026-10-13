import logging
import requests
from config import OPENAQ_API_KEY

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)

BASE_URL = "https://api.openaq.org/v3"

#  sensor 5404 came from the real location response we inspected

SENSOR_ID = 5404

def main() -> None:
    url = f"{BASE_URL}/sensors/{SENSOR_ID}/hours"

    headers = {"X-API-KEY": OPENAQ_API_KEY}

    params = {
        "datetime_from": "2016-03-21T00:00:00Z",
        "datetime_to": "2020-04-10T00:00:00Z",
        "limit": 3,
        "page": 1
    }

    logger.info(
        "requesting hourly data for sensor %s ", SENSOR_ID
    )

    response = requests.get(
        url, headers=headers, params=params, timeout=30
    )

    logger.info("http status: %s", response.status_code)

    response.raise_for_status()

    data = response.json()

    logger.info(
        "Top-level keys: %s", list(data.keys())
    )

    logger.info(
        "Meta: %s", data.get("meta")
    )

    results = data.get("results", [])

    logger.info(
        "number of results: %s", len(results)
    )

    for result in results:
        logger.info(
            "hourly result: %s", result
        )


if __name__ == "__main__":
    main()