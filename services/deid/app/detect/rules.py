"""룰번들 로더/레지스트리 (Epic 0).

seed(.docs/seed/*.json) 스키마 적재 + 베이스라인 privacy 보강 룰.
베이스라인 = global + privacy(내장), 오버레이 = 업종(industry_code) seed 파일.
patternType=regex 만 이번 슬라이스에서 활성. classifier/ner/dictionary 는 skip(로깅).
"""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field


class Patterns(BaseModel):
    regex: list[str] = Field(default_factory=list)
    luhnCheck: bool = False


class Rule(BaseModel):
    ruleId: str
    domain: str = "global"
    locale: str = "ko-KR"
    ioType: str = "both"
    category: str                       # pii|credentials|financial|sensitive|ip|safety|compliance|fraud
    subCategory: str | None = None
    description: str = ""
    patternType: str = "regex"          # regex|regex+classifier|classifier|ner|dictionary
    patterns: Patterns = Field(default_factory=Patterns)
    severity: str = "medium"            # low|medium|high|critical
    priority: int = 500
    action: str = "redact"              # seed 가드레일 액션(block/redact/...) — 정책엔진이 deid 액션으로 매핑
    regulationTags: list[str] = Field(default_factory=list)
    examplesPositive: list[str] = Field(default_factory=list)   # classifier ML 판정 앵커
    enabled: bool = True
    version: str = "1.0.0"

    @property
    def detectable(self) -> bool:
        """이번 슬라이스에서 검출 가능 = 정규식 보유."""
        return self.enabled and bool(self.patterns.regex)


# --- 베이스라인 privacy 보강 룰 (seed financial 다수가 classifier → regex+luhn 보강) ---
BASELINE_PRIVACY: list[dict] = [
    {
        "ruleId": "PRIV_FIN_CARD_001", "domain": "privacy", "category": "financial",
        "subCategory": "card_pan", "description": "신용카드 PAN (Luhn 검증)",
        "patternType": "regex+classifier",
        "patterns": {"regex": [r"\b(?:\d[ -]?){13,19}\b"], "luhnCheck": True},
        "severity": "critical", "priority": 940, "action": "block_or_pseudonymize",
        "regulationTags": ["PCI_DSS", "KR_CCA"], "version": "1.0.0",
    },
    {
        "ruleId": "PRIV_FIN_ACCT_KR_001", "domain": "privacy", "category": "financial",
        "subCategory": "bank_account_kr", "description": "은행 계좌번호(국내)",
        "patternType": "regex",
        "patterns": {"regex": [r"\b\d{3,6}-\d{2,6}-\d{1,6}\b"]},
        "severity": "high", "priority": 880, "action": "redact",
        "regulationTags": ["KR_CCA"], "version": "1.0.0",
    },
]


class RuleBundleLoader:
    """seed 디렉터리 + 베이스라인에서 룰을 적재해 industry_code 별로 합성."""

    def __init__(self, seed_dir: str, locale: str = "kr") -> None:
        self.seed_dir = Path(seed_dir)
        self.locale = locale
        self._cache: dict[str, list[Rule]] = {}

    def _load_file(self, domain: str) -> list[Rule]:
        path = self.seed_dir / f"{domain}.{self.locale}.json"
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        rules = data.get("rules", []) if isinstance(data, dict) else data
        out: list[Rule] = []
        for r in rules:
            try:
                out.append(Rule(**r))
            except Exception:  # noqa: BLE001 — 스키마 외 룰은 skip
                continue
        return out

    def baseline(self) -> list[Rule]:
        """global(seed) + privacy(seed, 없으면 내장 fallback)."""
        privacy = self._load_file("privacy") or [Rule(**r) for r in BASELINE_PRIVACY]
        return self._load_file("global") + privacy

    def domains_by_section(self) -> dict[str, list[str]]:
        """seed 디렉터리 스캔 → KSIC 섹션별 서브도메인 번들 목록 (Epic 5)."""
        out: dict[str, list[str]] = {}
        if not self.seed_dir.exists():
            return out
        for p in sorted(self.seed_dir.glob(f"*.{self.locale}.json")):
            dom = p.name[: -len(f".{self.locale}.json")]
            sec = _SECTION_OF.get(dom.split("-")[0])
            if sec:
                out.setdefault(sec, []).append(dom)
        return out

    def load(self, industry_code: str | None = None) -> list[Rule]:
        """베이스라인 + 업종 오버레이. industry_code = 서브도메인(manufacturing-chemical)
        또는 KSIC 섹션 1글자(C → 해당 섹션 전 서브도메인 병합). priority 내림차순."""
        key = industry_code or "_baseline"
        if key in self._cache:
            return self._cache[key]
        rules = self.baseline()
        if industry_code:
            if len(industry_code) == 1:                       # KSIC 섹션
                for dom in self.domains_by_section().get(industry_code.upper(), []):
                    rules += self._load_file(dom)
            else:                                             # 특정 서브도메인
                rules += self._load_file(industry_code)
        rules = [r for r in rules if r.enabled]
        rules.sort(key=lambda r: r.priority, reverse=True)
        self._cache[key] = rules
        return rules


# 도메인 prefix → KSIC 섹션 (Epic 5 오버레이)
_SECTION_OF = {
    "manufacturing": "C", "finance": "K", "healthcare": "Q",
    "public": "O", "arts": "R",
}
