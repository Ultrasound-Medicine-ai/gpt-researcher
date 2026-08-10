"""Chat → independent report tool callback (no FastAPI/app import). :-)"""

from __future__ import annotations

from typing import Any


def chat_report_request(task: str, requirements: str = "") -> dict[str, Any]:
    """Return a UI-consumable request for POST /api/jobs/research."""
    full_task = task
    if requirements:
        full_task = f"{task}\n\nAdditional requirements: {requirements}"
    return {
        "action": "create_report",
        "task": full_task,
        "knowledge_policy": "local_first",
    }
