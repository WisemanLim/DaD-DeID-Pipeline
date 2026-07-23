# PRD v2 (Full-Spec): DaD DeID Pipeline — Domain-Aware Document De-Identification Pipeline

> **DaD DeID Pipeline** = 일반 문서(PDF·DOCX·PPTX·**손글씨 메모 이미지** 포함)를 청킹/파싱·OCR·임베딩하는 과정에서, **개인정보(PII)뿐 아니라 업종(도메인) 특화 비공개 정보**(영업비밀·배합비율·BOM·공정 파라미터 등)까지 정책 기반으로 비식별하는 파이프라인.
> v1(`.docs/PRD.md`) 대비 2차 업데이트: 실제 시드 데이터(24개 KSIC 도메인 룰번들, KR/EN, 총 ~9.7K rules)·정책 JSON 스키마·Langfuse 감사구조 반영. v1 은 보존, 본 문서는 `.docs/PRD.v2.md` 로 재생성.

## 0. 영문 프로젝트명 제안

- **확정(사용자 선호):** **DaD DeID Pipeline** — _Domain-Aware Document De-Identification Pipeline_ 의 약칭. 업종(도메인) 인지 + 문서 비식별 + 파이프라인 성격을 그대로 표현.
- **포지셔닝 보정:** 시드에 담긴 "guardrails(block/refuse/disclaimer)"는 정책 **원천**이고, 본 프로젝트의 **핵심은 문서 비식별** — 개인정보 + **업종 특화 비공개 정보**. 따라서 정식명 = _Domain-Aware Document De-Identification Pipeline_.
- 후보(참고): `RedactFlow`(초기안), `DocuGuard`(시드 정책 패밀리 `DocuGuard-AI-Policy` 계승), `Aegis-DocShield`, `ScrubPipe`. → 도메인 인지·비식별 핵심 강조로 **DaD DeID Pipeline** 채택.

## 1. 개요

- **한 줄 요약:** 문서 업로드 → 파싱/OCR(손글씨 이미지 포함) → 민감정보 검출(개인정보 + 업종 비공개) → 정책 엔진 변환(마스킹·토큰화·범주화·recipe token) → 청크 메타데이터 + 민감도별 분리 인덱싱 → 거버넌스 관측.
- **배경 / 왜 지금:** 기본 파이프라인(청킹/파싱/OCR)은 global/privacy 만 보호. RAG/파인튜닝 확산으로 업종 비공개 정보가 인덱싱·외부 LLM 으로 유출될 통제 공백. 이미 `DocuGuard-AI-Policy` 형태의 정책 자산(24 도메인 룰번들)이 존재 → 이를 문서 비식별 파이프라인의 정책 소스로 통합할 시점.
- **작성자 / 날짜 / 버전:** Wiseman.Lim / 2026-06-09 / **v2.0 (draft)**

## 2. 문제와 대상 (Why & Who)

- **핵심 문제:** 문서 파이프라인이 ① 개인정보(주민번호·연락처·카드·계좌·PHI), ② **업종 특화 비공개 정보**(제조 배합비율/BOM/공정값, 화학 합성루트/촉매비율, 금융 거래연계, 의료 차트·검사값), ③ 안전·규제 위반 콘텐츠를 식별·변환하지 못한 채 인덱싱/외부 반출 → 거버넌스·규제 위반.
- **비즈니스 중요성:** 금융·의료·제조·공공 등 규제 고객 대상 RAG/WFP 운영 전제. 국내(데이터3법·산업안전보건·업종법) + 글로벌(GDPR·HIPAA·PCI·REACH·CE) 정합성 미충족 시 도입 차단.
- **근거 데이터:** **실측 시드** — 24개 KSIC 도메인 룰번들(KR/EN 쌍), 총 ~9,700 rules. 분포 예: `manufacturing-electronics` ip(영업비밀) 65건, `healthcare-clinical` 220 rules(safety 30·pii 71·compliance 78), `finance-banking` 200(pii 50·fraud 45·compliance 70). 출처: `.docs/seed/*.json`, `.docs/deid-policy-and-langfuse-pack.md`, `.docs/Perplexity-문서 업로드 비식별화.md`.
- **타깃 사용자:**
  - **현업 업로더** — 업종·문서유형만 선택, 비식별 자동 적용.
  - **거버넌스/보안 담당자** — 변환율·차단율·재식별 위험점수·예외승인 모니터링.
  - **WFP 파이프라인 운영자** — 업종 프리셋(검출 룰셋·정책·모델) 일관 적용.
