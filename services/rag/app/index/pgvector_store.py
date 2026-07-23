"""pgvector VectorStore 어댑터 (Epic 4 / VECTOR_BACKEND=pgvector).

postgres + pgvector 백엔드. 임베딩 = 공유 embedder(실모델 또는 해시 폴백) → dim 동적.
namespace=민감도 컬럼, project_id 테넌트 격리, RESTRICTED/TRADE_SECRET 외부반출 게이트는 쿼리 WHERE 로.
DB 미가용 시 import/connect 에서 예외 → 호출부가 in-memory 로 폴백.
dim 마이그레이션(dev): 기존 테이블 컬럼 dim 이 embedder.dim 과 다르면 재생성(데이터 비움). prod=Alembic.
"""
from __future__ import annotations

import hashlib

from app.index.embedder import get_embedder
from app.index.schema import SensitivityLevel
from app.index.store import IndexedChunk, SearchHit, VectorStore

_DIM = 64


def hash_embedding(text: str, dim: int = _DIM) -> list[float]:
    """결정적 해시 임베딩 — 토큰별 해시 버킷 카운트 → L2 정규화 (폴백/하위호환)."""
    vec = [0.0] * dim
    for tok in text.lower().split():
        h = int(hashlib.sha256(tok.encode()).hexdigest(), 16)
        vec[h % dim] += 1.0
    norm = sum(v * v for v in vec) ** 0.5
    return [v / norm for v in vec] if norm else vec


class PgVectorStore(VectorStore):
    def __init__(self, dsn: str) -> None:
        import psycopg
        from pgvector.psycopg import register_vector

        self._emb = get_embedder()
        self._dim = self._emb.dim
        self._conn = psycopg.connect(dsn, autocommit=True)
        self._conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        register_vector(self._conn)
        self._migrate_dim()
        self._conn.execute(f"""
            CREATE TABLE IF NOT EXISTS rag_chunks (
                chunk_id   TEXT PRIMARY KEY,
                document_id TEXT,
                project_id TEXT,
                sensitivity TEXT,
                text       TEXT,
                embedding  vector({self._dim})
            )""")
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS rag_chunks_proj ON rag_chunks (project_id, sensitivity)"
        )

    def _migrate_dim(self) -> None:
        """기존 rag_chunks.embedding dim 이 현재 embedder.dim 과 다르면 dev 재생성."""
        row = self._conn.execute("""
            SELECT a.atttypmod FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            WHERE c.relname='rag_chunks' AND a.attname='embedding'
        """).fetchone()
        if row and row[0] not in (None, -1) and row[0] != self._dim:
            print(f"[rag] pgvector dim {row[0]}→{self._dim} 마이그레이션(테이블 재생성)")
            self._conn.execute("DROP TABLE rag_chunks")

    def _embed(self, text: str) -> list[float]:
        return self._emb.embed(text)

    def upsert(self, chunk: IndexedChunk) -> None:
        m = chunk.metadata
        self._conn.execute(
            """INSERT INTO rag_chunks (chunk_id, document_id, project_id, sensitivity, text, embedding)
               VALUES (%s,%s,%s,%s,%s,%s)
               ON CONFLICT (chunk_id) DO UPDATE SET text=EXCLUDED.text, embedding=EXCLUDED.embedding""",
            (m.chunk_id, m.document_id, m.project_id, m.sensitivity_level.value,
             chunk.text, self._embed(chunk.text)),
        )

    def query(self, text, project_id, external, top_k=5):
        blocked_levels = (SensitivityLevel.RESTRICTED.value, SensitivityLevel.TRADE_SECRET.value)
        emb = self._embed(text)
        sql = "SELECT chunk_id, document_id, sensitivity, text, 1-(embedding <=> %s::vector) AS score FROM rag_chunks WHERE project_id=%s"
        params: list = [emb, project_id]
        blocked = 0
        if external:
            # 차단 대상 건수 집계
            cur = self._conn.execute(
                "SELECT count(*) FROM rag_chunks WHERE project_id=%s AND sensitivity = ANY(%s)",
                (project_id, list(blocked_levels)),
            )
            blocked = cur.fetchone()[0]
            sql += " AND sensitivity <> ALL(%s)"
            params.append(list(blocked_levels))
        sql += " ORDER BY score DESC LIMIT %s"
        params.append(top_k)
        hits = []
        for chunk_id, doc_id, sens, txt, score in self._conn.execute(sql, params).fetchall():
            if score and score > 0:
                hits.append(SearchHit(
                    chunk_id=chunk_id, document_id=doc_id,
                    sensitivity_level=SensitivityLevel(sens), score=round(float(score), 4), text=txt,
                ))
        return hits, blocked

    def namespaces(self) -> dict[str, int]:
        rows = self._conn.execute(
            "SELECT sensitivity, count(*) FROM rag_chunks GROUP BY sensitivity"
        ).fetchall()
        return {s: n for s, n in sorted(rows)}
