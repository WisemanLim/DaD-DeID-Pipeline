"""Dictionary 검출기 (Epic 1) — 용어 사전 기반 영업비밀/민감어 검출.

regex/NER 가 못 잡는 도메인 고정 용어(영업비밀 키워드 등) 매칭. 업종별 사전 확장 가능.
seed 의 dictionary patternType 룰 + 내장 도메인 렉시콘 결합.
"""
from __future__ import annotations

import re

from app.detect.detector import Detection
from app.detect.rules import Rule

# 내장 도메인 렉시콘 — {term: (category, subCategory, severity, action)}
BUILTIN_LEXICON: dict[str, tuple[str, str, str, str]] = {
    # 제조 영업비밀
    "촉매비율": ("ip", "catalyst_ratio_secret", "critical", "block_or_redact"),
    "배합비율": ("ip", "formulation_secret", "critical", "block_or_redact"),
    "합성루트": ("ip", "synthesis_route_secret", "critical", "block_or_redact"),
    "공정파라미터": ("ip", "process_param_secret", "high", "redact"),
    "반응압력": ("ip", "process_param_secret", "high", "redact"),
    # 금융
    "내부자정보": ("compliance", "insider_info", "critical", "block"),
}


def _terms_to_rules(lexicon: dict) -> list[tuple[re.Pattern, str, str, str, str]]:
    out = []
    for term, (cat, sub, sev, action) in lexicon.items():
        out.append((re.compile(re.escape(term)), cat, sub, sev, action))
    return out


class DictionaryDetector:
    def __init__(self, rules: list[Rule] | None = None, lexicon: dict | None = None) -> None:
        self._compiled = _terms_to_rules(lexicon or BUILTIN_LEXICON)
        # seed dictionary 룰의 regex 도 흡수(있으면)
        self._seed = [
            (re.compile(p), r) for r in (rules or [])
            if r.patternType == "dictionary" and r.enabled for p in r.patterns.regex
        ]

    def detect(self, text: str) -> list[Detection]:
        out: list[Detection] = []
        for pattern, cat, sub, sev, action in self._compiled:
            for m in pattern.finditer(text):
                out.append(Detection(
                    rule_id=f"DICT_{sub}", category=cat, sub_category=sub,
                    action=action, severity=sev, start=m.start(), end=m.end(),
                    text=m.group(), regulation_tags=["TRADE_SECRET"] if cat == "ip" else [],
                ))
        for pattern, rule in self._seed:
            for m in pattern.finditer(text):
                out.append(Detection(
                    rule_id=rule.ruleId, category=rule.category, sub_category=rule.subCategory,
                    action=rule.action, severity=rule.severity, start=m.start(), end=m.end(),
                    text=m.group(), regulation_tags=rule.regulationTags,
                ))
        return out
