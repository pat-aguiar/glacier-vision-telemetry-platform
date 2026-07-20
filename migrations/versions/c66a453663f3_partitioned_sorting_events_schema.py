"""partitioned sorting_events schema

Revision ID: c66a453663f3
Revises:
Create Date: 2026-07-20 14:07:33.964031

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c66a453663f3"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Calendar-year coverage for the initial partition set. Partitions outside
# this window fall through to sorting_events_default until a follow-up
# migration provisions the next year's set.
PARTITION_YEAR = 2026


def _month_bounds(year: int) -> list[tuple[str, str, str]]:
    bounds = []
    for month in range(1, 13):
        start = f"{year}-{month:02d}-01"
        end_year, end_month = (year, month + 1) if month < 12 else (year + 1, 1)
        end = f"{end_year}-{end_month:02d}-01"
        bounds.append((f"sorting_events_{year}_{month:02d}", start, end))
    return bounds


def upgrade() -> None:
    op.create_table(
        "facilities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "devices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "facility_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("facilities.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("serial_number", sa.String(128), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "inactive", "maintenance", "decommissioned", name="device_status"),
            nullable=False,
            server_default="active",
        ),
        sa.Column("installed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_devices_facility_id", "devices", ["facility_id"])

    # --- sorting_events: native Postgres RANGE partitioning ---------------
    # op.create_table has no notion of PARTITION BY / PARTITION OF, so the
    # partitioned parent and every monthly child are raw DDL. Constraints
    # declared on the parent (PK, CHECK, FKs) are automatically enforced on
    # every partition Postgres attaches underneath it.
    op.execute(
        """
        CREATE TABLE sorting_events (
            id UUID NOT NULL,
            occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
            device_id UUID NOT NULL,
            facility_id UUID NOT NULL,
            material_type VARCHAR(64) NOT NULL,
            confidence FLOAT NOT NULL,
            payload JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            CONSTRAINT pk_sorting_events PRIMARY KEY (id, occurred_at),
            CONSTRAINT ck_sorting_events_confidence_range
                CHECK (confidence >= 0 AND confidence <= 1),
            CONSTRAINT fk_sorting_events_device_id
                FOREIGN KEY (device_id) REFERENCES devices (id) ON DELETE RESTRICT,
            CONSTRAINT fk_sorting_events_facility_id
                FOREIGN KEY (facility_id) REFERENCES facilities (id) ON DELETE RESTRICT
        ) PARTITION BY RANGE (occurred_at)
        """
    )
    op.execute(
        "CREATE INDEX ix_sorting_events_device_id_occurred_at "
        "ON sorting_events (device_id, occurred_at)"
    )
    op.execute(
        "CREATE INDEX ix_sorting_events_facility_id_occurred_at "
        "ON sorting_events (facility_id, occurred_at)"
    )

    # Catch-all partition for rows outside the provisioned monthly ranges,
    # so out-of-window inserts fail loud in the app instead of erroring at
    # the DB with "no partition found" — remove/replace once every month is
    # covered on a rolling basis.
    op.execute("CREATE TABLE sorting_events_default PARTITION OF sorting_events DEFAULT")

    for partition_name, start, end in _month_bounds(PARTITION_YEAR):
        op.execute(
            f"CREATE TABLE {partition_name} PARTITION OF sorting_events "
            f"FOR VALUES FROM ('{start}') TO ('{end}')"
        )


def downgrade() -> None:
    # Dropping the partitioned parent drops all attached partitions
    # (including sorting_events_default and every monthly child) with it.
    op.execute("DROP TABLE IF EXISTS sorting_events")
    op.drop_index("ix_devices_facility_id", table_name="devices")
    op.drop_table("devices")
    op.execute("DROP TYPE IF EXISTS device_status")
    op.drop_table("facilities")
