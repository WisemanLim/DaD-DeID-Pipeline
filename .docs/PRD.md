# One-Page PRD: De-Identification-PI-DSI (개인정보·도메인 민감정보 비식별화)

> 산업분류(KSIC) 거버넌스 기반 문서 비식별 파이프라인 — 개인정보(PII/PHI/PCI)뿐 아니라 업종별 도메인 민감정보(영업비밀·공정 recipe·BOM·업종 맥락)까지 비식별한다.

## 1. 개요
- **한 줄 요약:** 문서 업로드 후 OCR·파싱·청킹·임베딩 파이프라인의 각 단계에 "업종(KSIC) 거버넌스 훅"을 붙여, 개인정보와 **도메인 스페시픽 민감정보**(예: 스프 배합비율 17.3% → `RANGE_15_20` / `recipe-token`)를 정책 기반으로 검출·변환(마스킹·토큰화·범주화)하는 비식별 엔진 + 거버넌스 대시보드.
- **배경 / 왜 지금 하는가:** 기본 문서 파이프라인(청킹/파싱/OCR)은 이미 있으나 global/privacy 기준만 보호한다. RAG·파인튜닝 도입이 늘며 업종별 거버넌스 민감정보가 인덱싱/외부 LLM 으로 유출될 통제 공백이 실위험화. (근거: `.docs/Perplexity-문서 업로드 비식별화.md`)
- **작성자 / 날짜 / 버전:** Wiseman.Lim / 2026-06-09 / v0.1 (draft)

## 2. 문제와 대상 (Why & Who)
- **해결하려는 핵심 문제:** 문서 파이프라인이 개인정보 외 업종별 민감정보(금융 계좌·거래, 의료 PHI, 제조 영업비밀형 수치/recipe)와 **업종 자체 같은 민감 맥락**을 식별·통제하지 못한다. 비식별 없이 청킹/임베딩/파인튜닝/외부 LLM 으로 흘러가 거버넌스·규제 위반 위험.
- **비즈니스 관점 중요성:** 금융·의료·제조 고객 대상 RAG/WFP 파이프라인 판매·운영의 전제 조건. 규제 정합성(국내 데이터3법·보건의료 가이드라인 + 글로벌 GDPR/HIPAA/PCI) 미충족 시 도입 차단.
- **근거 데이터 / VOC / 로그:** `가정:` 정량 VOC 미확보. 근거 = 첨부 리서치 문서(§1~5)와 업종 거버넌스 레퍼런스(OECD Health Data Governance, FINOS AI Governance, OWASP LLM-SVS, 국내 비식별 가이드라인).
- **타깃 사용자 / 페르소나:**
  - **현업 업로더** — 금융/의료/제조 문서를 올리는 실무자. 업종·문서유형만 고르면 비식별이 자동 적용되길 원함.
  - **거버넌스/보안 담당자** — 변환율·차단율·정책 예외·재식별 키 접근을 모니터링.
  - **WFP 파이프라인 운영자** — 업종 프리셋(모델·튜닝·거버넌스)을 일관 적용.
- **대표 사용 상황:** 업종(KSIC) 선택 → 문서 업로드 → 비식별 자동 적용 → 민감도별 분리 인덱싱 → 검색/RAG + 대시보드 관측.

## 3. 범위 (What — In / Out)
- **이번 릴리즈 핵심 기능 (P0/P1):**
  - **(P0) ⓐ 업종(KSIC) 거버넌스 프로파일** — `industry_governance_profile` (섹션별 데이터분류·허용처리·필수통제·규제 ref). 베이스라인 = ict-saas(J), 오버레이 = 제조(C)→의료(Q)→금융(K).
  - **(P0) ⓑ 민감정보 검출** — 파이프라인 단계별(파싱/OCR/청킹) 개인정보(PII/PHI/PCI) **+ 도메인 영업비밀형**(배합비율·BOM·공정파라미터) 엔티티 검출(regex + NER + 도메인 사전).
  - **(P0) ⓒ 정책 엔진 변환** — 항목별 조치 결정: 삭제·부분마스킹·토큰화·해시·**범주화(range bucket)**·**recipe token 치환**·보존.
  - **(P1) ⓓ 청크 민감도 메타데이터 + 분리 인덱싱** — chunk 단위 `sensitivity_level`·`transform_action`·`industry_code`·`lineage` 부여, 민감도별 별도 index/namespace.
  - **(P1) ⓔ 거버넌스 대시보드** — 변환율·차단율·정책 예외·고위험 청크 비중·재식별 키 접근 KPI 시각화.
