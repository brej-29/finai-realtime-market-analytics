from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002_alert_events_and_enums"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extend alert_direction_enum to support technical alert types.
    old_type = sa.Enum(
        "price_above",
        "price_below",
        name="alert_direction_enum",
        native_enum=False,
    )
    new_type = sa.Enum(
        "price_above",
        "price_below",
        "rsi_above",
        "rsi_below",
        "ma_cross",
        name="alert_direction_enum",
        native_enum=False,
    )

    # On some backends Enum(nativenum=False) is effectively a CHECK on VARCHAR;
    # altering via Alembic's alter_column will update the constraint.
    op.alter_column(
        "alerts",
        "direction",
        existing_type=old_type,
        type_=new_type,
        existing_nullable=False,
    )

    # Create alert_events table to record fired alerts.
    op.create_table(
        "alert_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "alert_id",
            sa.Integer(),
            sa.ForeignKey("alerts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "fired_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("message", sa.String(length=255), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "new",
                "delivered",
                "error",
                name="alert_event_status_enum",
                native_enum=False,
            ),
            nullable=False,
            server_default="new",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("alert_events")

    # Revert alert_direction_enum to original values.
    new_type = sa.Enum(
        "price_above",
        "price_below",
        name="alert_direction_enum",
        native_enum=False,
    )
    old_type = sa.Enum(
        "price_above",
        "price_below",
        "rsi_above",
        "rsi_below",
        "ma_cross",
        name="alert_direction_enum",
        native_enum=False,
    )

    op.alter_column(
        "alerts",
        "direction",
        existing_type=old_type,
        type_=new_type,
        existing_nullable=False,
    )