- **대표 사용 상황:** 업종(KSIC) 선택 → 업로드(손글씨 이미지 포함) → 비식별 → 민감도별 분리 인덱싱 → 검색/RAG + 대시보드.

## 3. 범위 (What — In / Out)

- **이번 릴리즈 핵심 기능 (P0/P1):**
  - **(P0) ⓐ 도메인 룰번들 로더** — `.docs/seed/*.json` 스키마(`ruleId/category/subCategory/ioType/patternType/patterns(regex,luhnCheck)/action/severity/priority/regulationTags/examples`)를 적재. 베이스라인 = `global`+`privacy`(범용 PII/credentials), 오버레이 = 업종별(C/K/Q/O/R).
  - **(P0) ⓑ 민감정보 검출** — 파싱/OCR/청킹 단계에서 다범주 검출: `pii·credentials·financial·sensitive(health·biometrics·children·location)·ip(trade_secret)·safety·compliance·fraud`. patternType: `regex`, `regex+classifier`(Luhn), NER, dictionary.
  - **(P0) ⓒ 정책 엔진 변환** — 항목별 조치. 비식별 액션: `REMOVE·MASK·TOKENIZE·GENERALIZE·RANGE_BUCKET·HASH`. 가드레일 액션(시드): `block·redact·block_or_redact·block_or_pseudonymize·warn·refuse·add_disclaimer·sanitize·aggregate_only`. `applies_to: [TEXT, TABLE, OCR, IMAGE_CAPTION, METADATA]`.
  - **(P0) ⓓ OCR/이미지 경로** — 손글씨 메모 등 이미지 문서 OCR 후 동일 비식별 적용(`applies_to=OCR/IMAGE_CAPTION`).
  - **(P1) ⓔ 청크 메타데이터 + 분리 인덱싱** — `industry_code·sensitivity_level·transform_action·lineage` 부여, 민감도별 namespace 분리. RESTRICTED/TRADE_SECRET 청크 외부 LLM 반출 차단.
  - **(P1) ⓕ 거버넌스 대시보드** — Langfuse/OTel 기반 운영지표(아래 §5).
  - **(P1) ⓖ 포털 E2E 파이프라인 UI** — 웹(portal:3000)에서 §1 한 줄 요약 흐름을 직접 실행: 업종(KSIC) 선택 → 문서 입력(텍스트/PDF·DOCX·TXT 파일/손글씨 이미지) → 검출·정책 변환 결과(청크별 민감도·transform_action·검출 룰) 확인 → 민감도별 분리 인덱싱 → 검색(외부반출 게이트 토글). 기존 대시보드(ⓕ)와 동일 앱. deid/rag REST 를 Next.js 서버 라우트로 프록시(브라우저 CORS 회피).
- **하지 않을 것 (Out of Scope):**
  - RAG 답변 품질/검색 정확도 튜닝, 모델 파인튜닝 자체.
  - 법률 자문(`.docs/*.html` 시뮬레이터는 정책 검토용 프론트).
  - OpenFGA 런타임 권한모델 **구현**(메타데이터/감사 훅만; 후속).
  - OCR/파서 엔진 자체 개발(Tika/Unstructured/Tesseract/OCRmyPDF/GROBID 활용).
  - 신규 룰 창작 — 시드 룰번들 기준, 신규는 별도 큐레이션 트랙.

## 4. 사용자 경험 (How — User Flow)

- **시나리오 1 (제조 C — 영업비밀):** KSIC `C/manufacturing-chemical` + "합성명세서" → 업로드 → OCR/파싱이 "촉매비율 17.3%, 반응압력 4.2bar" 추출 → 룰 `ip/catalyst_ratio_secret [block_or_redact]`·`ip/synthesis_route_secret` 매칭 → `RANGE_BUCKET`/`recipe-token` 치환, 상세값 vault 보관 → `sensitivity_level=RESTRICTED`, `trade_secret_enabled=true` → 분리 인덱싱 → 대시보드 `transform_rate_avg` 표시. (regulationTags: `TRADE_SECRET`, `KR_OSH`, `EU_REACH`)
- **시나리오 2 (의료 Q — PHI):** KSIC `Q/healthcare-clinical` + "진료기록" → 기본 `RESTRICTED` 제안(override 시 audit) → `pii/national_id_kr`·`CHART_ID`·`LAB_RESULT` 검출(risk_score 0.84) → 직접식별자 `REMOVE`·검사일 `GENERALIZE`·재식별 키 vault 분리 → de-identified 청크만 인덱싱 → 비식별 검증(직접식별자 0) 통과. (US_HIPAA, KR_MED_ACT, PIPA §23)
- **시나리오 3 (손글씨 메모 이미지):** 이미지 업로드 → OCR → 텍스트화 결과에 `applies_to=OCR` 룰 적용 → 검출/변환 → 캡션/메타데이터까지 비식별.

