"""Per-stage traces for Planner / Evidence / Claim / Writer / Synthesis / Audit."""

from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from typing import Any, Iterator, Optional


STAGES = (
    "planner",
    "evidence",
    "claim",
    "writer",
    "synthesis",
    "audit",
    "research_only",
    "legacy_write",
)


@dataclass
class StageSpan:
    stage: str
    span_id: str
    started_at: float
    ended_at: Optional[float] = None
    ok: bool = True
    error: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        if self.ended_at is None:
            return 0.0
        return round((self.ended_at - self.started_at) * 1000.0, 2)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["duration_ms"] = self.duration_ms
        return d


@dataclass
class PipelineTrace:
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    spans: list[StageSpan] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "spans": [s.to_dict() for s in self.spans],
            "by_stage": {
                s.stage: s.to_dict()
                for s in self.spans
                if s.stage in STAGES
            },
            "total_duration_ms": round(sum(s.duration_ms for s in self.spans), 2),
        }


_CURRENT: list[PipelineTrace] = []


def current_trace() -> Optional[PipelineTrace]:
    return _CURRENT[-1] if _CURRENT else None


@contextmanager
def pipeline_trace_scope(trace: Optional[PipelineTrace] = None) -> Iterator[PipelineTrace]:
    tr = trace or PipelineTrace()
    _CURRENT.append(tr)
    try:
        yield tr
    finally:
        _CURRENT.pop()


@contextmanager
def stage_span(stage: str, **meta: Any) -> Iterator[StageSpan]:
    tr = current_trace()
    span = StageSpan(
        stage=stage,
        span_id=uuid.uuid4().hex[:12],
        started_at=time.time(),
        meta=dict(meta),
    )
    try:
        yield span
        span.ok = True
    except Exception as exc:
        span.ok = False
        span.error = str(exc)[:400]
        raise
    finally:
        span.ended_at = time.time()
        if tr is not None:
            tr.spans.append(span)
