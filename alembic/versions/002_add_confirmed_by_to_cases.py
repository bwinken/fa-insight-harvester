"""Add confirmed_by_id to fa_cases.

Revision ID: 002
Revises: 001
Create Date: 2026-03-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "fa_cases",
        sa.Column(
            "confirmed_by_id",
            sa.Integer,
            sa.ForeignKey("fa_users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("fa_cases", "confirmed_by_id")
