"""add payment idempotency constraint

Revision ID: 0f42c49b8308
Revises:
Create Date: 2025-12-29 12:32:56.520335
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0f42c49b8308"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # SQLite-safe way to add UNIQUE constraint
    with op.batch_alter_table("payments", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_order_payment_idempotent",
            ["order_id", "razorpay_payment_id"],
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("payments", schema=None) as batch_op:
        batch_op.drop_constraint(
            "uq_order_payment_idempotent",
            type_="unique",
        )
