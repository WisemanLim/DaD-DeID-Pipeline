# test/impl/7 — 결과 / result

- 실행일: 2026-06-09
- 판정: **PASS** (deid 29/29 · ruff clean · domains 7/7)

```
29 passed   (기존 22 + domains 7)
```

| # | 케이스 | 결과 |
|---|---|---|
| S1 | test_domains_by_section_registry | PASS |
| S2 | test_privacy_seed_loaded_card_luhn | PASS |
| S3 | test_section_load_merges_subdomains | PASS |
| S4 | test_healthcare_rrn_removed | PASS (의료) |
| S5 | test_manufacturing_trade_secret | PASS (제조) |
| S6 | test_public_arts_baseline_pii | PASS (공공/예술) |
| S7 | test_domains_endpoint | PASS |

## 구현
- `RuleBundleLoader.baseline()` — 실 `privacy` seed(245룰·46 regex: card_number+Luhn, iban, passport, ssn 등) 적재, 없으면 내장 fallback
- `RuleBundleLoader.domains_by_section()` — seed 스캔 → KSIC 섹션별 서브도메인 (C 15·K 3·Q 3·O 1·R 1)
- `load(industry_code)` — KSIC 1글자(C) → 섹션 전 서브도메인 병합, 서브도메인명 → 단일 번들
- deid `GET /domains` — 섹션 레지스트리 + KSIC 라벨

## 발견
- 도메인 seed 번들(C 2810·K 600·Q 620·O 200·R 200)은 **거의 전부 classifier patternType** → regex 검출 0.
  → 도메인 특화 검출은 NER(인명/지명) + dictionary(영업비밀) + 후속 전용 분류기. PII deid 는 baseline(global+privacy) 담당.

## 수정 이력
- 없음.

## 한계 / 잔여
- classifier 룰(런타임 가드레일 I/O block/refuse 다수)은 Epic 7(후속) 범위 — 비식별 안정화 후.
