"""Test helpers that avoid importing heavy backend stacks during unit tests."""

from __future__ import annotations

import sys
import types
from enum import Enum
from unittest.mock import AsyncMock


def stub_db_session(
    monkeypatch,
    *,
    is_db_enabled: bool = False,
    session_factory=None,
) -> None:
    fake_session_mod = types.ModuleType("db.session")
    fake_session_mod.is_db_enabled = lambda: is_db_enabled
    fake_session_mod.get_session_factory = lambda: session_factory
    fake_session_mod.get_database_url = lambda: None
    fake_session_mod.get_engine = lambda: None
    fake_session_mod.init_db = AsyncMock(return_value=False)
    fake_session_mod.close_db = AsyncMock()
    monkeypatch.setitem(sys.modules, "db.session", fake_session_mod)


def stub_worker_imports(monkeypatch, *, run_agent=None, generate_files=None) -> None:
    """Stub imports at the top of jobs.worker.run_research_job."""
    wm = types.ModuleType("server.websocket_manager")
    wm.run_agent = run_agent or AsyncMock(return_value=("# Report\n", None))
    utils = types.ModuleType("server.server_utils")
    utils.generate_report_files = generate_files or AsyncMock(return_value={"md": "a.md"})
    utils.sanitize_filename = lambda value: value

    tone_mod = types.ModuleType("gpt_researcher.utils.enum")

    class Tone(Enum):
        Objective = "Objective"

    tone_mod.Tone = Tone

    monkeypatch.setitem(sys.modules, "server.websocket_manager", wm)
    monkeypatch.setitem(sys.modules, "server.server_utils", utils)
    monkeypatch.setitem(sys.modules, "gpt_researcher.utils.enum", tone_mod)
