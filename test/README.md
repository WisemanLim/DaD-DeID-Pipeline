# test/ — 시험 표준 / testing standard

test-runner 표준. 사이클: **시나리오 작성 → 시험 진행 → 오류 시 수정·재시험 → 결과 작성**.

```
test/
├── README.md            # 이 문서
├── dev-env/             # 표준 환경 검증 (1회) / env verification, once
│   ├── scenario.md
│   └── logs/
└── impl/                # 구현마다 차수 증가 / per implementation
    └── <Nth>/           # /wise-dev-standard:implement 가 생성
```

- 러너: `pnpm -r test`(Vitest, portal/bff) + `uv run pytest`(deid/rag) + **Ragas**(RAG groundedness/recall/MRR, `pytest -m ragas`).
- 도메인 추가 시험은 `COMPLIANCE.md` "추가 시험" 항 → `dev-env`/`impl/<Nth>` 케이스로 연결.
- 원본 로그(`test/**/logs/`)는 비커밋(.gitignore).
