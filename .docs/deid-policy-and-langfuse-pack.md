# 금융/의료/제조 비식별 설계안

이 문서는 업종별 데이터 비식별 시뮬레이터 설계, 법적 의무 체크리스트, 비식별 처리 정책 JSON 스키마, Langfuse 기반 감사 이벤트 로그 구조를 정리한 초안이다.

## 1. 업종별 최적 기술 및 위험도

### 금융
- 주요 데이터: 계좌번호, 카드번호, 거래내역, 고객식별정보
- 권장 기법: 부분 마스킹, 토큰화, 범주화, 총계처리
- 규제 위험도: High
- 운영 포인트: 제3자 제공 제한, 재식별 금지, 외부 LLM 반출 승인제

### 의료
- 주요 데이터: 환자명, 주민번호, 차트번호, 진단/처방, 검사값, 유전체
- 권장 기법: 가명처리, 직접식별자 제거, 일반화, k-익명성, 적정성 평가
- 규제 위험도: High
- 운영 포인트: 재식별 키 분리, 의료법/보건의료 가이드라인 검토, 결합 심사

### 제조
- 주요 데이터: 배합비율, BOM, 공정 파라미터, 설비값, 도면
- 권장 기법: recipe token화, 범위화, 수치 정밀도 축소, 반출 통제
- 규제 위험도: Medium-High
- 운영 포인트: 개인정보와 영업비밀 분리 분류, 최소권한 열람

## 2. 자동화 로드맵

1. 업종 코드와 문서 유형을 ingestion 메타데이터로 강제한다.
2. 문서 파싱 후 민감 엔티티 검출기와 업종별 룰셋을 함께 적용한다.
3. 비식별 처리 결과와 재식별 위험 점수를 저장한다.
4. 재식별 키 또는 token vault 접근 이벤트를 별도 감사한다.
5. 주기적으로 재식별 가능성 샘플링 점검과 정책 예외 검토를 수행한다.
6. Langfuse trace와 OpenFGA 권한 판정 로그를 결합해 운영 대시보드에 표시한다.

