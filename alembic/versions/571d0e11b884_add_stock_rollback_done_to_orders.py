"""add stock_rollback_done to orders

Revision ID: 571d0e11b884
Revises: 0f42c49b8308
Create Date: 2026-01-02 13:55:54.670199
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "571d0e11b884"
down_revision: Union[str, Sequence[str], None] = "0f42c49b8308"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add stock_rollback_done flag to orders table.
    This flag ensures inventory rollback is idempotent.
    """

    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "stock_rollback_done",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )


def downgrade() -> None:
    """
    Remove stock_rollback_done flag from orders table.
    """

    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.drop_column("stock_rollback_done")
