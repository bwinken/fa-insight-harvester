"""Audit logging helper — records user operations for accountability."""

import json

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fa_case import AuditLog


async def log_action(
    db: AsyncSession,
    *,
    user_id: int,
    action: str,
    target_type: str,
    target_id: int,
    detail: dict | None = None,
) -> None:
    """Create an audit log entry.

    Args:
        db: Active async DB session (caller is responsible for commit).
        user_id: The fa_users.id of the actor.
        action: One of "upload", "confirm", "edit", "delete".
        target_type: One of "report", "case".
        target_id: PK of the affected record.
        detail: Optional dict of extra context (serialised as JSON).
    """
    entry = AuditLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=json.dumps(detail, ensure_ascii=False) if detail else None,
    )
    db.add(entry)
    logger.info(
        "audit | user={} action={} target={}:{} detail={}",
        user_id,
        action,
        target_type,
        target_id,
        detail,
    )
