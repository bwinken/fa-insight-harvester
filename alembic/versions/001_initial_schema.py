"""Initial schema — users, weekly periods, reports, cases with pgvector.

Revision ID: 001
Revises: None
Create Date: 2026-03-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # --- fa_users ---
    op.create_table(
        "fa_users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("employee_name", sa.Text, unique=True, nullable=False),
        sa.Column("org_id", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # --- fa_weekly_periods ---
    op.create_table(
        "fa_weekly_periods",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("week_number", sa.Integer, nullable=False),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_weekly_year_week",
        "fa_weekly_periods",
        ["year", "week_number"],
        unique=True,
    )

    # --- fa_reports ---
    op.create_table(
        "fa_reports",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "weekly_period_id",
            sa.Integer,
            sa.ForeignKey("fa_weekly_periods.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "uploader_id",
            sa.Integer,
            sa.ForeignKey("fa_users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("filename", sa.String, nullable=False),
        sa.Column("total_slides", sa.Integer, default=0),
        sa.Column("status", sa.String, default="processing"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # --- fa_cases ---
    op.create_table(
        "fa_cases",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "report_id",
            sa.Integer,
            sa.ForeignKey("fa_reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("slide_number", sa.Integer, nullable=False),
        sa.Column("slide_image_path", sa.Text, nullable=True),
        sa.Column("date", sa.Text, nullable=True),
        sa.Column("customer", sa.Text, nullable=True),
        sa.Column("device", sa.Text, nullable=True),
        sa.Column("model", sa.Text, nullable=True),
        sa.Column("defect_mode", sa.Text, nullable=True),
        sa.Column("defect_rate_raw", sa.Text, nullable=True),
        sa.Column("defect_lots", sa.ARRAY(sa.Text), nullable=True),
        sa.Column("fab_assembly", sa.Text, nullable=True),
        sa.Column("fa_status", sa.Text, nullable=True),
        sa.Column("follow_up", sa.Text, nullable=True),
        sa.Column("raw_vlm_response", sa.Text, nullable=True),
        sa.Column(
            "confirmed_by_id",
            sa.Integer,
            sa.ForeignKey("fa_users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("text_embedding", Vector(dim=1024), nullable=True),
        sa.Column("image_embedding", Vector(dim=1024), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # Full-text search GIN index
    op.execute(
        "CREATE INDEX idx_cases_fts ON fa_cases USING gin ("
        "to_tsvector('simple', "
        "coalesce(customer,'') || ' ' || "
        "coalesce(device,'') || ' ' || "
        "coalesce(model,'') || ' ' || "
        "coalesce(defect_mode,'') || ' ' || "
        "coalesce(fa_status,'') || ' ' || "
        "coalesce(follow_up,'')))"
    )


def downgrade() -> None:
    op.drop_table("fa_cases")
    op.drop_table("fa_reports")
    op.drop_table("fa_weekly_periods")
    op.drop_table("fa_users")
    op.execute("DROP EXTENSION IF EXISTS vector")
