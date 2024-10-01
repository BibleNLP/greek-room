"""Add project self-referential foreign-key

Revision ID: 6451aba248d3
Revises: f005dd0c1a47
Create Date: 2024-09-30 17:05:10.994887

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6451aba248d3'
down_revision: Union[str, None] = 'f005dd0c1a47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add a new self-referential foreign key column for the `project` table
    """
    op.add_column("project", sa.Column("parent_id", sa.Integer))
    with op.batch_alter_table("project") as batch_op:
        batch_op.create_foreign_key(
            'fk_project_project_parent',
            "project",
            ["parent_id"],
            ["id"],
        )

def downgrade() -> None:
    """
    Drop the self-referential foreign key column for the `project` table
    """
    op.drop_column("project", "parent_id")
    with op.batch_alter_table("project") as batch_op:
        batch_op.drop_contraint('fk_project_project_parent')
