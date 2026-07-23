"""외부 파서 어댑터 (PRD: Tika/GROBID 활용) — HTTP 서버 연동.

TIKA_URL: Apache Tika 서버(범용 문서→텍스트). GROBID_URL: 과학문서 PDF→TEI.
서버 미설정/미가용이면 None 반환 → parsers.parse_document 가 pypdf/python-docx 로 폴백.
엔진 자체개발 안 함(PRD Out-of-scope) — 어댑터/폴백만. 네트워크 호출은 짧은 타임아웃.
"""
from __future__ import annotations

import os
import re
import urllib.error
import urllib.request

_TIMEOUT = 8


def tika_extract(data: bytes) -> str | None:
    """Tika 서버로 텍스트 추출. PUT /tika, Accept text/plain. 미설정/실패 시 None."""
    base = os.getenv("TIKA_URL", "").strip().rstrip("/")
    if not base:
        return None
    try:
        req = urllib.request.Request(
            f"{base}/tika", data=data, method="PUT",
            headers={"Accept": "text/plain", "Content-Type": "application/octet-stream"},
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return resp.read().decode("utf-8", errors="replace").strip()
    except (urllib.error.URLError, OSError, TimeoutError):
        return None


def grobid_extract(data: bytes) -> str | None:
    """GROBID 로 과학 PDF→TEI 후 본문 텍스트만 추출. 미설정/실패 시 None."""
    base = os.getenv("GROBID_URL", "").strip().rstrip("/")
    if not base:
        return None
    try:
        boundary = "----redactflowgrobid"
        body = (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="input"; filename="doc.pdf"\r\n'
            "Content-Type: application/pdf\r\n\r\n"
        ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
        req = urllib.request.Request(
            f"{base}/api/processFulltextDocument", data=body, method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            tei = resp.read().decode("utf-8", errors="replace")
        return re.sub(r"<[^>]+>", " ", tei)              # TEI 태그 제거(경량)
    except (urllib.error.URLError, OSError, TimeoutError):
        return None