## 5. 성공 지표 (Success)

| KPI (운영지표는 md pack §4.3 근거)                                 | 기준선         | 목표값                   | 측정                |
| ------------------------------------------------------------------ | -------------- | ------------------------ | ------------------- |
| `entities_detected_total` 대비 검출 재현율                         | `가정:` 미측정 | `가정:` ≥95%(직접식별자) | 라벨 평가셋 vs 검출 |
| `transform_rate_avg`(검출분 변환율)                                | `가정:`        | `가정:` 100%             | 파이프라인 로그     |
| `llm_sensitive_block_total`(RESTRICTED/TRADE_SECRET 외부반출 차단) | 0              | `가정:` 유출 0           | 정책판단 이벤트     |
| `reidentification_risk_score_avg`                                  | `가정:`        | `가정:` < threshold      | risk_model 샘플링   |
| `export_approval_pending_total` / 재식별 키 접근                   | —              | 전건 audit               | 키 vault 접근 로그  |
| `documents_processed_total` (처리량)                               | —              | `가정:` SLO 미정         | OTel 메트릭         |

> **검증 가능한 수용 기준 (Given-When-Then, 시드·도메인 YAML 근거):**
>
> - 제조(C): _Given_ 배합/공정 수치 문서, _When_ 비식별, _Then_ 절대값 미보존·`RANGE_BUCKET`/recipe-token만 잔존, `trade_secret`이면 export 차단. (manufacturing.yaml, seed ip/\*)
> - 의료(Q): _Given_ 진료기록, _When_ 비식별, _Then_ 산출물에 직접식별자 없음(재식별 불가). (healthcare.yaml)
> - 금융(K): _Given_ 카드/계좌, _When_ 비식별, _Then_ PAN Luhn 검증 후 부분마스킹+토큰화, 외부 반출 차단. (finance.yaml, seed PRIV_FIN/financial)
> - 공통(J): _Given_ 멀티테넌트, _When_ 인덱싱, _Then_ 크로스테넌트 누출 0(RLS). (ict-saas.yaml)
> - OCR: _Given_ 손글씨 이미지, _When_ OCR→비식별, _Then_ OCR/IMAGE_CAPTION 산출물에도 룰 적용 확인.

## 6. 리스크 및 메모

- **주요 리스크:**
  - 도메인 ip(영업비밀) 룰은 정규식만으로 한계 → NER/dictionary 보강·오탐 튜닝 필요(검출률 변동).
  - 시드 룰 KR/EN 쌍·총 ~9.7K → 룰 충돌/우선순위(`priority`) 관리, 버전(`version`) 거버넌스 필요.
  - 재식별 위험 — 단일 마스킹 불충분, 결합 재식별 모니터링(risk_model 주기 점검).
  - 비식별 과다 → 검색·분석성 저하(범주화 입도 트레이드오프).
  - OCR 품질(손글씨) 편차 → 미검출 위험, 신뢰도 임계 기반 재검 필요.
- **의존성:**
  - 내부: 기존 문서 파이프라인, WFP + KSIC/ISIC/NACE/NAICS 매핑, `DocuGuard-AI-Policy` 룰 자산, `ksic.ts`, `model_catalog`.
  - 외부(오픈소스): 파싱/OCR(Tika·Unstructured·Tesseract·OCRmyPDF·GROBID), 검출/비식별(Presidio + spaCy NER + 도메인 사전), 정책엔진(OPA/Cedar), 관측성(Langfuse/OTel), (후속)권한(OpenFGA), 벡터(pgvector/Qdrant/Weaviate).
- **미결정 (Open Questions):**
  - 성공지표 기준선·목표 수치, 처리량 SLO.
  - vault(재식별 키/recipe 매핑) 저장소 + KMS/HSM 범위.
  - 룰번들 버전·배포 거버넌스(누가/언제 갱신, 충돌 해소).
  - 가드레일(런타임 I/O block/refuse)을 본 릴리즈에 포함할지 vs 비식별 우선 후속.
  - 공공(O)·예술여가(R) 도메인 우선순위(시드엔 존재, govtech/media-gaming YAML 별도).

---

## 7. 기술 메모 (Technical Notes) — 예시/초안

