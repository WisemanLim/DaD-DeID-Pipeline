"""DaD DeID Pipeline deid — 검출 → 정책 → 변환 게이트.

POST /deid    : 텍스트 비식별 (regex+Luhn 검출 → 정책 매핑 → 변환)
POST /process : 문서 청킹 + 청크별 비식별 → ChunkMetadata + Langfuse 호환 trace (Epic 4/6)
GET  /rules   : 적재된 룰 요약 (industry_code 별)
GET  /metrics : PRD §5 운영지표 누적 (Epic 6)
GET  /health  : 헬스체크
"""
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.core.config import settings
from app.detect.composite import CompositeDetector
from app.detect.detector import Detector
from app.observability import MetricsRegistry, Trace
from app.pipeline import ChunkRecord, Pipeline
from app.policy.engine import PolicyEngine
from app.detect.rules import RuleBundleLoader
from app.transform.transformer import Transformer, TokenVault

app = FastAPI(title="DaD DeID Pipeline deid", version="0.1.0")

_loader = RuleBundleLoader(settings.seed_dir, settings.default_locale)
_policy = PolicyEngine()
_vault = TokenVault()
_metrics = MetricsRegistry()
_pipeline = Pipeline(_loader, _vault, _metrics)


class DeidRequest(BaseModel):
    text: str
    industry_code: str | None = Field(
        default=None, description="seed 도메인 id (예: manufacturing-chemical, finance-banking)"
    )


class DetectionOut(BaseModel):
    rule_id: str
    category: str
    sub_category: str | None
    action: str                 # deid 액션
    sensitivity: str
    start: int
    end: int


class DeidResponse(BaseModel):
    industry_code: str | None
    sensitivity_level: str
    export_blocked: bool
    detections: list[DetectionOut]
    transformed_text: str
    stats: dict


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "deid", "env": settings.env}


@app.get("/rules")
def rules(industry_code: str | None = None) -> dict:
    rs = _loader.load(industry_code)
    detector = Detector(rs)
    return {
        "industry_code": industry_code,
        "total": len(rs),
        "detectable_regex": len(detector._compiled),
        "unsupported_pattern_types": detector.unsupported,
    }


class ProcessRequest(BaseModel):
    text: str
    document_id: str
    industry_code: str | None = None
    project_id: str = "default"
    owner: str = "unknown"
    source_uri: str = ""


class ProcessResponse(BaseModel):
    document_id: str
    doc_sensitivity_level: str
    chunk_count: int
    chunks: list[ChunkRecord]
    trace: Trace                # Langfuse 호환 trace (PRD §7)


@app.post("/process", response_model=ProcessResponse)
def process(req: ProcessRequest) -> ProcessResponse:
    """문서 → 청킹 → 청크별 비식별 → ChunkMetadata (rag /index 로 인덱싱 가능)."""
    chunks, doc_level, trace = _pipeline.process(
        req.text, req.document_id, req.industry_code,
        req.project_id, req.owner, req.source_uri,
    )
    from app.langfuse_sink import emit
    emit(trace)                          # best-effort (LANGFUSE_HOST 설정 시)
    return ProcessResponse(
        document_id=req.document_id, doc_sensitivity_level=doc_level,
        chunk_count=len(chunks), chunks=chunks, trace=trace,
    )


class ProcessImageRequest(BaseModel):
    image_base64: str
    document_id: str
    industry_code: str | None = None
    project_id: str = "default"
    owner: str = "unknown"


class ProcessImageResponse(ProcessResponse):
    ocr_mean_confidence: float
    ocr_low_confidence: bool       # 손글씨 등 신뢰도 미달 → 재검 권고


@app.post("/process-image", response_model=ProcessImageResponse)
def process_image(req: ProcessImageRequest) -> ProcessImageResponse:
    """이미지(손글씨 포함) → OCR → 동일 비식별 (PRD §3 ⓓ / 시나리오3, applies_to=OCR)."""
    import base64

    from app.ocr import ocr_image

    result = ocr_image(base64.b64decode(req.image_base64))
    chunks, doc_level, trace = _pipeline.process(
        result.text, req.document_id, req.industry_code,
        req.project_id, req.owner, source_uri=f"ocr://{req.document_id}",
        document_type="image/ocr",
    )
    return ProcessImageResponse(
        document_id=req.document_id, doc_sensitivity_level=doc_level,
        chunk_count=len(chunks), chunks=chunks, trace=trace,
        ocr_mean_confidence=result.mean_confidence, ocr_low_confidence=result.low_confidence,
    )


class GuardRequest(BaseModel):
    text: str
    io_type: str = "input"          # input | output
    industry_code: str | None = None
    ml: bool = False                # classifier 룰 ML 판정(임베딩) 추가
    ml_threshold: float = 0.6
    llm: bool = False               # LLM(Claude) 정밀 판정 — ml 매치 룰 확인 (ANTHROPIC_API_KEY 필요)


