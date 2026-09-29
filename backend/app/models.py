from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class AirfareObservation(Base):
    __tablename__ = "airfare_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    collection_timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    origin: Mapped[str] = mapped_column(String(3), index=True)
    destination: Mapped[str] = mapped_column(String(3), index=True)
    route: Mapped[str] = mapped_column(String(7), index=True)
    airline: Mapped[str] = mapped_column(String(50), index=True)
    flight_number: Mapped[str | None] = mapped_column(String(12), nullable=True)
    travel_date: Mapped[date] = mapped_column(Date, index=True)
    advance_days: Mapped[int] = mapped_column(Integer, index=True)
    cabin: Mapped[str] = mapped_column(String(20), default="ECONOMY")
    fare_class: Mapped[str] = mapped_column(String(12), default="SAVER")
    base_fare: Mapped[float] = mapped_column(Float)
    taxes: Mapped[float] = mapped_column(Float)
    mandatory_fees: Mapped[float] = mapped_column(Float)
    total_fare: Mapped[float] = mapped_column(Float, index=True)
    availability: Mapped[str] = mapped_column(String(20), default="AVAILABLE")
    source: Mapped[str] = mapped_column(String(60), default="Development / replay data")
    quality_score: Mapped[float] = mapped_column(Float, default=100)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    departure_time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    arrival_time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stops: Mapped[int] = mapped_column(Integer, default=0)
    refundable: Mapped[bool] = mapped_column(Boolean, default=False)
    baggage: Mapped[str | None] = mapped_column(String(30), nullable=True)
    raw_payload_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    validation_status: Mapped[str] = mapped_column(String(16), default="valid", index=True)
    is_outlier: Mapped[bool] = mapped_column(Boolean, default=False)
