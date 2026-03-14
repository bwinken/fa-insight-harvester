"""Add updated_at/updated_by to FACase and create FACaseFieldLog table.

Supports inline editing with field-level audit trail.

Revision ID: 006
Revises: 005
Create Date: 2026-03-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add edit tracking columns to fa_cases
    op.add_column(
        "fa_cases",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "fa_cases",
        sa.Column(
            "updated_by_id",
            sa.Integer,
            sa.ForeignKey("fa_users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )

    # Create field-level change log table
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


def downgrade() -> None:
    op.drop_table("fa_case_field_logs")
    op.drop_column("fa_cases", "updated_by_id")
    op.drop_column("fa_cases", "updated_at")
