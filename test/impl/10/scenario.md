# test/impl/10 — pgvector 어댑터 + PDF/DOCX 파서 + Langfuse sink 시나리오

대상: rag `app/index/pgvector_store.py`, deid `app/parsers.py`·`app/langfuse_sink.py` + `/process-document`.
러너: deid `uv run pytest tests/test_parsers.py` + rag `uv run pytest`(postgres `make up` 필요).

## 시나리오

| # | Given | When | Then |
|---|---|---|---|
| S1 | DOCX(RRN) 바이트 | parse_docx | 텍스트 추출, RRN 포함 |
| S2 | text/plain | parse_document 디스패치 | 평문 디코드 |
| S3 | DOCX base64 | `/process-document` | 파싱→비식별, RRN 제거 |
| S4 | 빈 PDF | parse_document(pdf) | 무오류 str 반환 |
| S5 | LANGFUSE_HOST 미설정 | emit(trace) | no-op(False), 예외 없음 |
| S6 | 해시 임베딩 | hash_embedding | 결정적, dim=64, L2 정규화 |
| S7 | pgvector PUBLIC+RESTRICTED (DB 가용) | query external=true | RESTRICTED 차단(blocked≥1), PUBLIC만 |

## 도메인 compliance 매핑
- 의료(Q): DOCX 진료기록 파싱→비식별(RRN 제거)
- pgvector 백엔드도 외부반출 게이트·테넌트 격리 유지(WHERE project_id + sensitivity 필터)
- DB 미가용 시 S7 skip(통합테스트), in-memory 폴백
