"""Add language name column

Revision ID: f005dd0c1a47
Revises:
Create Date: 2024-05-09 13:28:51.976653

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import Column, String

# revision identifiers, used by Alembic.
revision: str = 'f005dd0c1a47'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add a new language name column in the `project` table
    """
    op.add_column("project", Column("lang_name", String(100)))


def downgrade() -> None:
    op.drop_column("project", "lang_name")
