from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0005_workspaces"
down_revision: Union[str, None] = "0004_research_provider_cost"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table in ("watchlists", "holdings", "alerts"):
        op.add_column(
            table,
            sa.Column("workspace_id", sa.String(length=36), nullable=False, server_default="demo"),
        )
        op.create_index(f"ix_{table}_workspace_id", table, ["workspace_id"])


def downgrade() -> None:
    for table in ("watchlists", "holdings", "alerts"):
        op.drop_index(f"ix_{table}_workspace_id", table_name=table)
        op.drop_column(table, "workspace_id")
