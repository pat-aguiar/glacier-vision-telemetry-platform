import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DeviceStatus(PyEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    DECOMMISSIONED = "decommissioned"


class Facility(Base):
    __tablename__ = "facilities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, server_default="UTC")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    devices: Mapped[list["Device"]] = relationship(back_populates="facility")


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("facilities.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    serial_number: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[DeviceStatus] = mapped_column(
        Enum(
            DeviceStatus,
            name="device_status",
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        server_default=DeviceStatus.ACTIVE.value,
    )
    installed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    facility: Mapped["Facility"] = relationship(back_populates="devices")
    sorting_events: Mapped[list["SortingEvent"]] = relationship(back_populates="device")


class SortingEvent(Base):
    """Native Postgres RANGE partitioned on `occurred_at`.

    SQLAlchemy only declares the parent table's shape here — partitions
    (e.g. monthly) must be created as raw DDL in an Alembic migration:

        CREATE TABLE sorting_events_2026_07 PARTITION OF sorting_events
        FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');

    Postgres requires every unique/primary key on a partitioned table to
    include the partition key column, hence the composite PK on
    (id, occurred_at) instead of a plain surrogate id.
    """

    __tablename__ = "sorting_events"
    __table_args__ = (
        PrimaryKeyConstraint("id", "occurred_at", name="pk_sorting_events"),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1", name="ck_sorting_events_confidence_range"
        ),
        UniqueConstraint("event_id", "occurred_at", name="ux_sorting_events_event_id_occurred_at"),
        Index("ix_sorting_events_device_id_occurred_at", "device_id", "occurred_at"),
        Index("ix_sorting_events_facility_id_occurred_at", "facility_id", "occurred_at"),
        {"postgresql_partition_by": "RANGE (occurred_at)"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False
    )
    # Denormalized from device.facility_id so facility-scoped queries and
    # partition pruning don't require a join across every partition.
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False
    )
    material_type: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB)
    event_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    device: Mapped["Device"] = relationship(back_populates="sorting_events")
    facility: Mapped["Facility"] = relationship()
