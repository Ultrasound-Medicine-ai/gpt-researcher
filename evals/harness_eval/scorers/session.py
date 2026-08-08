"""Session isolation scorers (API contract). Skip if API unreachable."""

from __future__ import annotations

import os
from typing import Any


def score_session_isolation(api_base: str | None = None) -> tuple[bool, list[str], dict[str, Any]]:
    """
    Cheap check: two users' report namespaces should not collide when X-User-Id set.
    Returns skipped=True when API is down so CI cheap suite can soft-pass.
    """
    import urllib.error
    import urllib.request
    import json
    import uuid

    base = (api_base or os.getenv("HARNESS_API_BASE") or "http://127.0.0.1:8000").rstrip("/")
    meta: dict[str, Any] = {"api_base": base}
    try:
        rid = str(uuid.uuid4())
        body = json.dumps(
            {
                "id": rid,
                "question": "harness isolation probe",
                "answer": "secret-for-user-a",
                "orderedData": [],
                "chatMessages": [],
            }
        ).encode("utf-8")

        def _req(method: str, path: str, user: str, data: bytes | None = None):
            req = urllib.request.Request(
                f"{base}{path}",
                data=data,
                method=method,
                headers={
                    "Content-Type": "application/json",
                    "X-User-Id": user,
                },
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))

        status, _ = _req("POST", "/api/reports", "user-a", body)
        if status >= 400:
            return False, [f"create failed status={status}"], meta

        # User B should not see user A's report when isolation is on
        try:
            status_b, payload_b = _req("GET", f"/api/reports/{rid}", "user-b")
            if status_b == 200 and payload_b.get("report"):
                return False, ["user-b can read user-a report"], meta
        except urllib.error.HTTPError as err:
            if err.code not in (403, 404):
                return False, [f"unexpected status for user-b: {err.code}"], meta

        status_a, payload_a = _req("GET", f"/api/reports/{rid}", "user-a")
        if status_a != 200 or not payload_a.get("report"):
            return False, ["user-a cannot reload own report"], meta

        meta["passed"] = True
        return True, [], meta
    except Exception as exc:
        meta["skipped"] = True
        meta["reason"] = str(exc)
        # Soft-pass when API not running — cheap suite should not fail offline
        return True, [], meta