- **아키텍처(3계층):** 정책 원천(룰번들+DeidPolicy 스키마) → 파이프라인 훅(파싱·OCR·청킹·임베딩 각 단계) → 관측(Langfuse/OTel 대시보드). **민감 원문 저장소 ↔ 변환 후 검색용 저장소 분리.** 외부 모델 호출 전 정책판단 게이트.
- **핵심 컴포넌트:** ① 룰번들 로더/레지스트리(`category·priority·enabled·version`), ② 검출기(regex / regex+Luhn / NER / dictionary), ③ 정책 엔진(action 결정), ④ 변환기(REMOVE/MASK/TOKENIZE/GENERALIZE/RANGE_BUCKET/HASH + token vault), ⑤ OCR 어댑터(이미지·손글씨), ⑥ 청크 메타데이터/lineage, ⑦ 분리 인덱싱, ⑧ 거버넌스 대시보드.
- **정책 스키마(`DeidentificationPolicy`, md pack §3):** `policy_id·version·industry{ksic_section,domain,subdomain}·classification{default_level∈PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED, trade_secret_enabled, allowed_use∈SEARCH/RAG/FINE_TUNING/ANALYTICS/EXPORT}·rules[{field_type,detection{regex,ner_label,dictionary},action,replacement,applies_to,fine_tuning_allowed}]·risk_model{base_risk,reidentification_review{required,frequency,threshold_score}}·audit{log_input_hash,store_transform_map,approval_required_for_export,langfuse_trace_tags}`.
- **룰번들 스키마(시드 실측):** `{ruleId, domain, locale, ioType∈input/output/both, category, subCategory, description, patternType, patterns{regex[],luhnCheck}, severity∈low/medium/high/critical, priority(0-999), action, messageTemplate{ko-KR,en}, regulationTags[], examplesPositive[], examplesNegative[], enabled, version}`.
- **비기능 요구사항 (업종 오버레이, 출처 domains/\*.yaml):**
  - **베이스라인(ict-saas/J):** 멀티테넌트 격리(RLS), 크로스테넌트 누출 차단, OTel 관측성, OpenAPI 계약. 규제: 정보통신망법·PIPA·ISMS-P·CSAP / SOC2·ISO27001·GDPR.
  - **제조(C):** 영업비밀 범주화·recipe token, OT/IT 분리(IEC 62443), OT 데이터 온프렘 우선. ISA-95/IEC 62264. (seed tags: TRADE_SECRET·KR_OSH·EU_REACH·EU_CE·EU_MACHINERY_DIRECTIVE)
  - **의료(Q):** 필드레벨 암호화, 가명키 vault 격리, 불변 감사추적(ATNA), 비프로드 실 PHI 금지. PIPA §23·가명정보 특례·보건의료데이터 가이드라인(2024-12)·의료법 / HIPAA·GDPR Art.9. (tags: US_HIPAA·KR_MED_ACT·KR_PHARMA_ACT)
  - **금융(K):** 토큰화로 PCI scope 축소, 개인신용정보 비프로드 금지, append-only 감사, HSM/KMS. 전자금융거래법·신용정보법·전자금융감독규정(2025-02) / PCI-DSS 4.0.1. (tags: KR_FSC·KR_FSCMA·KR_CCA·PCI_DSS)
  - **공공(O)/예술여가(R):** 시드에 `public-administration`·`arts-recreation` 존재 — resident_registration·tax·welfare PII + venue/safety compliance. (govtech/media-gaming YAML 별도 매핑 필요)
- **데이터/로깅 (Langfuse, md pack §4):** trace 상단=문서/업종/정책 메타(`industry·ksic_section·document_type·sensitivity_level·policy_id`), 하위 span=`ocr.parse → deid.detect → deid.transform → authz.openfga.check → rag.answer`. 운영지표 §5.
- **외부 연동 / API:** `가정:` FastAPI 정책 평가기 + Presidio/(후속)OpenFGA/Langfuse. ingestion 필수 메타: `industry_code·document_type·region·source_system`.
- **리스크/트레이드오프:** 검출률 vs 오탐, 비식별 강도 vs 검색성, 온프렘(OT/PHI) vs 클라우드 비용, 룰 수(~9.7K) vs 평가 지연.

## 8. 실행 연결 (Epic / Story 힌트)

