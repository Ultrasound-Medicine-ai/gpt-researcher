import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List


class ReportStore:
    def __init__(self, path: Path):
        self._path = path
        self._lock = asyncio.Lock()

    async def _ensure_parent_dir(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)

    async def _read_all_unlocked(self) -> Dict[str, Dict[str, Any]]:
        if not self._path.exists():
            return {}
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data  # type: ignore[return-value]
        except Exception:
            return {}
        return {}

    async def _write_all_unlocked(self, data: Dict[str, Dict[str, Any]]) -> None:
        await self._ensure_parent_dir()
        tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        tmp_path.replace(self._path)

    async def list_reports(
        self,
        report_ids: List[str] | None = None,
        user_id: str | None = None,
    ) -> List[Dict[str, Any]]:
        async with self._lock:
            data = await self._read_all_unlocked()
            values = list(data.values()) if report_ids is None else [
                data[report_id] for report_id in report_ids if report_id in data
            ]
            if user_id:
                values = [
                    r for r in values
                    if not r.get("user_id") or r.get("user_id") == user_id
                ]
            return values

    async def get_report(
        self, report_id: str, user_id: str | None = None
    ) -> Dict[str, Any] | None:
        async with self._lock:
            data = await self._read_all_unlocked()
            report = data.get(report_id)
            if report and user_id and report.get("user_id") and report.get("user_id") != user_id:
                return None
            return report

    async def upsert_report(
        self,
        report_id: str,
        report: Dict[str, Any],
        user_id: str | None = None,
    ) -> None:
        async with self._lock:
            data = await self._read_all_unlocked()
            if user_id:
                report = {**report, "user_id": user_id}
            data[report_id] = report
            await self._write_all_unlocked(data)

    async def delete_report(self, report_id: str, user_id: str | None = None) -> bool:
        async with self._lock:
            data = await self._read_all_unlocked()
            existing = data.get(report_id)
            if existing is None:
                return False
            if user_id and existing.get("user_id") and existing.get("user_id") != user_id:
                return False
            del data[report_id]
            await self._write_all_unlocked(data)
            return True

    async def get_session_context(
        self, report_id: str, user_id: str | None = None
    ) -> Dict[str, Any]:
        """JSON-mode session context for Chat (report + stored messages only)."""
        report = await self.get_report(report_id, user_id=user_id)
        if report is None:
            return {}
        return {
            "report": report,
            "research_topic": report.get("question") or "",
            "research_context": "",
            "messages": report.get("chatMessages") or [],
            "report_language": report.get("report_language") or "chinese",
        }
