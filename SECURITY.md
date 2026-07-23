# SECURITY — DaD DeID Pipeline

> 자동 생성. 근거: `profiles/bio-rag-research.yaml` `security_standards` + `index_metadata_min_fields`.
> 규제·데이터등급 상세는 `COMPLIANCE.md` 참조(보완 문서).

## 보안 표준 / Security standards

| 항목 | 표준 |
|---|---|
| 데이터 분류 | 공개/내부/민감/규제대상(PHI·유전·개인신용정보·영업비밀) 4단계. **업로드 기본값 = 민감** |
| 접근 제어 | OIDC SSO + RBAC/ABAC. 질의 시점 ACL 필터 후 검색 |
| 비식별 | 전처리 파이프라인에 마스킹 단계 기본 포함 (deid 서비스) |
| 감사 | 인덱싱/조회/다운로드 감사로그 → Audit DB + SIEM |
| 출처 | 모든 응답에 출처·버전·인덱싱시점·검증상태 병기 |
| 재현성 | chunker / embedding 모델 / prompt 버전 고정·기록 |
| 고위험 | 고위험 질의 → human-in-the-loop 승인 큐 |

## 외부 반출 게이트 / export gate

- `sensitivity_level ∈ {RESTRICTED, TRADE_SECRET}` 청크는 **외부 LLM 반출 차단**
  (`services/rag/app/index/schema.py::ChunkMetadata.export_blocked`).
- 재식별 키 / recipe token 은 vault 격리. 접근은 전건 audit + 승인.

## 인덱스 메타데이터 최소 필드 / index metadata min fields

`document_id · source_uri · domain · project_id · sensitivity · owner · version · chunk_id · section_path · approval_state · retention_policy · indexed_at`
(+ PRD: `industry_code · transform_action · lineage`) — 구현: `services/rag/app/index/schema.py`.
