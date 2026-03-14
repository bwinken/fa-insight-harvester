"""Add fa_report_slides table for tracking all slides per report.

Revision ID: 004
Revises: 003
Create Date: 2026-03-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fa_report_slides",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "report_id",
            sa.Integer,
            sa.ForeignKey("fa_reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("slide_number", sa.Integer, nullable=False),
        sa.Column("image_path", sa.Text, nullable=True),
        sa.Column("is_candidate", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_case_page", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "linked_case_id",
            sa.Integer,
            sa.ForeignKey("fa_cases.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_slides_report", "fa_report_slides", ["report_id"])
    op.create_index(
        "idx_slides_report_number",
        "fa_report_slides",
        ["report_id", "slide_number"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("fa_report_slides")