- **하지 않을 것 (Out of Scope):**
  - RAG 답변 품질/검색 정확도 튜닝, 모델 파인튜닝 자체.
  - 법률 자문(시뮬레이터는 정책 검토용 프론트, 자문 아님).
  - OpenFGA 전체 권한모델·런타임 권한 판정 구현 — 후속(메타데이터 훅만 남김).
  - 기존 OCR/파서 엔진 자체 개발(Tika/Unstructured/Tesseract 등 활용).

## 4. 사용자 경험 (How — User Flow)
- **대표 시나리오 1 (제조 — 도메인 민감정보):** 제조 현업이 KSIC `C` + "공정명세서" 선택 → 업로드 → OCR/파싱이 "배합비율 17.3%, 압력 4.2bar" 추출 → 도메인 검출기가 영업비밀형 수치로 식별 → 정책 엔진이 `RANGE_15_20`·임계구간으로 범주화, 상세값은 vault 보관 → 청크에 `sensitivity_level=TRADE_SECRET` 부여 → 분리 인덱싱 → 대시보드에 `recipe_transform_rate` 표시.
- **대표 시나리오 2 (의료 — 개인정보/PHI):** 의료 현업이 KSIC `Q` + "진료기록" 선택 → 기본 분류 `Restricted` 자동 제안(override 시 audit 로그) → 환자식별자·검사일·검사값 검출 → 가명처리+일반화, 재식별 키는 별도 금고 분리 → de-identified 청크만 인덱싱 → 비식별 검증(산출물에 직접식별자 없음) 통과 시 통과.

## 5. 성공 지표 (Success)

| KPI | 기준선(Baseline) | 목표값(Target) | 측정 방법 |
|---|---|---|---|
| 업종별 민감 엔티티 검출률(재현율) | `가정:` 미측정 | `가정:` ≥ 95% (직접식별자) | 라벨 평가셋 vs 검출 결과 |
| 문서유형별 변환(마스킹/치환) 적용률 | `가정:` | `가정:` 100%(검출분) | 파이프라인 로그 집계 |
| 외부 LLM 호출 차단 건수(RESTRICTED/TRADE_SECRET) | 0 | `가정:` 유출 0건 | 정책판단 이벤트 |
| `recipe_transform_rate`(제조 영업비밀) | `가정:` | `가정:` 100% | 도메인 검출/변환 로그 |
| 재식별 키 접근 이벤트 수 | — | 전건 audit 기록 | 키 금고 접근 로그 |

> **검증 가능한 수용 기준 후보 (업종 오버레이 근거, `testing_additions`):**
> - 의료(Q): *Given* 진료기록 업로드, *When* 비식별 완료, *Then* 산출물에 직접식별자 없음(재식별 불가). (healthcare.yaml)
> - 제조(C): *Given* 공정 수치 포함 문서, *When* 비식별, *Then* 절대값 미보존·범주/토큰만 잔존. (manufacturing.yaml)
> - 금융(K): *Given* 카드/계좌 데이터, *When* 비식별, *Then* PAN 부분마스킹+토큰화, 외부 반출 차단. (finance.yaml)
> - 공통(J): *Given* 멀티테넌트, *When* 인덱싱, *Then* 크로스테넌트 누출 0(RLS). (ict-saas.yaml)

