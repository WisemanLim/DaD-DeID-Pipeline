"""런타임 가드레일 (Epic 7, 후속) — I/O block/refuse/warn/add_disclaimer.

PRD §3 가드레일 액션 + ioType(input/output/both). 비식별(REMOVE/MASK..)과 별개로,
LLM 입출력을 정책 위반(safety/compliance/fraud)으로 차단·거부·면책고지한다.
매칭 = regex 룰(ioType 일치) + 내장 가드레일 렉시콘. classifier 룰의 ML 판정은 후속.
"""
from __future__ import annotations

import re
from enum import IntEnum

from pydantic import BaseModel

from app.detect.rules import Rule

# 가드레일 카테고리 — 비식별이 아니라 I/O 통제 대상
_GUARD_CATEGORIES = {"safety", "compliance", "fraud"}


class Decision(IntEnum):
    """우선순위 = 값(높을수록 강함). 최종 결정 = 매칭 중 최대."""
    ALLOW = 0
    WARN = 1
    ADD_DISCLAIMER = 2
    REDACT = 3
    REFUSE = 4
    BLOCK = 5


# seed 가드레일 action → Decision
_ACTION_TO_DECISION = {
    "allow": Decision.ALLOW, "warn": Decision.WARN,
    "add_disclaimer": Decision.ADD_DISCLAIMER, "sanitize": Decision.REDACT,
    "redact": Decision.REDACT, "aggregate_only": Decision.REDACT,
    "block_or_redact": Decision.BLOCK, "block_or_pseudonymize": Decision.BLOCK,
    "refuse": Decision.REFUSE, "block": Decision.BLOCK,
}

# 내장 가드레일 렉시콘 (입력 차단/거부) — {term: (decision, category, message)}
BUILTIN_GUARD: dict[str, tuple[Decision, str, str]] = {
    "자금세탁": (Decision.BLOCK, "fraud", "자금세탁 관련 요청은 차단됩니다."),
    "KYC 없이": (Decision.REFUSE, "compliance", "고객확인(KYC) 우회 지원 불가."),
    "kyc 우회": (Decision.REFUSE, "compliance", "고객확인(KYC) 우회 지원 불가."),
    "내부자": (Decision.BLOCK, "compliance", "내부자 정보 관련 요청 차단."),
    "REACH 등록 없이": (Decision.BLOCK, "compliance", "REACH 미등록 EU 수출 권유 차단."),
    "폭발물 제조": (Decision.BLOCK, "safety", "위험물 제조 정보 제공 불가."),
}


class GuardMatch(BaseModel):
    rule_id: str
    category: str
    decision: str
    message: str


class GuardResult(BaseModel):
    decision: str                  # ALLOW/WARN/ADD_DISCLAIMER/REDACT/REFUSE/BLOCK
    allowed: bool                  # BLOCK/REFUSE 면 False
    matches: list[GuardMatch]
    messages: list[str]


class GuardrailEngine:
    def __init__(self, rules: list[Rule]) -> None:
        # ioType 별 regex 가드레일 룰(가드 카테고리 한정)
        self._rules = [
            (re.compile(p), r) for r in rules
            if r.enabled and r.category in _GUARD_CATEGORIES
            for p in r.patterns.regex
        ]
        self._lex = [(re.compile(re.escape(t), re.I), t, d, c, m)
                     for t, (d, c, m) in BUILTIN_GUARD.items()]

    @staticmethod
    def _io_ok(rule_io: str, want: str) -> bool:
        return rule_io in (want, "both")

    def evaluate(self, text: str, io_type: str = "input") -> GuardResult:
        matches: list[GuardMatch] = []
        for pattern, rule in self._rules:
            if not self._io_ok(rule.ioType, io_type):
                continue
            if pattern.search(text):
                dec = _ACTION_TO_DECISION.get(rule.action, Decision.WARN)
                matches.append(GuardMatch(
                    rule_id=rule.ruleId, category=rule.category,
                    decision=dec.name, message=rule.description or rule.action,
                ))
        for pattern, _term, dec, cat, msg in self._lex:
            if pattern.search(text):
                matches.append(GuardMatch(
                    rule_id=f"GUARD_{cat}", category=cat, decision=dec.name, message=msg,
                ))
        if matches:
            top = max(Decision[m.decision] for m in matches)
        else:
            top = Decision.ALLOW
        return GuardResult(
            decision=top.name,
            allowed=top < Decision.REFUSE,
            matches=matches,
            messages=[m.message for m in matches],
        )
