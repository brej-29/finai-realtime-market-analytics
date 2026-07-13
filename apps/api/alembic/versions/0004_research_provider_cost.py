from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0004_research_provider_cost"
down_revision: Union[str, None] = "0003_research_reports"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "research_reports",
        sa.Column("provider", sa.String(length=20), nullable=False, server_default="anthropic"),
    )
    op.add_column(
        "research_reports",
        sa.Column("estimated_cost_usd", sa.Float(), nullable=False, server_default="0.0"),
    )


def downgrade() -> None:
    op.drop_column("research_reports", "estimated_cost_usd")
    op.drop_column("research_reports", "provider")