_judge_cache: dict[str | None, object] = {}


def _get_judge(industry_code):
    from app.detect.classifier_judge import ClassifierJudge
    from app.guardrail import _GUARD_CATEGORIES

    if industry_code not in _judge_cache:
        _judge_cache[industry_code] = ClassifierJudge(
            _loader.load(industry_code), categories=_GUARD_CATEGORIES,
        )
    return _judge_cache[industry_code]


@app.post("/guard")
def guard(req: GuardRequest) -> dict:
    """런타임 가드레일 (Epic 7) — I/O 정책 위반 차단/거부/면책고지. ml=true 시 classifier 임베딩 판정 추가."""
    from app.guardrail import _ACTION_TO_DECISION, Decision, GuardMatch, GuardrailEngine

    engine = GuardrailEngine(_loader.load(req.industry_code))
    result = engine.evaluate(req.text, req.io_type)

    if req.ml:
        judged = _get_judge(req.industry_code).judge(req.text, req.ml_threshold)
        rules_by_id = {r.ruleId: r for r in _loader.load(req.industry_code)}
        for j in judged:
            # llm=true 면 Claude 로 정밀 확인(키 있을 때만; 미가용이면 ML 결과 유지)
            if req.llm:
                from app.detect.llm_judge import judge as llm_judge
                rule = rules_by_id.get(j.rule_id)
                if rule is not None:
                    v = llm_judge(req.text, rule)
                    if v.available and not v.violates:
                        continue        # LLM 이 위반 아님으로 판정 → 매치 제외
            dec = _ACTION_TO_DECISION.get(j.action, Decision.WARN)
            result.matches.append(GuardMatch(
                rule_id=j.rule_id, category=j.category, decision=dec.name,
                message=f"ML 판정({j.score})",
            ))
        if result.matches:
            top = max(Decision[m.decision] for m in result.matches)
            result.decision = top.name
            result.allowed = top < Decision.REFUSE
            result.messages = [m.message for m in result.matches]

    _metrics.inc("guard_eval_total")
    if not result.allowed:
        _metrics.inc("guard_blocked_total")
    return result.model_dump()


@app.get("/domains")
def domains() -> dict:
    """KSIC 섹션별 적재 가능한 도메인 오버레이 번들 (Epic 5)."""
    by_sec = _loader.domains_by_section()
    return {
        "sections": by_sec,
        "ksic_map": {"C": "제조", "K": "금융", "Q": "의료", "O": "공공", "R": "예술", "J": "ICT(베이스라인)"},
    }


class ProcessDocumentRequest(BaseModel):
    file_base64: str
    content_type: str               # application/pdf | ...wordprocessingml... | text/plain
    document_id: str
    industry_code: str | None = None
    project_id: str = "default"
    owner: str = "unknown"


@app.post("/process-document", response_model=ProcessResponse)
def process_document(req: ProcessDocumentRequest) -> ProcessResponse:
    """PDF/DOCX/TXT → 파싱 → 비식별 (PRD 파서 어댑터 활용)."""
    import base64

    from app.parsers import parse_document

    text = parse_document(base64.b64decode(req.file_base64), req.content_type)
    chunks, doc_level, trace = _pipeline.process(
        text, req.document_id, req.industry_code,
        req.project_id, req.owner, source_uri=f"doc://{req.document_id}",
        document_type=req.content_type,
    )
    return ProcessResponse(
        document_id=req.document_id, doc_sensitivity_level=doc_level,
        chunk_count=len(chunks), chunks=chunks, trace=trace,
    )


@app.get("/metrics")
def metrics() -> dict:
    """PRD §5 운영지표 누적 (entities_detected_total·transform_rate_avg·documents_processed_total 등)."""
    return _metrics.snapshot()


@app.post("/deid", response_model=DeidResponse)
def deid(req: DeidRequest) -> DeidResponse:
    rules = _loader.load(req.industry_code)
    detector = CompositeDetector(
        rules, settings.default_locale, settings.enable_ner, settings.enable_dict,
    )
    transformer = Transformer(_vault)

    detections = detector.detect(req.text)
    decisions = [_policy.decide(d) for d in detections]
    level = _policy.overall_sensitivity(decisions)
    transformed = transformer.transform(req.text, decisions)

    return DeidResponse(
        industry_code=req.industry_code,
        sensitivity_level=level.value,
        export_blocked=_policy.export_blocked(level),
        detections=[
            DetectionOut(
                rule_id=p.detection.rule_id, category=p.detection.category,
                sub_category=p.detection.sub_category, action=p.action.value,
                sensitivity=p.sensitivity.value, start=p.detection.start, end=p.detection.end,
            )
            for p in decisions
        ],
        transformed_text=transformed,
        stats={
            "entities_detected_total": len(detections),
            "transform_rate_avg": 1.0 if detections else 0.0,
            "vault_entries": len(_vault),
        },
    )
