import logging
from datetime import timedelta

from sqlalchemy import select, func, delete

from database import SessionLocal
from models import FactMeasurement, DataQuality, DimSensor, DimParameter


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)



# sanity thresholds: screening thresholds not official regulatory limits
OUTLIER_THRESHOLDS = {
    "pm25":1000,
    "pm10":1000,
    "no2":1000,
    "so2":1000,
    "o3": 1000,
    "co": 100000
}


def clear_previous_checks(session):
    # remove results from previous runs so table shows latest check
    session.execute(delete(DataQuality))
    session.commit()


def check_hourly_gaps(session):
    # flag gaps greater than 6 hours between measurements for each sensor

    sensor_ids = session.scalars(select(DimSensor.sensor_id)).all()

    gap_count = 0

    for sensor_id in sensor_ids:
        measurements = session.scalars(
            select(FactMeasurement.measured_at)
            .where(FactMeasurement.sensor_id == sensor_id)
            .order_by(FactMeasurement.measured_at)
        ).all()

        for previous, current in zip(measurements, measurements[1:]):
            gap = current - previous
            if gap > timedelta(hours=6):
                detail = (f"gap of {gap} between {previous} and {current}")

                session.add(
                    DataQuality(
                        sensor_id = sensor_id,
                        check_type="hourly_gap",
                        detail=detail
                    )
                )

                gap_count +=1

    logger.info("hourly gaps found: %s", gap_count)
    return gap_count



def check_negative_values(session):
    # flag -ve pollutant measurements
    rows = session.execute(
        select(FactMeasurement.sensor_id,
        FactMeasurement.measured_at,
        FactMeasurement.value
        ).where(FactMeasurement.value < 0)
    ).all()

    for sensor_id, measured_at, value in rows:
        detail = (f"Negative measurement: value={value} at {measured_at}")

        session.add(
            DataQuality(
                sensor_id=sensor_id,
                check_type="negative_value",
                detail=detail
            )
        )

    logger.info("Negative values found: %s", len(rows))
    return len(rows)



def check_outliers(session):
    # flag unusually high pollutant measurements

    rows = session.execute(
        select(FactMeasurement.sensor_id,
               FactMeasurement.measured_at,
               FactMeasurement.value,
               DimParameter.name
            )
            .join(
                DimSensor,
                FactMeasurement.sensor_id == DimSensor.sensor_id
            )
            .join(
                DimParameter,
                DimSensor.parameter_id == DimParameter.parameter_id
            )
    ).all()

    count = 0

    for sensor_id, measured_at, value, parameter_name in rows:
        threshold = OUTLIER_THRESHOLDS.get(parameter_name)

        if threshold is not None and value > threshold:

            detail = (
                f"high {parameter_name} measurements"
                f"value={value}, threshold={threshold},"
                f"time={measured_at}"
            )

            session.add(
                DataQuality(
                    sensor_id=sensor_id,
                    cehck_type="high_value",
                    detail=detail
                )
            )

            count +=1

    logger.info("high-value issues found: %s", count)

    return count



def main():
    logger.info("----Start data quality checks----")

    session = SessionLocal()

    try:
        clear_previous_checks(session)

        gap_count= check_hourly_gaps(session)
        negative_count = check_negative_values(session)
        outlier_count = check_outliers(session)

        session.commit()

        logger.info(
            "Data quality checks finished"
            "Gaps=%s | Negative=%s | High values=%s",
            gap_count,
            negative_count,
            outlier_count
        )

    except Exception:
        session.rollback()
        logger.exception("Data quality checks failed")
        raise

    finally:
        session.close()



if __name__ == "__main__":
    main()