"""거버넌스 관측 (Epic 6) — Langfuse 호환 trace + KPI 메트릭.

PRD §7 데이터/로깅: trace 상단 = 문서/업종/정책 메타, 하위 span = ocr.parse → deid.detect →
deid.transform → authz.openfga.check → rag.answer. 신규 의존성 없이 stdlib 로 Langfuse 호환
페이로드를 생성. 라이브 연동(LANGFUSE_HOST 설정) 은 후속 — 페이로드는 그대로 langfuse.trace() 입력 가능.
PRD §5 운영지표 = MetricsRegistry 카운터.
"""
from __future__ import annotations

import time
from contextlib import contextmanager

from pydantic import BaseModel, Field


class Span(BaseModel):
    name: str
    duration_ms: float
    metadata: dict = Field(default_factory=dict)


class Trace(BaseModel):
    name: str = "redactflow.deid"
    # PRD §7 trace 상단 태그
    tags: dict = Field(default_factory=dict)   # industry·ksic_section·document_type·sensitivity_level·policy_id
    spans: list[Span] = Field(default_factory=list)


class TraceRecorder:
    """span 타이밍 수집 → Langfuse 호환 Trace 페이로드."""

    def __init__(self, tags: dict) -> None:
        self._trace = Trace(tags=tags)

    @contextmanager
    def span(self, name: str, metadata: dict | None = None):
        start = time.perf_counter()
        meta = dict(metadata or {})
        try:
            yield meta              # 호출부가 결과 메타 채움
        finally:
            self._trace.spans.append(Span(
                name=name, duration_ms=round((time.perf_counter() - start) * 1000, 3),
                metadata=meta,
            ))

    def trace(self) -> Trace:
        return self._trace


class MetricsRegistry:
    """PRD §5 운영지표 누적 카운터 (프로세스 수명 동안)."""

    def __init__(self) -> None:
        self._c: dict[str, float] = {}

    def inc(self, name: str, n: float = 1) -> None:
        self._c[name] = self._c.get(name, 0) + n

    def snapshot(self) -> dict:
        c = dict(self._c)
        detected = c.get("entities_detected_total", 0)
        transformed = c.get("entities_transformed_total", 0)
        c["transform_rate_avg"] = round(transformed / detected, 4) if detected else 0.0
        return c
