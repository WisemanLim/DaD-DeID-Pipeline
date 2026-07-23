"""NER 검출기 (Epic 1) — spaCy 기반 인명/지명/기관 검출.

regex 가 못 잡는 비정형 식별자(이름·주소·기관) 보강. KR=ko_core_news_sm, EN=en_core_web_sm.
모델 lazy-load(최초 1회). spaCy 엔티티 라벨 → pii 서브카테고리 매핑.
"""
from __future__ import annotations

from functools import lru_cache

from app.detect.detector import Detection

# spaCy 라벨 → (subCategory). EN: PERSON/GPE/LOC/ORG, KR(ko): PS/LC/OG
_LABEL_MAP = {
    "PERSON": "person_name", "PS": "person_name",
    "GPE": "location", "LOC": "location", "LC": "location",
    "ORG": "organization", "OG": "organization",
}

_MODEL_BY_LOCALE = {"kr": "ko_core_news_sm", "en": "en_core_web_sm"}


@lru_cache(maxsize=4)
def _load(model_name: str):
    import spacy
    return spacy.load(model_name, disable=["lemmatizer"])


class NerDetector:
    def __init__(self, locale: str = "kr") -> None:
        self.model_name = _MODEL_BY_LOCALE.get(locale, "ko_core_news_sm")

    def detect(self, text: str) -> list[Detection]:
        nlp = _load(self.model_name)
        out: list[Detection] = []
        for ent in nlp(text).ents:
            sub = _LABEL_MAP.get(ent.label_)
            if not sub:
                continue
            out.append(Detection(
                rule_id=f"NER_{ent.label_}", category="pii", sub_category=sub,
                action="redact", severity="medium",
                start=ent.start_char, end=ent.end_char, text=ent.text,
                regulation_tags=["KR_PIPA"],
            ))
        return out
