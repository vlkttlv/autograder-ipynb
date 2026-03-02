"""merge two heads after ef42d3dd6660

Revision ID: 5b608a4ccf4d
Revises: 1d9b0b43fabc, 9c2cc5d40370
Create Date: 2026-03-02 20:00:33.098914

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5b608a4ccf4d'
down_revision: Union[str, None] = ('1d9b0b43fabc', '9c2cc5d40370')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
