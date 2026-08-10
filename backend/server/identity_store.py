"""Persist visitor/registered users and migrate visitor-owned rows. :-)"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def ensure_user(
    user_id: str,
    *,
    kind: str = "visitor",
    email: str | None = None,
    display_name: str | None = None,
    password_hash: str | None = None,
) -> None:
    """Upsert a users row so FKs on sessions/jobs succeed."""
    try:
        from db.session import get_session_factory, is_db_enabled
        from db.models import User

        if not is_db_enabled():
            return
        factory = get_session_factory()
        if factory is None:
            return
        async with factory() as session:
            row = await session.get(User, user_id)
            if row is None:
                session.add(
                    User(
                        id=user_id,
                        email=email,
                        display_name=display_name,
                        kind=kind,
                        password_hash=password_hash,
                    )
                )
            else:
                if email is not None:
                    row.email = email
                if display_name is not None:
                    row.display_name = display_name
                if password_hash is not None:
                    row.password_hash = password_hash
                if kind:
                    row.kind = kind
            await session.commit()
    except Exception as exc:
        logger.warning("ensure_user failed for %s: %s", user_id, exc)


async def get_user_by_email(email: str) -> Optional[dict]:
    try:
        from db.session import get_session_factory, is_db_enabled
        from db.models import User
        from sqlalchemy import select

        if not is_db_enabled():
            return None
        factory = get_session_factory()
        if factory is None:
            return None
        async with factory() as session:
            row = (
                await session.execute(select(User).where(User.email == email))
            ).scalar_one_or_none()
            if not row:
                return None
            return {
                "id": row.id,
                "email": row.email,
                "display_name": row.display_name,
                "kind": getattr(row, "kind", "registered"),
                "password_hash": getattr(row, "password_hash", None),
            }
    except Exception as exc:
        logger.warning("get_user_by_email failed: %s", exc)
        return None


async def migrate_visitor_ownership(*, from_user_id: str, to_user_id: str) -> dict:
    """Move sessions, jobs, documents, chunks from visitor → registered user."""
    stats = {
        "sessions": 0,
        "jobs": 0,
        "documents": 0,
        "chunks": 0,
        "from_user_id": from_user_id,
        "to_user_id": to_user_id,
    }
    if not from_user_id or not to_user_id or from_user_id == to_user_id:
        return stats
    if not from_user_id.startswith("vis_"):
        return stats

    try:
        from db.session import get_session_factory, is_db_enabled
        from db.models import ResearchSession, ResearchJob, Document, DocumentChunk
        from sqlalchemy import update

        if not is_db_enabled():
            return stats
        factory = get_session_factory()
        if factory is None:
            return stats

        await ensure_user(to_user_id, kind="registered")

        async with factory() as session:
            r1 = await session.execute(
                update(ResearchSession)
                .where(ResearchSession.user_id == from_user_id)
                .values(user_id=to_user_id, tenant_id=to_user_id)
            )
            stats["sessions"] = r1.rowcount or 0

            r2 = await session.execute(
                update(ResearchJob)
                .where(ResearchJob.user_id == from_user_id)
                .values(user_id=to_user_id, tenant_id=to_user_id)
            )
            stats["jobs"] = r2.rowcount or 0

            try:
                r3 = await session.execute(
                    update(Document)
                    .where(Document.user_id == from_user_id)
                    .values(user_id=to_user_id, tenant_id=to_user_id)
                )
                stats["documents"] = r3.rowcount or 0
                r4 = await session.execute(
                    update(DocumentChunk)
                    .where(DocumentChunk.user_id == from_user_id)
                    .values(user_id=to_user_id, tenant_id=to_user_id)
                )
                stats["chunks"] = r4.rowcount or 0
            except Exception as doc_exc:
                logger.warning("document migrate skipped: %s", doc_exc)

            await session.commit()
    except Exception as exc:
        logger.exception("migrate_visitor_ownership failed: %s", exc)
    return stats
