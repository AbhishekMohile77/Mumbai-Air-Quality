import logging
import requests
from config import OPENAQ_API_KEY

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)

BASE_URL = "https://api.openaq.org/v3"

def main() -> None:
    url = f"{BASE_URL}/locations"

    headers = {"X-API-Key": OPENAQ_API_KEY}

    params = {
        "coordinates": "19.0760,72.8777", #Mumbai coordinates
        "radius": 25000,
        "limit": 5
    }

    logger.info("sending test request to OpenAQ")

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=30
    )

    logger.info("HHTTP status: %s", response.status_code)

    response.raise_for_status()

    data = response.json()

    logger.info("top-level response keys: %s", list(data.keys()))

    if data.get("results"):
        logger.info("number of locations returned: %s", len(data["results"]))

        first_location = data["results"][0]

        logger.info(
            "first location result: \n%s",
            first_location
        )
    else:
        logger.warning("no locations returned")

if __name__ == "__main__":
    main()