- **Epic 0 — 베이스라인:** 룰번들 로더/레지스트리 + DeidPolicy 스키마 + 멀티테넌트/관측성 골격 (`global`+`privacy` 적용).
- **Epic 1 — 검출 계층:** regex(+Luhn)/NER/dictionary 검출기, 우선순위·중복 해소.
- **Epic 2 — 변환 계층:** REMOVE/MASK/TOKENIZE/GENERALIZE/RANGE_BUCKET/HASH + token vault.
- **Epic 3 — OCR/이미지 경로:** 손글씨 이미지 OCR 어댑터 + OCR/IMAGE_CAPTION 비식별.
- **Epic 4 — 파이프라인 훅 + 분리 인덱싱:** 청크 메타데이터/lineage, 민감도별 namespace, 외부반출 차단 게이트.
- **Epic 5 — 도메인 오버레이:** 제조(C, 15 서브도메인) → 의료(Q) → 금융(K) → 공공(O)/예술여가(R) 순 룰셋·검증.
- **Epic 6 — 거버넌스 대시보드:** Langfuse/OTel 운영지표.
- **Epic 7 (후속) — 런타임 가드레일:** ioType input/output block/refuse/disclaimer (비식별 안정화 후).

## 9. 실행/프로세스 관리 표준 (환경별) — 추가 요구사항

- **인프라(datastore)**: `docker compose --env-file .env.<env>` (postgres+pgvector, redis; 프로파일 `app`=컨테이너 서비스).
- **서비스 프로세스(deid/rag/worker, host-native)**: **pm2**(`ecosystem.config.cjs`)로 환경별(local/dev/staging/prod) 기동·중지·로그·상태 통합. local 개발 편의를 위한 `uvx honcho`(`make run`)는 유지, pm2 경로가 표준.
- **워크스페이스 앱(portal/bff)**: pm2 대상에 포함(호스트 dev 프로세스로 등록), 기존 `make run-web`(pnpm 병렬)도 유지.
- **Makefile 타겟**: `make <env>-all`(compose 인프라 기동 + pm2 startOrRestart) / `<env>-stop` / `<env>-logs` / `<env>-ps`, `env ∈ {local,dev,staging,prod}`.
- **근거**: 참고 프로젝트(AITech-VLM-receipt) Makefile 패턴을 이식 — 인프라(compose)와 서비스(pm2)를 분리 관리해 재시작·로그 확인을 표준화.
- **bff (`apps/bff`)**: nest 스캐폴딩 완료(`nest-cli.json`/`tsconfig*.json`/`AppModule`/`AppController` + `GET /health`, :3001) — pm2 관리 대상(4앱: deid/rag/portal/bff) 편입. **OIDC SSO·RBAC/ABAC·감사로그·멀티테넌트 RLS 컨텍스트는 미구현**(다음 단계, AGENTS.md 상 bff 역할 정의 참고).

---

## 변경 이력

- 2026-07-23: §9 실행/프로세스 관리 표준(pm2 기반 환경별 Makefile 타겟) 추가.
- 2026-07-23: §9 bff nest 스캐폴딩 완료(health 엔드포인트) — pm2 4앱 편입. 인증/권한/감사 로직은 다음 단계로 이관.
- 2026-07-23: 작성자 표기 Wiseman.Lim 으로 수정(PRD.md·PRD.v2.md). §3 (P1) ⓖ 포털 E2E 파이프라인 UI 추가 — 기존 대시보드 전용 포털을 §1 한 줄 요약 전 과정 실행 UI 로 확장.
- 2026-07-23: 프로젝트명 RedactFlow → **DaD DeID Pipeline**(Domain-Aware Document De-Identification Pipeline) 으로 변경. 문서·표시 문구 전반 반영(코드 식별자 `redactflow`(DB·패키지명)는 보존).

### 자가 점검 (Definition of Ready)

- [x] 문제 정의가 실제 사용자 문제 설명(개인정보 + 업종 비공개 정보 + 손글씨 이미지)
- [x] In/Out Scope 둘 다 명확
- [△] 성공지표 측정 가능하나 **기준선·목표 `가정:`**(시드 평가셋/1차 후 확정)
- [x] 수용 기준 Given-When-Then(업종별 + OCR)
- [x] 의존성·리스크 명시(룰 거버넌스·OCR 품질·재식별·트레이드오프)
- [x] 규제·데이터등급 NFR/리스크 반영(국내+글로벌, 시드 regulationTags + domains/\*.yaml 근거)

> 근거: `.docs/seed/*.json`(24 도메인 룰번들), `.docs/deid-policy-and-langfuse-pack.md`(정책 스키마·Langfuse), `.docs/Perplexity-문서 업로드 비식별화.md`, `.docs/*.html`(시뮬레이터·대시보드 시안), `domains/{ict-saas,manufacturing,healthcare,finance}.yaml`