## 6. 리스크 및 메모
- **주요 리스크:**
  - 도메인 영업비밀형 정보는 표준 DLP 사전이 없음 → 업종별 식별 사전 큐레이션 필요(검출률 변동). 본 PRD 가정: **시드 데이터(업종별 가드레일용)를 추가 제공받아 1차 후 보강**.
  - 재식별 위험 — 단일 기법(마스킹) 불충분, 결합 재식별 모니터링 필요(국내 비식별 가이드라인).
  - 비식별 과다 → 검색성/분석성 저하 트레이드오프(범주화 입도 조정 필요).
- **의존성 (내부/외부):**
  - 내부: 기존 문서 파이프라인(청킹/파싱/OCR), WFP + KSIC/ISIC/NACE/NAICS 매핑(`industry_classification`/`industry_code_mapping`), `ksic.ts`, `model_catalog`.
  - 외부(오픈소스 후보): 파싱(Apache Tika/Unstructured/Tesseract/OCRmyPDF/GROBID), 검출/비식별(Microsoft Presidio + spaCy NER + 도메인 사전), 정책엔진(OPA/Cedar), 관측성(Langfuse/OTel), (후속)권한(OpenFGA).
- **미결정 사항 (Open Questions):**
  - 성공지표 기준선·목표값 수치 미확정(`가정:` 상태).
  - 시드 데이터 제공 시점·포맷·업종 커버리지 범위.
  - vault(재식별 키/recipe 매핑) 저장소 선택 및 키 관리(KMS/HSM) 범위.
  - 1차 완료 후 수정 예정(반복 개선) — 베이스라인→C→Q→K 순.

---

## 7. 기술 메모 (Technical Notes) — 예시/초안

- **주요 기술 결정 (아키텍처·핵심 컴포넌트·인터페이스):** `가정:`
  - **정책 원천 → 파이프라인 적용 → 대시보드 관측** 3계층. 업종 가이드라인을 정책 소스로, OCR/파싱/청킹/임베딩 각 단계에 거버넌스 훅.
  - 핵심 컴포넌트: ① 업종 거버넌스 프로파일 스토어, ② 민감 엔티티 검출기(regex/NER/도메인 사전), ③ 정책 엔진(조치 결정), ④ 변환기(마스킹/토큰화/범주화/recipe token), ⑤ 청크 메타데이터/lineage, ⑥ 분리 인덱싱(민감도별 namespace), ⑦ 거버넌스 대시보드.
  - **핵심 원칙:** "민감 원문 저장소"와 "변환 후 검색용 저장소"를 분리. 외부 모델 호출 전 정책판단 지점에서 `RESTRICTED`/`TRADE_SECRET` 청크 프롬프트 유출 차단.
  - 데이터 모델(초안, 첨부 문서 §1):
    ```sql
    industry_governance_profile (
      id uuid pk,
      ksic_section char(1),               -- A~U (베이스 J, 오버레이 C/Q/K)
      risk_level enum('low','medium','high','very_high'),
      data_classification_schema_id uuid,  -- 4/5단계 분류
      allowed_processing jsonb,            -- train_in_cloud, RAG_only, no_pii_training...
      required_controls jsonb,             -- encryption, dlp, k_anonymity, dp, range_bucket...
      regulatory_refs jsonb                -- [{name, url, citation_id}, ...]
    )
    ```
  - 비식별 정책 JSON 스키마 블록(첨부 §5): `industry`(ksic/domain), `classification`(민감도·허용범위·`trade_secret_enabled`), `rules`(detection: regex/NER/dictionary, action: MASK/TOKENIZE/GENERALIZE), `risk_model`(재식별 검토 주기·threshold), `audit`(입력해시·매핑저장·export승인·Langfuse 태그).
