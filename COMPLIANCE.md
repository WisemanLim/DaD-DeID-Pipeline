# COMPLIANCE — DaD DeID Pipeline (다도메인 / multi-domain)

> 자동 생성. 근거: `domains/{ict-saas,healthcare,finance,manufacturing}.yaml` + `.docs` KSIC 통합표 + PRD v2.
> DaD DeID Pipeline 는 **다도메인 문서 비식별 파이프라인** — 베이스라인 `ict-saas`(J) + 오버레이 합집합
> `healthcare`(Q)·`finance`(K)·`manufacturing`(C), 후속 `govtech`(O)·`media-gaming`(R).
> **규제 충돌 시 더 강한 쪽 우선.** 규제는 변하므로 References 로 재확인.

## 분류 / Classification

| 도메인 | KSIC | ISIC/NACE | NAICS | 역할 |
|---|---|---|---|---|
| ict-saas | J | J | 51 | **베이스라인** (멀티테넌트·관측성·API-first) |
| healthcare | Q | Q | 62 | 오버레이 (PHI) |
| finance | K | K | 52 | 오버레이 (개인신용정보·카드) |
| manufacturing | C | C | 31-33 | 오버레이 (영업비밀) |
| govtech / media-gaming | O / R | — | 92 / 71 | 후속 (seed: public-administration, arts-recreation) |

## 한국 규제 (1순위) / Korea regulations

### 베이스라인 (J — ict-saas)
| 규제 | 시행 | 영향 |
|---|---|---|
| 정보통신망법 | — | 네트워크·정보보호 의무(§47=ISMS 근거), 침해사고 신고 |
| 개인정보보호법(PIPA) | — | PII 동의·최소화·유출통지(§32-2) |
| ISMS-P | 3년 주기 | 접근로그·변경관리·암호화 증적 |
| CSAP(클라우드) | 2025 온라인 발급 | 공공/정부 클라우드 IaaS/SaaS/DaaS 인증 |

### 의료 (Q — healthcare)
| 규제 | 시행 | 영향 |
|---|---|---|
| PIPA §23 민감정보 | — | 건강정보 별도동의 + **필드레벨 암호화** |
| PIPA 가명정보 특례 | — | 연구·AI 가명처리, 결합전문기관 경유, **재식별 경로 금지** |
| 보건의료데이터 활용 가이드라인 | 2024-12 | 비정형(영상·텍스트)·유전체 가명처리 방법·책임범위 |
| 의료법(§21·22·23) | — | EMR 보존, 진료정보 누설금지 → 변조방지 저장·감사 |
| 생명윤리법 | — | 인체유래물·유전정보 연구 IRB 승인 게이트 |

### 금융 (K — finance)
| 규제 | 시행 | 영향 |
|---|---|---|
| 전자금융거래법 | — | 안전성·무결성 의무 → 인증·로깅·책임추적 |
| 전자금융감독규정 | 2025-02-05 | 망분리 위험기반 예외, SaaS 별도기준, 가명정보 R&D 허용 |
| 신용정보법 | — | 개인신용정보 가명/익명 처리, **비프로드 반출 통제** |
| 마이데이터(MyData 2.0) | 2025-06-19 | 표준 전송 API + 동의원장 + 강인증/암호화 |
| 재해복구센터(DR) | 2026 단계적 | DR/BCP 인프라 필수 |

### 제조 (C — manufacturing)
| 규제 | 시행 | 영향 |
|---|---|---|
| 중대재해처벌법 | 시행령 2025-10-01 | 안전관리 AI 안전감시 + 감사 증적 |
| 산업안전보건법 | — | 안전보건 관리체계 증적 로깅 |
| OT 데이터 주권 | — | 공정/OT 데이터 온프렘·엣지 우선, 통제된 클라우드 복제 |
| 스마트공장 표준(KS X) | — | OPC-UA 정보모델·MQTT 토픽 준수 |

## 국제 기준 / Global compliance

- **공통:** SOC 2 Type II · ISO/IEC 27001 · GDPR (EU 테넌트)
- **의료:** HIPAA(PHI) · GDPR Art.9(특수범주·DPIA) · HL7 FHIR R4 · ISO 13485/IEC 62304(SaMD)
- **금융:** **PCI-DSS 4.0.1**(2025-03-31 의무, CDE 전구간 MFA) · ISO 20022 · PSD2 SCA/RBA · DORA/PQC
- **제조:** **EU REACH·CE·기계지침** · ISA-95/IEC 62264 · **ISA/IEC 62443**(OT 보안) · OPC-UA(IEC 62541)

