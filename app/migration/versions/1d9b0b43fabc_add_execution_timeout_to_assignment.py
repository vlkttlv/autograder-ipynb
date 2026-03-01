"""add execution timeout to assignment

Revision ID: 1d9b0b43fabc
Revises: ef42d3dd6660
Create Date: 2026-03-01 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1d9b0b43fabc"
down_revision: Union[str, None] = "ef42d3dd6660"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "assignment",
        sa.Column(
            "execution_timeout_seconds",
            sa.Integer(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("assignment", "execution_timeout_seconds")
