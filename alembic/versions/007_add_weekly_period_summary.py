"""Add summary column to fa_weekly_periods.

LLM-generated weekly summary, regenerated on each report confirmation.

Revision ID: 007
Revises: 006
Create Date: 2026-03-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "fa_weekly_periods",
        sa.Column("summary", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("fa_weekly_periods", "summary")
