"""Add classification and extraction status fields to fa_report_slides.

Supports two-stage VLM pipeline: Stage 1 (classification) + Stage 2 (extraction).

Revision ID: 005
Revises: 004
Create Date: 2026-03-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "fa_report_slides",
        sa.Column(
            "classification_status",
            sa.String(16),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "fa_report_slides",
        sa.Column("classification_confidence", sa.Float, nullable=True),
    )
    op.add_column(
        "fa_report_slides",
        sa.Column("vlm_raw_classification", sa.Text, nullable=True),
    )
    op.add_column(
        "fa_report_slides",
        sa.Column(
            "extraction_status",
            sa.String(16),
            nullable=False,
            server_default="pending",
        ),
    )

    # Backfill existing data: slides already marked as case pages
    # should be treated as fully processed (classification=case, extraction=done)
    op.execute(
        "UPDATE fa_report_slides SET classification_status = 'case', "
        "extraction_status = 'done' WHERE is_case_page = true"
    )
    op.execute(
        "UPDATE fa_report_slides SET classification_status = 'not_case' "
        "WHERE is_case_page = false AND is_candidate = true"
    )


def downgrade() -> None:
    op.drop_column("fa_report_slides", "extraction_status")
    op.drop_column("fa_report_slides", "vlm_raw_classification")
    op.drop_column("fa_report_slides", "classification_confidence")
    op.drop_column("fa_report_slides", "classification_status")
