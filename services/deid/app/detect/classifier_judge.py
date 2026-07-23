"""classifier 룰 ML 판정 (Epic 1/7) — 임베딩 margin 기반.

seed classifier 룰(정규식 없음)을 examplesPositive 앵커로 임베딩. 다국어 임베딩 모델은 한국어
절대 코사인 baseline 이 높아(무관 문장도 ~0.88) 절대 임계가 부적합 → **benign 앵커 대비 margin**
(rule_sim - benign_sim)으로 판정. margin ≥ threshold 면 의도 위반으로 매칭 → 룰 action.
NER/regex 가 못 잡는 의도 기반 위반(AML/KYC 우회 등) 포착.
"""
from __future__ import annotations

from pydantic import BaseModel

from app.detect.embedder import cosine, get_embedder
from app.detect.rules import Rule

# benign 기준 앵커 — 정상 질의 baseline (margin 보정용)
_BENIGN = [
    "오늘 날씨 어때", "점심 메뉴 추천", "일반 상품 안내",
    "이자율 알려줘", "감사합니다", "사용법 문의",
]


class JudgeMatch(BaseModel):
    rule_id: str
    category: str
    sub_category: str | None
    action: str
    score: float          # margin (rule_sim - benign_sim)


class ClassifierJudge:
    def __init__(self, rules: list[Rule], categories: set[str] | None = None) -> None:
        self._emb = get_embedder()
        self._benign = [self._emb.embed(b) for b in _BENIGN]
        # classifier 룰(정규식 없음) 중 examplesPositive 보유, (선택) 카테고리 필터
        self._anchors: list[tuple[Rule, list[list[float]]]] = []
        targets = [
            r for r in rules
            if r.enabled and not r.patterns.regex and r.examplesPositive
            and (categories is None or r.category in categories)
        ]
        if not targets:
            return
        flat: list[str] = []
        spans: list[tuple[Rule, int, int]] = []
        for r in targets:
            ex = r.examplesPositive[:3]            # 룰당 최대 3 앵커(비용 제한)
            spans.append((r, len(flat), len(flat) + len(ex)))
            flat.extend(ex)
        embed_many = getattr(self._emb, "embed_many", None)
        vecs = embed_many(flat) if embed_many else [self._emb.embed(t) for t in flat]
        for r, lo, hi in spans:
            self._anchors.append((r, vecs[lo:hi]))

    def judge(self, text: str, threshold: float = 0.01) -> list[JudgeMatch]:
        """threshold = margin(rule_sim - benign_sim) 하한. 기본 0.01."""
        if not self._anchors:
            return []
        q = self._emb.embed(text)
        benign_sim = max(cosine(q, b) for b in self._benign) if self._benign else 0.0
        out: list[JudgeMatch] = []
        for rule, anchors in self._anchors:
            margin = max(cosine(q, a) for a in anchors) - benign_sim
            if margin >= threshold:
                out.append(JudgeMatch(
                    rule_id=rule.ruleId, category=rule.category, sub_category=rule.subCategory,
                    action=rule.action, score=round(margin, 4),
                ))
        out.sort(key=lambda m: m.score, reverse=True)
        return out
