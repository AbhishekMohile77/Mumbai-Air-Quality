from datetime import datetime, date as DateType, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Double,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class DimLocation(Base):
    __tablename__ = "dim_location"

    location_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    city: Mapped[str] = mapped_column(
        String(100),
        nullable=True
    )

    country: Mapped[str] = mapped_column(
        String(100),
        nullable=True
    )

    latitude: Mapped[float] = mapped_column(
        Double,
        nullable=False
    )

    longitude: Mapped[float] = mapped_column(
        Double,
        nullable=False
    )

    provider: Mapped[str] = mapped_column(
        String(255),
        nullable=True
    )


class DimParameter(Base):
    __tablename__ = "dim_parameter"

    parameter_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True
    )

    display_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    unit: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

class DimSensor(Base):
    __tablename__ = "dim_sensor"

    sensor_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    location_id: Mapped[int] = mapped_column(
        ForeignKey("dim_location.location_id"),
        nullable=False
    )

    parameter_id: Mapped[int] = mapped_column(
        ForeignKey("dim_parameter.parameter_id"),
        nullable=False
    )

    class DimDate(Base):
        __tablename__ = "dim_date"

        date_id: Mapped[int] = mapped_column(
            Integer,
            primary_key=True
        )

        date: Mapped[DateType] = mapped_column(
            Date,
            nullable=False,
            unique=True
        )

        year: Mapped[int] = mapped_column(
            Integer,
            nullable=False
        )

        month: Mapped[int] = mapped_column(
            Integer,
            nullable=False
        )

        month_name: Mapped[str] = mapped_column(
            String(20),
            nullable=False
        )

        weekday: Mapped[str] = mapped_column(
            String(20),
            nullable=False
        )

        is_weekend: Mapped[bool] = mapped_column(
            Boolean,
            nullable=False
        )


class FactMeasurement(Base):
    __tablename__ = "fact_measurement"

    sensor_id: Mapped[int] = mapped_column(
        ForeignKey("dim_sensor.sensor_id"),
        primary_key=True
    )

    measured_at: Mapped[datetime] = mapped_column(
        DateTime,
        primary_key=True
    )

    value: Mapped[float] = mapped_column(
        Double,
        nullable=False
    )

class DataQuality(Base):
    __tablename__ = "data_quality"

    sensor_id: Mapped[int] = mapped_column(
        ForeignKey("dim_sensor.sensor_id"),
        primary_key=True
    )

    check_type: Mapped[str] = mapped_column(
        String(100),
        primary_key=True
    )

    detail: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    flagged_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now(timezone.utc),
    )