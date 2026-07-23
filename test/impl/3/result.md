# test/impl/3 — 결과 / result

- 실행일: 2026-06-09
- 러너: `cd services/deid && uv run pytest -q` (단위) + 크로스서비스 E2E
- 판정: **PASS** (deid 11/11 · ruff clean · E2E 통과)

```
11 passed, 1 warning in 0.19s    (기존 8 + pipeline 3)
```

| # | 케이스 | 결과 |
|---|---|---|
| S1 | test_chunker_splits_paragraphs | PASS |
| S2 | test_process_emits_chunk_metadata (문서민감도 최대) | PASS |
| S3 | RRN 제거 + lineage + chunk_id | PASS |
| S4 | test_process_metadata_matches_rag_contract | PASS (계약 호환) |

## E2E (실 2서비스 결선, deid:8001 + rag:8002)
```
문서 = "회사 공개 소개 자료...\n\n환자 900101-1234567, 카드 4242 4242 4242 4242 결제..."
1) POST deid/process → doc_sensitivity=RESTRICTED, chunks=2
2) 각 청크 POST rag/index:
   docA#0 ns=PUBLIC      blocked=False
   docA#1 ns=RESTRICTED  blocked=True
3) POST rag/search {external:true} → hits=[], export_blocked_count=1   (RESTRICTED 차단)
4) POST rag/search {external:false} → hits=2                            (내부 전건)
```

## 수정 이력
- 없음 (최초 통과).

## 한계 / 잔여
- 청커 = 문단(빈 줄) 기준. 토큰 길이/구조 기반 청킹은 후속.
- 결선은 현재 명시 호출(클라이언트가 process→index 순차). 단일 오케스트레이션 엔드포인트/큐는 후속.
- 다음: NER 검출기(Epic 1+, spaCy 모델 = 네트워크 승인 필요), OCR 경로(Epic 3), Langfuse trace(Epic 6).
