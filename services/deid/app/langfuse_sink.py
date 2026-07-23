"""Langfuse 라이브 sink (Epic 6) — LANGFUSE_HOST 설정 시 trace 전송, 아니면 no-op.

best-effort: SDK 미설치/서버 부재/네트워크 오류는 조용히 무시(파이프라인 차단 금지).
trace 페이로드는 observability.Trace (Langfuse 호환). 키는 env(LANGFUSE_PUBLIC_KEY/SECRET_KEY).
"""
from __future__ import annotations

import os

from app.observability import Trace


def emit(trace: Trace) -> bool:
    """Langfuse 로 trace 전송. 성공=True, 비활성/실패=False(예외 삼킴)."""
    host = os.getenv("LANGFUSE_HOST", "").strip()
    pub = os.getenv("LANGFUSE_PUBLIC_KEY", "").strip()
    sec = os.getenv("LANGFUSE_SECRET_KEY", "").strip()
    if not (host and pub and sec):
        return False                      # 미설정 → no-op (오프라인 기본)
    try:
        from langfuse import Langfuse

        client = Langfuse(host=host, public_key=pub, secret_key=sec)
        t = client.trace(name=trace.name, tags=list(trace.tags.values()), metadata=trace.tags)
        for s in trace.spans:
            t.span(name=s.name, metadata=s.metadata)
        client.flush()
        return True
    except Exception:  # noqa: BLE001 — sink 실패가 파이프라인을 막지 않음
        return False
