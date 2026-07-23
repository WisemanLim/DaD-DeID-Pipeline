"""문서 처리 파이프라인 (PRD §1 핵심 플로우).

청킹 → 청크별 검출/정책/변환 → ChunkMetadata 산출(rag /index 계약).
계약 경계 = packages/shared/schema/*.json (마이크로서비스 JSON 계약, python 결합 없음).
민감도(sensitivity_level) = 청크 내 검출들의 최대. transform_action = 적용된 액션 합집합.
lineage = {rule_ids, policy_engine}.
"""
from __future__ import annotations

import re

from pydantic import BaseModel

from app.core.config import settings
from app.detect.composite import CompositeDetector
from app.detect.rules import RuleBundleLoader
from app.observability import MetricsRegistry, Trace, TraceRecorder
from app.policy.engine import PolicyEngine, Sensitivity
from app.transform.transformer import TokenVault, Transformer

# 단순 청커 — 빈 줄(문단) 기준. 후속: 토큰 길이/구조 기반.
_SPLIT = re.compile(r"\n\s*\n")


def chunk_text(text: str) -> list[str]:
    parts = [p.strip() for p in _SPLIT.split(text) if p.strip()]
    return parts or ([text.strip()] if text.strip() else [])


class ChunkRecord(BaseModel):
    text: str           # 비식별된 청크 본문
    metadata: dict      # rag ChunkMetadata 계약과 일치


class Pipeline:
    def __init__(
        self, loader: RuleBundleLoader, vault: TokenVault,
        metrics: MetricsRegistry | None = None,
    ) -> None:
        self.loader = loader
        self.policy = PolicyEngine()
        self.vault = vault
        self.metrics = metrics or MetricsRegistry()

    def process(
        self, text: str, document_id: str, industry_code: str | None,
        project_id: str, owner: str, source_uri: str = "", version: str = "1",
        document_type: str = "text",
    ) -> tuple[list[ChunkRecord], str, Trace]:
        rules = self.loader.load(industry_code)
        detector = CompositeDetector(
            rules, settings.default_locale, settings.enable_ner, settings.enable_dict,
        )
        transformer = Transformer(self.vault)
        recorder = TraceRecorder(tags={
            "industry_code": industry_code or "J",
            "document_id": document_id,
            "document_type": document_type,        # text | image/ocr (PRD applies_to)
            "policy_id": "builtin",
        })

        records: list[ChunkRecord] = []
        doc_level = Sensitivity.PUBLIC
        for i, chunk in enumerate(chunk_text(text)):
            with recorder.span("deid.detect") as m:
                detections = detector.detect(chunk)
                m["entities_detected"] = len(detections)
            decisions = [self.policy.decide(d) for d in detections]
            level = self.policy.overall_sensitivity(decisions)
            with recorder.span("deid.transform") as m:
                transformed = transformer.transform(chunk, decisions)
                m["entities_transformed"] = len(decisions)
            actions = sorted({p.action.value for p in decisions}) or ["NONE"]

            # PRD §5 운영지표
            self.metrics.inc("entities_detected_total", len(detections))
            self.metrics.inc("entities_transformed_total", len(decisions))
            self.metrics.inc("chunks_processed_total")
            if self.policy.export_blocked(level):
                self.metrics.inc("restricted_chunks_total")

            records.append(ChunkRecord(
                text=transformed,
                metadata={
                    "document_id": document_id,
                    "chunk_id": f"{document_id}#{i}",
                    "industry_code": industry_code or "J",
                    "sensitivity_level": level.value,
                    "transform_action": "+".join(actions),
                    "lineage": {
                        "rule_ids": [p.detection.rule_id for p in decisions],
                        "policy_engine": "builtin",
                    },
                    "source_uri": source_uri,
                    "domain": industry_code or "global",
                    "project_id": project_id,
                    "owner": owner,
                    "version": version,
                    "section_path": f"chunk[{i}]",
                },
            ))
            if _RANK[level] > _RANK[doc_level]:
                doc_level = level
        self.metrics.inc("documents_processed_total")
        return records, doc_level.value, recorder.trace()


_RANK = {s: i for i, s in enumerate(Sensitivity)}
