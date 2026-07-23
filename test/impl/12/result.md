# test/impl/12 — 결과 / result

- 실행일: 2026-06-10
- 판정: **PASS** (deid 44/44 · ruff clean)

```
classifier_judge: 4 passed
deid 전체: 44 passed   (기존 40 + classifier 4)
```

| # | 케이스 | 결과 |
|---|---|---|
| S1 | test_judge_matches_paraphrase | PASS (margin 양수) |
| S2 | test_judge_ignores_unrelated | PASS |
| S3 | test_judge_empty_when_no_classifier_rules | PASS |
| S4 | test_guard_ml_endpoint_blocks | PASS |

## 구현
- `app/detect/embedder.py` — deid 측 임베딩(STEmbedder + 해시 폴백), `cosine()`
- `app/detect/classifier_judge.py` — classifier 룰 examplesPositive 앵커 임베딩, **margin(rule_sim−benign_sim)** 판정
- `/guard?ml=true` — 가드레일에 classifier ML 레이어 결선(industry_code별 judge 캐시)
- Rule 모델에 `examplesPositive` 필드 추가

## 수정 이력
- **FAIL→PASS**: 절대 코사인 임계(0.5)에서 무관 입력 오탐(모델 한국어 baseline 0.88).
  margin 방식(benign 앵커 대비)으로 전환 → 위반 +0.02~0.06 vs benign 음수 분리, threshold 0.01 통과.

## 한계 / 잔여
- margin threshold(0.01)는 benign 앵커 6종 기준 경험값 — 도메인별 캘리브레이션 권고.
- 룰당 앵커 3개 제한(비용). 대량 classifier 룰(도메인 200+) 첫 호출 임베딩 비용 → judge 캐시로 완화.
- 더 정밀한 판정은 LLM judge(Claude) 후속 — 현재 임베딩 margin.
