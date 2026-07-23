"""청크 인덱스 메타데이터 스키마 스텁 / chunk index metadata schema stub.

근거: bio-rag-research.index_metadata_min_fields + PRD §3 ⓔ (분리 인덱싱).
민감도(sensitivity_level)별 namespace 분리, lineage 추적, 외부반출 게이트 판단에 사용.
"""
from enum import Enum

from pydantic import BaseModel


class SensitivityLevel(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"        # 외부 LLM 반출 차단
    TRADE_SECRET = "TRADE_SECRET"    # 외부 LLM 반출 차단 (제조 영업비밀)


class ChunkMetadata(BaseModel):
    # --- 분리 인덱싱 핵심 (PRD §3 ⓔ) ---
    document_id: str
    chunk_id: str
    industry_code: str               # KSIC 섹션/도메인 (C/K/Q/O/R/J)
    sensitivity_level: SensitivityLevel
    transform_action: str            # REMOVE/MASK/TOKENIZE/GENERALIZE/RANGE_BUCKET/HASH
    lineage: dict                     # 원문→파생 추적 (source span, rule_id, policy_id)
    # --- 출처/재현성 (bio-rag security_standards.provenance/reproducibility) ---
    source_uri: str
    domain: str
    project_id: str
    owner: str
    version: str
    section_path: str | None = None
    approval_state: str = "auto"     # auto | pending_export | approved
    retention_policy: str | None = None
    indexed_at: str | None = None    # ISO8601 (구현 시 주입)

    def export_blocked(self) -> bool:
        """RESTRICTED/TRADE_SECRET 는 외부 LLM 반출 차단."""
        return self.sensitivity_level in (
            SensitivityLevel.RESTRICTED,
            SensitivityLevel.TRADE_SECRET,
        )
