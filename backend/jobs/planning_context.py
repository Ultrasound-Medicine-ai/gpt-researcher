"""Per-user planning hints: recent history + tech-first acronym preference. :-)"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

_TECH_HINT_RE = re.compile(
    r"(?:server[- ]?sent|eventsource|websocket|http|api|rag|llm|embedding|"
    r"postgres|redis|docker|react|next\.?js|typescript|python|kubernetes|"
    r"微服务|推送|流式|前端|后端|协议|框架)",
    re.IGNORECASE,
)

_FINANCE_HINT_RE = re.compile(
    r"(?:stock|exchange|证券|交易所|上交所|深交所|股市|IPO|行情|finance|trading)",
    re.IGNORECASE,
)

# Ambiguous tokens → preferred expansions by domain. :-)
_ACRONYM_MAP: dict[str, dict[str, str]] = {
    "SSE": {
        "tech": "Server-Sent Events (SSE; HTTP EventSource server push)",
        "finance": "Shanghai Stock Exchange (SSE; 上海证券交易所)",
    },
    "API": {
        "tech": "Application Programming Interface (API)",
        "finance": "Application Programming Interface (API)",
    },
    "RAG": {
        "tech": "Retrieval-Augmented Generation (RAG)",
        "finance": "Retrieval-Augmented Generation (RAG)",
    },
}


def _env_truthy(name: str, default: str = "true") -> bool:
    raw = (os.getenv(name) or default).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def planning_user_context_enabled() -> bool:
    return _env_truthy("RESEARCH_USER_PLANNING_CONTEXT", "true")


def default_domain_preference() -> str:
    raw = (os.getenv("RESEARCH_AMBIGUITY_PREFERENCE") or "tech").strip().lower()
    return raw if raw in {"tech", "finance", "auto"} else "tech"


def _clip(text: str, n: int) -> str:
    t = re.sub(r"\s+", " ", (text or "").strip())
    return t if len(t) <= n else t[: n - 1].rstrip() + "…"


def infer_domain_preference(blobs: list[str], *, default: str = "tech") -> str:
    """Score recent text for tech vs finance lean; default tech for this product. :-)"""
    joined = "\n".join(b for b in blobs if b)
    if not joined.strip():
        return default if default != "auto" else "tech"
    tech = len(_TECH_HINT_RE.findall(joined))
    finance = len(_FINANCE_HINT_RE.findall(joined))
    if finance >= tech + 2:
        return "finance"
    if tech >= finance:
        return "tech"
    return default if default != "auto" else "tech"


def _token_in_text(token: str, text: str) -> bool:
    """Match ASCII acronyms next to CJK (\\b fails between 研 and SSE). :-)"""
    if not text or not token:
        return False
    return bool(
        re.search(
            rf"(?i)(?<![A-Za-z0-9]){re.escape(token)}(?![A-Za-z0-9])",
            text,
        )
    )


def expand_ambiguous_task(task: str, *, preference: str) -> tuple[str, list[str]]:
    """Return (expanded_task, notes). Leaves task unchanged when no acronym hits."""
    notes: list[str] = []
    expanded = task
    pref = preference if preference in {"tech", "finance"} else "tech"
    for token, mapping in _ACRONYM_MAP.items():
        if not _token_in_text(token, task):
            continue
        # Skip if already disambiguated
        if token == "SSE" and re.search(
            r"(?i)server[- ]?sent|eventsource|上海证券|stock exchange", task
        ):
            continue
        choice = mapping.get(pref) or mapping.get("tech") or token
        notes.append(f"{token} → {choice}")
        # Append clarification once; keep original wording for title fidelity. :-)
        if choice.lower() not in expanded.lower():
            expanded = f"{expanded}（指：{choice}）"
    return expanded, notes


def build_planning_hint(
    *,
    task: str,
    recent_titles: list[str],
    recent_chat_lines: list[str],
    preference: Optional[str] = None,
) -> dict[str, Any]:
    """Build hint dict for search/planning injection."""
    pref_mode = preference or default_domain_preference()
    blobs = [*recent_titles, *recent_chat_lines, task]
    domain = (
        infer_domain_preference(blobs, default="tech")
        if pref_mode == "auto"
        else pref_mode
    )
    expanded, notes = expand_ambiguous_task(task, preference=domain)

    history_bits = []
    for t in recent_titles[:6]:
        history_bits.append(f"- report: {_clip(t, 120)}")
    for line in recent_chat_lines[-8:]:
        history_bits.append(f"- chat: {_clip(line, 160)}")

    lines = [
        f"User domain preference for this product: {domain}-first.",
        "When the task contains ambiguous acronyms, prefer the meaning above "
        "unless the user clearly asks for another domain.",
    ]
    if notes:
        lines.append("Disambiguation applied: " + "; ".join(notes))
    if history_bits:
        lines.append("Recent user research/chat signals:")
        lines.extend(history_bits)
    else:
        lines.append("No prior user history available; keep tech-first defaults.")

    hint = "\n".join(lines)
    return {
        "domain_preference": domain,
        "expanded_task": expanded,
        "planning_hint": hint,
        "disambiguation_notes": notes,
    }


async def collect_user_recent_signals(
    *,
    report_store: Any,
    user_id: str,
    parent_chat_id: Optional[str] = None,
    client_messages: Optional[list[dict]] = None,
    limit_reports: int = 8,
) -> tuple[list[str], list[str]]:
    """Return (recent_report_titles, recent_chat_lines) best-effort."""
    titles: list[str] = []
    chat_lines: list[str] = []

    # Client-provided chat turns (current conversation)
    for m in client_messages or []:
        role = str(m.get("role") or "user")
        content = str(m.get("content") or "").strip()
        if content:
            chat_lines.append(f"{role}: {content}")

    if report_store is None or not user_id:
        return titles, chat_lines

    try:
        if parent_chat_id and hasattr(report_store, "get_report"):
            parent = await report_store.get_report(parent_chat_id, user_id=user_id)
            if parent:
                q = str(parent.get("question") or "").strip()
                if q:
                    titles.append(q)
                for msg in (parent.get("chatMessages") or [])[-10:]:
                    role = str(msg.get("role") or "user")
                    content = str(msg.get("content") or "").strip()
                    if content:
                        chat_lines.append(f"{role}: {content}")
    except Exception as exc:
        logger.debug("parent chat load skipped: %s", exc)

    try:
        if hasattr(report_store, "list_recent_report_titles"):
            titles.extend(
                await report_store.list_recent_report_titles(
                    user_id=user_id, limit=limit_reports
                )
            )
        elif hasattr(report_store, "list_reports"):
            # Fallback: filter in Python (may be heavier). :-)
            rows = await report_store.list_reports(report_ids=None, user_id=user_id)
            rows = sorted(
                rows,
                key=lambda r: r.get("updatedAt") or r.get("createdAt") or 0,
                reverse=True,
            )
            for r in rows[:limit_reports]:
                q = str(r.get("question") or r.get("title") or "").strip()
                if q and q not in titles:
                    titles.append(q)
    except Exception as exc:
        logger.debug("recent reports load skipped: %s", exc)

    # de-dupe preserve order
    def _uniq(items: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for it in items:
            key = it.strip()
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(key)
        return out

    return _uniq(titles)[:limit_reports], _uniq(chat_lines)[-12:]


def intent_clarify_enabled() -> bool:
    return _env_truthy("RESEARCH_INTENT_CLARIFY", "true")


def find_ambiguous_hits(task: str) -> list[dict[str, str]]:
    """Acronyms in task whose tech/finance senses differ and are not yet clarified."""
    hits: list[dict[str, str]] = []
    for token, mapping in _ACRONYM_MAP.items():
        tech = mapping.get("tech") or ""
        finance = mapping.get("finance") or ""
        if not tech or tech == finance:
            continue
        if not _token_in_text(token, task or ""):
            continue
        if token == "SSE" and re.search(
            r"(?i)server[- ]?sent|eventsource|上海证券|stock\s*exchange|上交所",
            task or "",
        ):
            continue
        hits.append({"token": token, "tech": tech, "finance": finance})
    return hits


def _history_strength(blobs: list[str]) -> tuple[str, int, int]:
    joined = "\n".join(b for b in blobs if b)
    tech = len(_TECH_HINT_RE.findall(joined))
    finance = len(_FINANCE_HINT_RE.findall(joined))
    if finance >= tech + 2 and finance > 0:
        return "finance", tech, finance
    if tech >= finance + 1 and tech > 0:
        return "tech", tech, finance
    if tech > 0 and tech >= finance:
        return "tech", tech, finance
    return "weak", tech, finance


def apply_sense_to_task(task: str, *, token: str, sense_label: str) -> str:
    """Force a concrete sense into the task string for planning/search."""
    base = (task or "").strip()
    if sense_label.lower() in base.lower():
        return base
    return f"{base}（指：{sense_label}）"


async def build_planning_context_for_job(
    *,
    task: str,
    user_id: str,
    report_store: Any = None,
    parent_chat_id: Optional[str] = None,
    client_messages: Optional[list[dict]] = None,
    force_domain: Optional[str] = None,
) -> dict[str, Any]:
    if not planning_user_context_enabled():
        return {
            "domain_preference": default_domain_preference(),
            "expanded_task": task,
            "planning_hint": "",
            "disambiguation_notes": [],
            "action": "proceed",
            "confidence": "high",
        }
    titles, chats = await collect_user_recent_signals(
        report_store=report_store,
        user_id=user_id,
        parent_chat_id=parent_chat_id,
        client_messages=client_messages,
    )
    preference = force_domain if force_domain in {"tech", "finance"} else None
    hint = build_planning_hint(
        task=task,
        recent_titles=titles,
        recent_chat_lines=chats,
        preference=preference,
    )
    hint["action"] = "proceed"
    hint["confidence"] = "medium"
    return hint


async def resolve_report_intent(
    *,
    task: str,
    user_id: str,
    report_store: Any = None,
    parent_chat_id: Optional[str] = None,
    client_messages: Optional[list[dict]] = None,
    force_domain: Optional[str] = None,
    force_sense: Optional[str] = None,
) -> dict[str, Any]:
    """
    Decide proceed vs clarify before creating a research Job.

    - Ambiguous acronym + weak history → ask user (when RESEARCH_INTENT_CLARIFY)
    - Strong history / force_domain / force_sense → auto-expand and proceed
    """
    task = (task or "").strip()
    if not planning_user_context_enabled():
        return {
            "action": "proceed",
            "confidence": "high",
            "domain_preference": default_domain_preference(),
            "expanded_task": task,
            "planning_hint": "",
            "disambiguation_notes": [],
            "ambiguous_tokens": [],
            "history_scores": {"tech": 0, "finance": 0},
        }

    titles, chats = await collect_user_recent_signals(
        report_store=report_store,
        user_id=user_id,
        parent_chat_id=parent_chat_id,
        client_messages=client_messages,
    )
    blobs = [*titles, *chats, task]
    strength, tech_n, finance_n = _history_strength(blobs)
    hits = find_ambiguous_hits(task)

    # Explicit sense from UI (user picked an option). :-)
    if force_sense and hits:
        token = hits[0]["token"]
        expanded = apply_sense_to_task(task, token=token, sense_label=force_sense)
        domain = (
            "finance"
            if re.search(r"(?i)stock|exchange|证券|上交所", force_sense)
            else "tech"
        )
        hint = build_planning_hint(
            task=expanded,
            recent_titles=titles,
            recent_chat_lines=chats,
            preference=domain,
        )
        return {
            **hint,
            "action": "proceed",
            "confidence": "high",
            "expanded_task": expanded,
            "ambiguous_tokens": [h["token"] for h in hits],
            "history_scores": {"tech": tech_n, "finance": finance_n},
        }

    if force_domain in {"tech", "finance"}:
        hint = build_planning_hint(
            task=task,
            recent_titles=titles,
            recent_chat_lines=chats,
            preference=force_domain,
        )
        return {
            **hint,
            "action": "proceed",
            "confidence": "high",
            "ambiguous_tokens": [h["token"] for h in hits],
            "history_scores": {"tech": tech_n, "finance": finance_n},
        }

    if not hits:
        hint = build_planning_hint(
            task=task, recent_titles=titles, recent_chat_lines=chats
        )
        return {
            **hint,
            "action": "proceed",
            "confidence": "high",
            "ambiguous_tokens": [],
            "history_scores": {"tech": tech_n, "finance": finance_n},
        }

    # Strong history signal → auto disambiguate
    if strength in {"tech", "finance"}:
        hint = build_planning_hint(
            task=task,
            recent_titles=titles,
            recent_chat_lines=chats,
            preference=strength,
        )
        return {
            **hint,
            "action": "proceed",
            "confidence": "high",
            "ambiguous_tokens": [h["token"] for h in hits],
            "history_scores": {"tech": tech_n, "finance": finance_n},
            "auto_reason": f"history_{strength}",
        }

    # Weak / no history: ask unless clarify disabled (then tech-first). :-)
    if intent_clarify_enabled():
        options = []
        for h in hits:
            for domain_key, label in (("tech", h["tech"]), ("finance", h["finance"])):
                options.append(
                    {
                        "id": f"{h['token'].lower()}_{domain_key}",
                        "token": h["token"],
                        "domain": domain_key,
                        "label": label,
                        "resolved_task": apply_sense_to_task(
                            task, token=h["token"], sense_label=label
                        ),
                    }
                )
        # de-dupe labels
        seen_labels: set[str] = set()
        uniq_opts = []
        for opt in options:
            if opt["label"] in seen_labels:
                continue
            seen_labels.add(opt["label"])
            uniq_opts.append(opt)
        token_list = ", ".join(h["token"] for h in hits)
        question = (
            f"你提到的「{token_list}」可能有多种含义。请确认要调研哪一个？\n"
            + "\n".join(
                f"{i + 1}) {opt['label']}" for i, opt in enumerate(uniq_opts)
            )
        )
        return {
            "action": "clarify",
            "confidence": "low",
            "task": task,
            "expanded_task": task,
            "planning_hint": "",
            "disambiguation_notes": [],
            "domain_preference": default_domain_preference(),
            "ambiguous_tokens": [h["token"] for h in hits],
            "options": uniq_opts,
            "clarification_question": question,
            "history_scores": {"tech": tech_n, "finance": finance_n},
        }

    hint = build_planning_hint(
        task=task,
        recent_titles=titles,
        recent_chat_lines=chats,
        preference="tech",
    )
    return {
        **hint,
        "action": "proceed",
        "confidence": "medium",
        "ambiguous_tokens": [h["token"] for h in hits],
        "history_scores": {"tech": tech_n, "finance": finance_n},
        "auto_reason": "default_tech_first",
    }