- **비기능 요구사항 (성능·보안·규제·SLO·Observability):** (업종 오버레이 반영, 출처 = domains/*.yaml)
  - **베이스라인(ict-saas/J):** 멀티테넌트 격리(RLS/스키마/DB-per-tenant), 크로스테넌트 누출 차단, OpenTelemetry 관측성, OpenAPI 계약. 규제: 정보통신망법·PIPA·ISMS-P·CSAP. 글로벌: SOC2 Type II·ISO 27001·GDPR.
  - **제조(C):** 영업비밀형 수치 범주화·recipe token, OT/IT 분리(IEC 62443), OT 데이터 온프렘·엣지 우선. 글로벌: ISA-95/IEC 62264, IEC 62443.
  - **의료(Q):** 필드레벨 암호화, 가명키 금고 격리, 불변 감사추적(ATNA), 비프로드 실 PHI 금지(합성/비식별만). 규제: PIPA §23 민감정보·가명정보 특례, 보건의료데이터 활용 가이드라인(2024-12), 의료법. 글로벌: HIPAA, GDPR Art.9.
  - **금융(K):** 토큰화로 PCI scope 축소, 개인신용정보 비프로드 반출 금지, append-only 감사로그, HSM/KMS 키 격리. 규제: 전자금융거래법·신용정보법·전자금융감독규정(2025-02-05, 가명정보 R&D 허용). 글로벌: PCI-DSS 4.0.1.
- **데이터 / 로깅 요구사항 (지표 측정 관점):** 청크별 `industry_code`·`sensitivity_level`·`transform_action`·`lineage` 메타데이터. Langfuse trace 상단=문서/업종/정책 메타, 하위 span=`deid.detect`·`deid.transform`·`authz.openfga.check`·`rag.answer`. 재식별 키 접근·정책 예외·외부호출 차단 전건 audit.
- **외부 연동 / API 스펙 요약:** `가정:` FastAPI 기준 정책 평가기 + Presidio/(후속)OpenFGA/Langfuse 연동. ingestion 필수 메타: `industry_code`·`document_type`·`region`·`source_system`.
- **리스크 및 트레이드오프:** 검출률 vs 오탐, 비식별 강도 vs 검색·분석성, 온프렘(OT/PHI) vs 클라우드 비용. 데이터등급 상향 시 인프라 분리 비용 증가.

## 8. 실행 연결 (Epic / Story 힌트)
- **Epic 0 — 베이스라인(J):** 거버넌스 프로파일 스토어 + 정책 JSON 스키마 + 멀티테넌트/관측성 골격.
- **Epic 1 — 검출 계층:** 개인정보(PII/PHI/PCI) 검출기(Presidio+NER) + regex 룰셋.
- **Epic 2 — 도메인 민감정보 계층(C 우선):** 영업비밀형 사전·범주화/recipe token 변환 + 시드 데이터 연동.
- **Epic 3 — 파이프라인 훅:** OCR/파싱/청킹/임베딩 단계별 정책 훅 + 청크 메타데이터/분리 인덱싱.
- **Epic 4 — 정책 엔진:** OPA/Cedar 기반 조치 결정 + 외부 LLM 호출 차단 지점.
- **Epic 5 — 거버넌스 대시보드:** Langfuse/OTel 연동 KPI(변환율·차단율·재식별 키 접근).
- **Epic 6 — 오버레이 확장:** 의료(Q) → 금융(K) 프로파일·검증 기준 순차 적용.

---

### 자가 점검 (Definition of Ready)
- [x] 문제 정의가 실제 사용자 문제를 설명 (개인정보+도메인 민감정보 유출 공백)
- [x] In/Out Scope 둘 다 명확
- [△] 성공 지표 측정 가능하나 **기준선·목표값 `가정:`** (시드 데이터/1차 후 확정)
- [x] 수용 기준 Given-When-Then 형태(업종별)
- [x] 의존성·리스크 명시(시드 데이터 의존, 재식별 위험, 트레이드오프)
- [x] 규제·데이터등급을 NFR/리스크에 반영(국내+글로벌 매핑, domains/*.yaml 근거)

> 근거: `.docs/Perplexity-문서 업로드 비식별화.md` (§1~5), `domains/{ict-saas,manufacturing,healthcare,finance}.yaml`
