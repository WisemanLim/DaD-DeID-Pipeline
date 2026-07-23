# test/impl/12 — classifier 룰 ML 판정 시나리오

대상: deid `app/detect/{embedder,classifier_judge}.py` + `/guard?ml=true`.
러너: `cd services/deid && uv run pytest tests/test_classifier_judge.py`.

## 시나리오

| # | Given | When | Then |
|---|---|---|---|
| S1 | AML 우회 classifier 룰(examplesPositive) | judge("KYC 우회…") | margin≥0.01 → AML_BYPASS 매칭 |
| S2 | 무관 입력("점심 메뉴") | judge | benign margin 미달 → 매칭 없음 |
| S3 | classifier 룰 없음(regex만) | judge | 빈 결과 |
| S4 | `/guard ml=true` 위반 텍스트 | POST | allowed=False |

## 설계 메모
- 다국어 임베딩 모델은 한국어 절대 코사인 baseline 높음(무관 0.88) → **margin(rule_sim − benign_sim)** 방식
- 분리 측정: 위반 +0.02~0.06, benign 음수 → threshold 0.01
- 모델 미가용 시 해시 폴백(정확도 저하, threshold 재보정 필요)

## 도메인 compliance 매핑
- 금융(K): AML/KYC 우회 의도 — regex/NER 미포착분을 임베딩 판정으로 보강 → 가드레일 차단
