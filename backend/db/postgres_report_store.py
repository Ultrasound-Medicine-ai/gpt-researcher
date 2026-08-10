"""PostgreSQL-backed report store with the same API as JSON ReportStore."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .models import ChatMessage, Report, ResearchSession, ResearchSource, User

logger = logging.getLogger(__name__)


class PostgresReportStore:
    """Persist reports/sessions in PostgreSQL while preserving ReportStore methods."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def _ensure_user(self, session: AsyncSession, user_id: str) -> None:
        existing = await session.get(User, user_id)
        if existing is None:
            session.add(User(id=user_id, display_name=user_id))
            await session.flush()

    def _session_to_dict(
        self,
        research: ResearchSession,
        report: Report | None,
        messages: list[ChatMessage] | None = None,
    ) -> Dict[str, Any]:
        chat_messages = []
        if messages is not None:
            for msg in messages:
                item: Dict[str, Any] = {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": int(msg.created_at.timestamp() * 1000) if msg.created_at else 0,
                }
                if msg.metadata_json:
                    item["metadata"] = msg.metadata_json
                chat_messages.append(item)

        return {
            "id": str(research.id),
            "question": (report.question if report else research.task_text) or "",
            "answer": (report.markdown if report else "") or "",
            "orderedData": (report.ordered_data if report else []) or [],
            "chatMessages": chat_messages,
            "timestamp": int(
                (report.updated_at if report and report.updated_at else research.updated_at).timestamp()
                * 1000
            ),
            "user_id": research.user_id,
            "status": research.status,
            "report_language": research.report_language,
            "job_id": research.job_id,
        }

    async def list_reports(
        self,
        report_ids: List[str] | None = None,
        user_id: str | None = None,
    ) -> List[Dict[str, Any]]:
        async with self._session_factory() as session:
            stmt = select(ResearchSession, Report).outerjoin(
                Report, Report.session_id == ResearchSession.id
            )
            if user_id:
                stmt = stmt.where(ResearchSession.user_id == user_id)
            if report_ids is not None:
                uuids = []
                for rid in report_ids:
                    try:
                        uuids.append(uuid.UUID(rid))
                    except ValueError:
                        continue
                if not uuids:
                    return []
                stmt = stmt.where(ResearchSession.id.in_(uuids))
            rows = (await session.execute(stmt)).all()
            results = []
            for research, report in rows:
                msg_rows = (
                    await session.execute(
                        select(ChatMessage)
                        .where(ChatMessage.session_id == research.id)
                        .order_by(ChatMessage.created_at.asc())
                    )
                ).scalars().all()
                results.append(self._session_to_dict(research, report, list(msg_rows)))
            return results

    async def get_report(
        self, report_id: str, user_id: str | None = None
    ) -> Dict[str, Any] | None:
        try:
            sid = uuid.UUID(report_id)
        except ValueError:
            return None

        async with self._session_factory() as session:
            research = await session.get(ResearchSession, sid)
            if research is None:
                return None
            if user_id and research.user_id != user_id:
                return None
            report = (
                await session.execute(select(Report).where(Report.session_id == sid))
            ).scalar_one_or_none()
            msg_rows = (
                await session.execute(
                    select(ChatMessage)
                    .where(ChatMessage.session_id == sid)
                    .order_by(ChatMessage.created_at.asc())
                )
            ).scalars().all()
            return self._session_to_dict(research, report, list(msg_rows))

    async def upsert_report(
        self,
        report_id: str,
        report: Dict[str, Any],
        user_id: str | None = None,
    ) -> None:
        """Upsert report. Persistence failures are logged and re-raised by callers if needed."""
        try:
            sid = uuid.UUID(str(report_id))
        except ValueError:
            sid = uuid.uuid4()
        owner = user_id or report.get("user_id") or "anonymous"
        async with self._session_factory() as session:
            await self._ensure_user(session, owner)
            from security import tenant_id_for

            tid = report.get("tenant_id") or tenant_id_for(owner)
            research = await session.get(ResearchSession, sid)
            if research is None:
                research = ResearchSession(
                    id=sid,
                    user_id=owner,
                    tenant_id=tid,
                    task_text=str(report.get("question") or ""),
                    report_language=str(report.get("report_language") or "chinese"),
                    status=str(report.get("status") or "completed"),
                    job_id=report.get("job_id"),
                )
                session.add(research)
            else:
                if user_id and research.user_id != user_id:
                    raise PermissionError("Report belongs to another user")
                research.task_text = str(report.get("question") or research.task_text)
                if not getattr(research, "tenant_id", None):
                    research.tenant_id = tid
                if report.get("report_language"):
                    research.report_language = str(report["report_language"])
                if report.get("status"):
                    research.status = str(report["status"])
                if report.get("job_id"):
                    research.job_id = report["job_id"]

            existing_report = (
                await session.execute(select(Report).where(Report.session_id == sid))
            ).scalar_one_or_none()
            if existing_report is None:
                session.add(
                    Report(
                        session_id=sid,
                        markdown=str(report.get("answer") or ""),
                        question=str(report.get("question") or ""),
                        ordered_data=report.get("orderedData") or [],
                        citation_style=str(report.get("citation_style") or "numbered"),
                    )
                )
            else:
                existing_report.markdown = str(report.get("answer") or existing_report.markdown)
                existing_report.question = str(report.get("question") or existing_report.question)
                if "orderedData" in report:
                    existing_report.ordered_data = report.get("orderedData") or []
                existing_report.version = int(existing_report.version or 1) + 1

            # Replace chat messages when provided
            if "chatMessages" in report and isinstance(report["chatMessages"], list):
                old_msgs = (
                    await session.execute(
                        select(ChatMessage).where(ChatMessage.session_id == sid)
                    )
                ).scalars().all()
                for msg in old_msgs:
                    await session.delete(msg)
                for msg in report["chatMessages"]:
                    if not isinstance(msg, dict):
                        continue
                    session.add(
                        ChatMessage(
                            session_id=sid,
                            role=str(msg.get("role") or "user"),
                            content=str(msg.get("content") or ""),
                            metadata_json=msg.get("metadata"),
                        )
                    )

            await session.commit()

    async def delete_report(self, report_id: str, user_id: str | None = None) -> bool:
        try:
            sid = uuid.UUID(report_id)
        except ValueError:
            return False
        async with self._session_factory() as session:
            research = await session.get(ResearchSession, sid)
            if research is None:
                return False
            if user_id and research.user_id != user_id:
                return False
            await session.delete(research)
            await session.commit()
            return True

    async def get_session_context(self, report_id: str, user_id: str | None = None) -> Dict[str, Any]:
        """Load server-side chat context: report + sources excerpts + messages."""
        report = await self.get_report(report_id, user_id=user_id)
        if report is None:
            return {}

        try:
            sid = uuid.UUID(report_id)
        except ValueError:
            return {"report": report}

        async with self._session_factory() as session:
            sources = (
                await session.execute(
                    select(ResearchSource)
                    .where(ResearchSource.session_id == sid)
                    .order_by(ResearchSource.source_index.asc())
                )
            ).scalars().all()
            source_blocks = []
            for src in sources:
                source_blocks.append(
                    f"[{src.source_index}] {src.title or 'Untitled'}\n"
                    f"URL: {src.url}\n"
                    f"{(src.excerpt or '')[:500]}"
                )
            research_context = "\n\n".join(source_blocks)
            return {
                "report": report,
                "research_topic": report.get("question") or "",
                "research_context": research_context,
                "messages": report.get("chatMessages") or [],
                "report_language": report.get("report_language") or "chinese",
            }

    async def save_research_sources(
        self,
        report_id: str,
        sources: List[Dict[str, Any]],
        user_id: str | None = None,
        *,
        raise_on_error: bool = False,
    ) -> None:
        """Persist numbered sources. raise_on_error=True for job completion gating."""
        try:
            sid = uuid.UUID(report_id)
            async with self._session_factory() as session:
                research = await session.get(ResearchSession, sid)
                if research is None:
                    if raise_on_error:
                        raise ValueError(f"Session not found for sources: {report_id}")
                    return
                if user_id and research.user_id != user_id:
                    if raise_on_error:
                        raise PermissionError("Session belongs to another user")
                    return
                old = (
                    await session.execute(
                        select(ResearchSource).where(ResearchSource.session_id == sid)
                    )
                ).scalars().all()
                for row in old:
                    await session.delete(row)
                for index, source in enumerate(sources, start=1):
                    url = str(source.get("url") or "").strip()
                    if not url:
                        continue
                    raw = str(source.get("raw_content") or "")
                    session.add(
                        ResearchSource(
                            session_id=sid,
                            source_index=index,
                            url=url,
                            title=str(source.get("title") or ""),
                            excerpt=raw[:500],
                            raw_content_ref=source.get("raw_content_ref"),
                        )
                    )
                await session.commit()
        except Exception as exc:
            logger.warning("Failed to persist research sources: %s", exc)
            if raise_on_error:
                raise
