"""복합 검출기 (Epic 1) — regex(+Luhn) + NER(spaCy) + dictionary 병합 + 겹침 해소.

regex 는 항상, NER/dictionary 는 토글. 단일 Detection 리스트로 통합 후 위치순 정렬·겹침 제거.
"""
from __future__ import annotations

from app.detect.detector import Detection, Detector
from app.detect.dictionary import DictionaryDetector
from app.detect.ner import NerDetector
from app.detect.rules import Rule


class CompositeDetector:
    def __init__(
        self, rules: list[Rule], locale: str = "kr",
        enable_ner: bool = True, enable_dict: bool = True,
    ) -> None:
        self._regex = Detector(rules)
        self._ner = NerDetector(locale) if enable_ner else None
        self._dict = DictionaryDetector(rules) if enable_dict else None
        self.unsupported = self._regex.unsupported

    def detect(self, text: str) -> list[Detection]:
        found: list[Detection] = list(self._regex.detect(text))
        if self._dict:
            found += self._dict.detect(text)
        if self._ner:
            found += self._ner.detect(text)
        # regex 결과는 이미 정렬됐지만 병합 후 재해소
        return Detector._resolve_overlaps(found)
