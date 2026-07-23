"""검출기 (Epic 1) — regex + Luhn. 우선순위·중복(겹침) 해소.

classifier/ner/dictionary 는 미지원 → skip(unsupported 리스트로 보고).
"""
from __future__ import annotations

import re

from pydantic import BaseModel

from app.detect.rules import Rule


class Detection(BaseModel):
    rule_id: str
    category: str
    sub_category: str | None
    action: str                 # seed 가드레일 액션 (정책엔진 입력)
    severity: str
    start: int
    end: int
    text: str
    regulation_tags: list[str]


def luhn_valid(digits: str) -> bool:
    """Luhn 체크섬. 카드/계좌 오탐 축소."""
    nums = [int(c) for c in digits if c.isdigit()]
    if len(nums) < 13:
        return False
    total, parity = 0, len(nums) % 2
    for i, n in enumerate(nums):
        if i % 2 == parity:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


class Detector:
    def __init__(self, rules: list[Rule]) -> None:
        # (compiled regex, rule) — detectable 룰만
        self._compiled = [
            (re.compile(p), r) for r in rules if r.detectable for p in r.patterns.regex
        ]
        self.unsupported = sorted({
            r.patternType for r in rules if r.enabled and not r.detectable
        })

    def detect(self, text: str) -> list[Detection]:
        found: list[Detection] = []
        for pattern, rule in self._compiled:
            for m in pattern.finditer(text):
                if rule.patterns.luhnCheck and not luhn_valid(m.group()):
                    continue
                found.append(Detection(
                    rule_id=rule.ruleId, category=rule.category,
                    sub_category=rule.subCategory, action=rule.action,
                    severity=rule.severity, start=m.start(), end=m.end(),
                    text=m.group(), regulation_tags=rule.regulationTags,
                ))
        return self._resolve_overlaps(found)

    @staticmethod
    def _resolve_overlaps(dets: list[Detection]) -> list[Detection]:
        """겹치는 스팬은 더 긴(=구체적) 매치 우선, 동률이면 먼저. 위치순 반환."""
        ordered = sorted(dets, key=lambda d: (d.start, -(d.end - d.start)))
        kept: list[Detection] = []
        occupied_end = -1
        for d in ordered:
            if d.start >= occupied_end:
                kept.append(d)
                occupied_end = d.end
        return kept