## 3. 비식별 처리 정책 JSON 스키마 설계안

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.org/schemas/deid-policy.schema.json",
  "title": "DeidentificationPolicy",
  "type": "object",
  "required": [
    "policy_id",
    "version",
    "industry",
    "classification",
    "rules",
    "risk_model",
    "audit"
  ],
  "properties": {
    "policy_id": { "type": "string" },
    "version": { "type": "string" },
    "industry": {
      "type": "object",
      "required": ["ksic_section", "domain"],
      "properties": {
        "ksic_section": { "type": "string", "enum": ["C", "K", "Q"] },
        "domain": { "type": "string", "enum": ["manufacturing", "finance", "healthcare"] },
        "subdomain": { "type": ["string", "null"] }
      }
    },
    "classification": {
      "type": "object",
      "required": ["default_level", "trade_secret_enabled"],
      "properties": {
        "default_level": {
          "type": "string",
          "enum": ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"]
        },
        "trade_secret_enabled": { "type": "boolean" },
        "allowed_use": {
          "type": "array",
          "items": {
            "type": "string",
            "enum": ["SEARCH", "RAG", "FINE_TUNING", "ANALYTICS", "EXPORT"]
          }
        }
      }
    },
    "rules": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["field_type", "detection", "action"],
        "properties": {
          "field_type": { "type": "string" },
          "detection": {
            "type": "object",
            "properties": {
              "regex": { "type": ["string", "null"] },
              "ner_label": { "type": ["string", "null"] },
              "dictionary": { "type": ["string", "null"] }
            }
          },
          "action": {
            "type": "string",
            "enum": ["REMOVE", "MASK", "TOKENIZE", "GENERALIZE", "RANGE_BUCKET", "HASH"]
          },
          "replacement": { "type": ["string", "null"] },
          "applies_to": {
            "type": "array",
            "items": { "type": "string", "enum": ["TEXT", "TABLE", "OCR", "IMAGE_CAPTION", "METADATA"] }
          },
          "fine_tuning_allowed": { "type": "boolean" }
        }
      }
    },
    "risk_model": {
      "type": "object",
      "required": ["base_risk", "reidentification_review"],
      "properties": {
        "base_risk": { "type": "string", "enum": ["LOW", "MEDIUM", "MEDIUM_HIGH", "HIGH"] },
        "reidentification_review": {
          "type": "object",
          "properties": {
            "required": { "type": "boolean" },
            "frequency": { "type": "string", "enum": ["PER_UPLOAD", "DAILY", "WEEKLY", "MONTHLY"] },
            "threshold_score": { "type": "number" }
          }
        }
      }
    },
    "audit": {
      "type": "object",
      "required": ["log_input_hash", "store_transform_map", "approval_required_for_export"],
      "properties": {
        "log_input_hash": { "type": "boolean" },
        "store_transform_map": { "type": "boolean" },
        "approval_required_for_export": { "type": "boolean" },
        "langfuse_trace_tags": {
          "type": "array",
          "items": { "type": "string" }
        }
      }
    }
  }
}
```

## 4. Langfuse 감사 이벤트 로그 구조

Langfuse는 trace, span/observation, input/output, latency, token, cost, user/session 메타데이터를 구조적으로 기록하는 데 적합하다.

### 4.1 Trace 단위 예시

```json
{
  "trace_id": "trc_20260609_001",
  "session_id": "sess_abc123",
  "user_id": "u_1001",
  "pipeline": "document-rag",
  "industry": "healthcare",
  "ksic_section": "Q",
  "document_id": "doc_8921",
  "document_type": "clinical_note",
  "sensitivity_level": "RESTRICTED",
  "policy_id": "deid-q-v1",
  "policy_version": "1.2.0",
  "event_time": "2026-06-09T15:40:00+09:00",
  "tags": [
    "ocr",
    "deid",
    "rag",
    "restricted",
    "phi"
  ]
}
```

### 4.2 Observation/Span 예시

```json
[
  {
    "name": "ocr.parse",
    "type": "tool",
    "input": { "file_type": "pdf", "pages": 12 },
    "output": { "text_length": 18420 },
    "metadata": { "engine": "ocrmypdf+tesseract" },
    "latency_ms": 3840
  },
  {
    "name": "deid.detect",
    "type": "chain",
    "input": { "text_hash": "sha256:abcd..." },
    "output": {
      "entities_detected": 14,
      "entity_types": ["NAME", "RRN", "CHART_ID", "LAB_RESULT"]
    },
    "metadata": {
      "ruleset": "healthcare-v3",
      "risk_score": 0.84
    },
    "latency_ms": 422
  },
  {
    "name": "deid.transform",
    "type": "chain",
    "input": { "policy_id": "deid-q-v1" },
    "output": {
      "transformed": 12,
      "transform_actions": ["TOKENIZE", "GENERALIZE"]
    },
    "metadata": {
      "transform_rate": 0.86,
      "token_vault_ref": true
    },
    "latency_ms": 119
  },
  {
    "name": "authz.openfga.check",
    "type": "tool",
    "input": {
      "user": "u_1001",
      "relation": "can_query",
      "object": "doc:doc_8921"
    },
    "output": { "allowed": true },
    "metadata": {
      "model_id": "rag-authz-v2"
    },
    "latency_ms": 18
  },
  {
    "name": "rag.answer",
    "type": "generation",
    "input": {
      "query": "최근 검사 결과 요약",
      "retrieved_chunks": 4
    },
    "output": {
      "answer_hash": "sha256:efgh...",
      "citations": 3
    },
    "metadata": {
      "model": "local-llm-medical",
      "tokens_in": 1432,
      "tokens_out": 286,
      "cost": 0,
      "blocked_sensitive_fields": 2
    },
    "latency_ms": 2410
  }
]
```

### 4.3 운영 지표
- documents_processed_total
- entities_detected_total
- transform_rate_avg
- reidentification_risk_score_avg
- openfga_denied_total
- export_approval_pending_total
- llm_sensitive_block_total

## 5. 업종별 시뮬레이터에 넣을 추천 로직

### 금융
- 계좌번호·카드번호·거래금액 검출
- 금액은 범주화, 식별자는 부분 마스킹 또는 토큰화
- 외부 모델 전송 시 자동 차단 플래그

### 의료
- 이름·주민번호·차트번호·검사일·검사값 검출
- 직접식별자 제거 후 검사일 일반화
- 고위험 점수 시 RAG는 허용, fine-tuning은 금지

### 제조
- 배합비율·설비 온도·압력·BOM 코드 검출
- 절대값을 범위값 또는 secret token으로 치환
- trade_secret 플래그가 있으면 export 금지
