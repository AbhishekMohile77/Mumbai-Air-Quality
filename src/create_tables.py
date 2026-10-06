import logging
from database import Base, engine
import models

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Creating database tables....")
    Base.metadata.create_all(engine)
    logger.info("Database tables created successfully")


if __name__ == "__main__":
    main()