## 데이터 등급 / Data classes

> ⚠️ **`규제대상` 등급은 비-프로덕션(dev/staging/test)에 실데이터 반입 금지** — 합성/비식별 데이터만.

| 데이터 | 등급 | 도메인 | 비고 |
|---|---|---|---|
| PHI/의료정보 | 규제대상 | Q | 의료법 보존·누설금지, **실 PHI 비프로드 금지** |
| 민감정보(건강)·유전정보 | 규제대상 | Q | PIPA §23, 생명윤리법 IRB |
| 개인신용정보 | 규제대상 | K | 신용정보법 최고민감, 비프로드 금지 |
| 결제/카드데이터(CHD/SAD) | 규제대상 | K | PCI-DSS scope, 토큰화로 범위 축소 |
| 영업비밀(배합비율/BOM/공정값) | 규제대상/민감 | C | RANGE_BUCKET·recipe token, vault 격리 |
| OT/제어 데이터 | 규제대상 | C | OT/IT 분리, 무결성 |
| 안전이벤트 데이터 | 규제대상 | C | 중대재해처벌법 증적 |
| 테넌트 데이터·고객 PII | 민감 | J | RLS 격리, PIPA/GDPR |
| 인증/키·아이덴티티 | 규제대상 | J/K | HSM/KMS 격리 |
| 가명정보 | 제한 | Q/K | 재식별 금지(Q), R&D 사용 가능(K, 2025) |
| 거래원장/감사로그 | 무결성 | K | append-only, 변조방지 |

## 인프라 패턴 / Infra patterns

- **멀티테넌트 RLS 격리** (J) — 크로스테넌트 누출 0 (PRD 공통 수용기준)
- **비식별 파이프라인** (Q/C) — 정형+비정형(영상/텍스트 마스킹·OCR redaction)+유전체, **가명키/recipe token vault 격리**
- **불변 감사추적** — ATNA(Q) · append-only + SIEM(K) · 안전감사 증적(C)
- **PCI scope 축소** (K) — PAN Luhn 검증 → 토큰화, CDE 네트워크 분리, HSM/KMS 단일 제어평면
- **OT/IT 분리** (C) — IEC 62443 존/컨듀잇, OT 데이터 온프렘·엣지 우선
- **민감 원문 저장소 ↔ 검색용 저장소 분리** (PRD §7), 외부 LLM 호출 전 정책판단 게이트
- 관측성: OpenTelemetry + Langfuse, 티어드 보관

## 개발환경 특수 요구 / dev-env special

- **비프로드 실데이터 금지** — PHI(Synthea 합성), 개인신용정보(합성 KYC/결제 샌드박스), 영업비밀(가짜 수치)만
- 코드→배포 **불변 감사추적** (ISMS-P 증적), 통제된 릴리스/서명 빌드
- 의료 SaMD 시 IEC 62304 SW 수명주기 + DHF 추적행렬 (해당 시)
- 금융 마이데이터 전송 API conformance 샌드박스 (해당 시)
- 제조 OPC-UA/MQTT 적합성 테스트 하네스 (해당 시)

## 추가 시험 (test/ 반영) / testing additions

- **비식별 검증**: 산출물에 직접식별자 없음(재식별 불가) — 의료 수용기준
- **크로스테넌트 누출 차단(RLS)** + OpenAPI 계약 적합성 — 베이스라인
- **PAN 토큰화 + CDE MFA** 검증 — 금융 수용기준
- **영업비밀**: 절대값 미보존·RANGE_BUCKET/recipe-token만 잔존, trade_secret export 차단 — 제조 수용기준
- **OCR**: OCR/IMAGE_CAPTION 산출물에도 룰 적용 확인
- 감사로그: 조회·다운로드·break-glass 기록

## 출처 / References

- ict-saas: ISMS-P(isms-p.or.kr), CSAP(isms.kisa.or.kr), SOC2/ISO(secureframe.com)
- healthcare: 건강정보고속도로(myhealthway.go.kr), 보건의료데이터 가이드라인(pipc.go.kr), EMR 인증제(emrcert.mohw.go.kr), FHIR(hl7.org/fhir)
- finance: 전자금융감독규정(fsc.go.kr/no010101/82885), 망분리 개선(fsc.go.kr/no010101/84780), PCI-DSS 4.0.1(pcisecuritystandards.org)
- manufacturing: ISA/IEC 62443(isa.org), ISA-95 2025(automation.com), 중대재해처벌법(saige.ai)
- PRD: `.docs/seed/*.json`(24 도메인 룰번들), `.docs/deid-policy-and-langfuse-pack.md`
