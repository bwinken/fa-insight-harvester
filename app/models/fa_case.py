import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class FAUser(Base):
    __tablename__ = "fa_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_name: Mapped[str] = mapped_column(Text, unique=True)  # JWT sub
    org_id: Mapped[str | None] = mapped_column(Text)  # JWT org_id
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    reports: Mapped[list["FAReport"]] = relationship(back_populates="uploader")


class FAWeeklyPeriod(Base):
    __tablename__ = "fa_weekly_periods"

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(Integer)
    week_number: Mapped[int] = mapped_column(Integer)
    start_date: Mapped[datetime.date] = mapped_column(Date)
    end_date: Mapped[datetime.date] = mapped_column(Date)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    reports: Mapped[list["FAReport"]] = relationship(back_populates="weekly_period")

    __table_args__ = (
        Index("idx_weekly_year_week", "year", "week_number", unique=True),
    )


class FAReport(Base):
    __tablename__ = "fa_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    weekly_period_id: Mapped[int] = mapped_column(
        ForeignKey("fa_weekly_periods.id", ondelete="RESTRICT")
    )
    uploader_id: Mapped[int] = mapped_column(
        ForeignKey("fa_users.id", ondelete="RESTRICT")
    )
    filename: Mapped[str]
    total_slides: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(default="processing")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    weekly_period: Mapped["FAWeeklyPeriod"] = relationship(back_populates="reports")
    uploader: Mapped["FAUser"] = relationship(back_populates="reports")
    cases: Mapped[list["FACase"]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )
    slides: Mapped[list["FAReportSlide"]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )


class FAReportSlide(Base):
    """Every slide in an uploaded report — both case and non-case pages."""

    __tablename__ = "fa_report_slides"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("fa_reports.id", ondelete="CASCADE")
    )
    slide_number: Mapped[int] = mapped_column(Integer)
    image_path: Mapped[str | None] = mapped_column(Text)
    is_candidate: Mapped[bool] = mapped_column(Boolean, default=False)
    is_case_page: Mapped[bool] = mapped_column(Boolean, default=False)
    linked_case_id: Mapped[int | None] = mapped_column(
        ForeignKey("fa_cases.id", ondelete="SET NULL"), nullable=True
    )

    # Stage 1: VLM classification result
    classification_status: Mapped[str] = mapped_column(
        String(16), default="pending"
    )  # pending | case | not_case | error
    classification_confidence: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    vlm_raw_classification: Mapped[str | None] = mapped_column(Text)

    # Stage 2: VLM field extraction status
    extraction_status: Mapped[str] = mapped_column(
        String(16), default="pending"
    )  # pending | done | error

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    report: Mapped["FAReport"] = relationship(back_populates="slides")
    linked_case: Mapped["FACase | None"] = relationship()

    __table_args__ = (
        Index("idx_slides_report", "report_id"),
        Index("idx_slides_report_number", "report_id", "slide_number", unique=True),
    )


class FACase(Base):
    __tablename__ = "fa_cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("fa_reports.id", ondelete="CASCADE")
    )
    slide_number: Mapped[int]
    slide_image_path: Mapped[str | None]

    date: Mapped[str | None] = mapped_column(Text)
    customer: Mapped[str | None] = mapped_column(Text)
    device: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(Text)
    defect_mode: Mapped[str | None] = mapped_column(Text)
    defect_rate_raw: Mapped[str | None] = mapped_column(Text)
    defect_lots: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    fab_assembly: Mapped[str | None] = mapped_column(Text)
    fa_status: Mapped[str | None] = mapped_column(Text)
    follow_up: Mapped[str | None] = mapped_column(Text)

    raw_vlm_response: Mapped[str | None] = mapped_column(Text)
    confirmed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("fa_users.id", ondelete="RESTRICT"), nullable=True
    )
    text_embedding = mapped_column(Vector(dim=1024), nullable=True)
    image_embedding = mapped_column(Vector(dim=1024), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("fa_users.id", ondelete="RESTRICT"), nullable=True
    )

    report: Mapped["FAReport"] = relationship(back_populates="cases")
    confirmed_by: Mapped["FAUser | None"] = relationship(
        foreign_keys=[confirmed_by_id]
    )
    updated_by: Mapped["FAUser | None"] = relationship(
        foreign_keys=[updated_by_id]
    )

    __table_args__ = (
        Index(
            "idx_cases_fts",
            text(
                "to_tsvector('simple', "
                "coalesce(customer,'') || ' ' || "
                "coalesce(device,'') || ' ' || "
                "coalesce(model,'') || ' ' || "
                "coalesce(defect_mode,'') || ' ' || "
                "coalesce(fa_status,'') || ' ' || "
                "coalesce(follow_up,''))"
            ),
            postgresql_using="gin",
        ),
    )


class FACaseFieldLog(Base):
    """Tracks field-level changes on FA cases for detailed audit trail."""

    __tablename__ = "fa_case_field_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(
        ForeignKey("fa_cases.id", ondelete="CASCADE")
    )
    field_name: Mapped[str] = mapped_column(String(32))
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    edited_by_id: Mapped[int] = mapped_column(
        ForeignKey("fa_users.id", ondelete="RESTRICT")
    )
    edited_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    case: Mapped["FACase"] = relationship()
    edited_by: Mapped["FAUser"] = relationship()

    __table_args__ = (
        Index("idx_field_log_case", "case_id"),
        Index("idx_field_log_edited_at", "edited_at"),
    )


class AuditLog(Base):
    """Tracks all significant user operations for accountability."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("fa_users.id", ondelete="RESTRICT"))
    action: Mapped[str] = mapped_column(String(32))  # upload, confirm, edit, delete
    target_type: Mapped[str] = mapped_column(String(32))  # report, case
    target_id: Mapped[int] = mapped_column(Integer)
    detail: Mapped[str | None] = mapped_column(Text)  # JSON string of changes
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["FAUser"] = relationship()

    __table_args__ = (
        Index("idx_audit_user_id", "user_id"),
        Index("idx_audit_action", "action"),
        Index("idx_audit_target", "target_type", "target_id"),
    )
