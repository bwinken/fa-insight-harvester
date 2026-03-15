"""Initial schema — users, weekly periods, reports, slides, cases,
field logs, audit logs, with pgvector.

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
    # Enable extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

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
        sa.Column("summary", sa.Text, nullable=True),
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
    # Prevent uploading the same file to the same week twice
    op.create_index(
        "idx_reports_period_filename",
        "fa_reports",
        ["weekly_period_id", "filename"],
        unique=True,
    )
    op.create_index(
        "idx_reports_weekly_period",
        "fa_reports",
        ["weekly_period_id"],
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
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_by_id",
            sa.Integer,
            sa.ForeignKey("fa_users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.create_index("idx_cases_report", "fa_cases", ["report_id"])
    op.create_index("idx_cases_created_at", "fa_cases", ["created_at"])

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

    # HNSW index for vector similarity search (cosine distance)
    op.execute(
        "CREATE INDEX idx_cases_text_embedding ON fa_cases "
        "USING hnsw (text_embedding vector_cosine_ops)"
    )

    # Trigram indexes for ilike fuzzy search on customer/device
    op.execute(
        "CREATE INDEX idx_cases_customer_trgm ON fa_cases "
        "USING gin (customer gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX idx_cases_device_trgm ON fa_cases USING gin (device gin_trgm_ops)"
    )

    # --- fa_report_slides ---
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
            "classification_status",
            sa.String(16),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("classification_confidence", sa.Float, nullable=True),
        sa.Column("vlm_raw_classification", sa.Text, nullable=True),
        sa.Column(
            "extraction_status",
            sa.String(16),
            nullable=False,
            server_default="pending",
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

    # --- fa_case_field_logs ---
    op.create_table(
        "fa_case_field_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "case_id",
            sa.Integer,
            sa.ForeignKey("fa_cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field_name", sa.String(32), nullable=False),
        sa.Column("old_value", sa.Text, nullable=True),
        sa.Column("new_value", sa.Text, nullable=True),
        sa.Column(
            "edited_by_id",
            sa.Integer,
            sa.ForeignKey("fa_users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "edited_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_field_log_case", "fa_case_field_logs", ["case_id"])
    op.create_index("idx_field_log_edited_at", "fa_case_field_logs", ["edited_at"])

    # --- audit_logs ---
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("fa_users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("target_type", sa.String(32), nullable=False),
        sa.Column("target_id", sa.Integer, nullable=False),
        sa.Column("detail", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_audit_user_id", "audit_logs", ["user_id"])
    op.create_index("idx_audit_action", "audit_logs", ["action"])
    op.create_index("idx_audit_target", "audit_logs", ["target_type", "target_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("fa_case_field_logs")
    op.drop_table("fa_report_slides")
    op.drop_table("fa_cases")
    op.drop_table("fa_reports")
    op.drop_table("fa_weekly_periods")
    op.drop_table("fa_users")
    op.execute("DROP EXTENSION IF EXISTS vector")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
