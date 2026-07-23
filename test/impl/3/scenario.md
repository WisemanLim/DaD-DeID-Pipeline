# test/impl/3 — deid→rag 결선 파이프라인 (PRD §1 핵심 플로우) 시나리오

대상: deid `/process`(청킹 + 청크별 비식별 → ChunkMetadata) → rag `/index` → rag `/search` 게이트.
러너: `cd services/deid && uv run pytest` (단위) + 크로스서비스 E2E(curl/python).

## 시나리오

| # | Given | When | Then (수용 기준) |
|---|---|---|---|
| S1 | "문단1\n\n문단2" | chunk_text | 2 청크 분리, 공백 입력=빈 리스트 |
| S2 | 공개문단 + RRN 진료문단 | `/process` | 2청크, 문서민감도=RESTRICTED(최대), 공개=PUBLIC/NONE |
| S3 | RRN 청크 | `/process` | RRN 제거, transform_action 에 REMOVE, lineage.rule_ids 존재, chunk_id=`docA#1` |
| S4 | `/process` 산출 metadata | 키 검사 | rag ChunkMetadata 필수필드 ⊇ (계약 호환) |
| **E2E** | 공개+RRN+카드 문서 | process→index×N→search | namespace 분리, external 검색 RESTRICTED 차단(blocked=1), internal 전건 |

## 도메인 compliance 매핑 (COMPLIANCE.md)
- 의료(Q): S2/S3/E2E — 비식별 후 인덱싱, 직접식별자 미잔존
- 금융(K): E2E — 카드 청크 RESTRICTED → 외부반출 차단
- ict-saas(J): project_id 전파 → 테넌트 격리 유지
