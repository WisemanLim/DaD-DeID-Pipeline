"""변환기 (Epic 2) — REMOVE/MASK/TOKENIZE/GENERALIZE/RANGE_BUCKET/HASH + token vault.

vault 는 메모리 스텁(config.vault_url=memory://). 실 KMS/HSM 은 PRD 미결정 → 인터페이스 유지.
TOKENIZE/RANGE_BUCKET = 가역(vault 매핑 보관). HASH = 비가역. REMOVE/MASK/GENERALIZE = 손실.
"""
from __future__ import annotations

import hashlib
import re

from app.policy.engine import DeidAction, PolicyDecision

_DATE_RE = re.compile(r"\b(\d{4})[-./]\d{1,2}[-./]\d{1,2}\b")
_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")


class TokenVault:
    """재식별 키/recipe token 매핑. 메모리 스텁 — 전건 접근은 감사 대상(audit 훅 후속)."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def put(self, prefix: str, original: str) -> str:
        token = hashlib.sha256(original.encode()).hexdigest()[:10]
        key = f"{prefix}:{token}"
        self._store[key] = original
        return key

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def __len__(self) -> int:
        return len(self._store)


def _mask(s: str) -> str:
    """끝 4자 노출, 나머지 * (구분자 보존)."""
    visible = 4 if len(re.sub(r"\D", "", s)) > 4 else 0
    out, shown = [], 0
    for ch in reversed(s):
        if ch.isalnum() and shown < visible:
            out.append(ch)
            shown += 1
        elif ch.isalnum():
            out.append("*")
        else:
            out.append(ch)
    return "".join(reversed(out))


def _generalize(s: str) -> str:
    m = _DATE_RE.search(s)
    return m.group(1) if m else "⟨GENERALIZED⟩"


def _range_bucket(s: str) -> str:
    m = _NUM_RE.search(s)
    if not m:
        return "⟨RANGE_BUCKET⟩"
    v = float(m.group())
    lo = (int(v) // 10) * 10
    return f"⟨RANGE:{lo}-{lo + 10}⟩"


class Transformer:
    def __init__(self, vault: TokenVault | None = None) -> None:
        # 빈 vault 는 __len__==0 → falsy. `or` 쓰면 주입 vault 무시되므로 is None 비교.
        self.vault = vault if vault is not None else TokenVault()

    def _apply(self, action: DeidAction, original: str) -> str:
        if action == DeidAction.REMOVE:
            return "[REMOVED]"
        if action == DeidAction.MASK:
            return _mask(original)
        if action == DeidAction.TOKENIZE:
            return f"⟨{self.vault.put('TOK', original)}⟩"
        if action == DeidAction.GENERALIZE:
            return _generalize(original)
        if action == DeidAction.RANGE_BUCKET:
            self.vault.put("RECIPE", original)        # 상세값 vault 보관
            return _range_bucket(original)
        if action == DeidAction.HASH:
            return f"⟨HASH:{hashlib.sha256(original.encode()).hexdigest()[:12]}⟩"
        return original

    def transform(self, text: str, decisions: list[PolicyDecision]) -> str:
        """우→좌로 치환해 오프셋 보존."""
        for p in sorted(decisions, key=lambda d: d.detection.start, reverse=True):
            d = p.detection
            text = text[: d.start] + self._apply(p.action, d.text) + text[d.end :]
        return text
