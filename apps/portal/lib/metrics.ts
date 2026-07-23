// 거버넌스 대시보드 — deid/rag /metrics 소비 (Epic 6 ⓕ)

export interface DeidMetrics {
  entities_detected_total?: number;
  entities_transformed_total?: number;
  transform_rate_avg?: number;
  documents_processed_total?: number;
  chunks_processed_total?: number;
  restricted_chunks_total?: number;
}

export interface RagMetrics {
  llm_sensitive_block_total?: number;
  chunks_indexed_total?: number;
  searches_total?: number;
}

export interface Kpi {
  key: string;
  label: string;
  value: string;
  source: "deid" | "rag";
}

const DEID_BASE = process.env.NEXT_PUBLIC_DEID_API_BASE ?? "http://localhost:8001";
const RAG_BASE = process.env.NEXT_PUBLIC_RAG_API_BASE ?? "http://localhost:8002";

// 순수 함수 — KPI 카드 배열로 정규화 (PRD §5 운영지표). 테스트 대상.
export function formatKpis(deid: DeidMetrics, rag: RagMetrics): Kpi[] {
  const pct = (v?: number) => `${Math.round((v ?? 0) * 100)}%`;
  const num = (v?: number) => String(v ?? 0);
  return [
    { key: "entities_detected_total", label: "검출 엔티티 누적", value: num(deid.entities_detected_total), source: "deid" },
    { key: "transform_rate_avg", label: "변환율", value: pct(deid.transform_rate_avg), source: "deid" },
    { key: "documents_processed_total", label: "처리 문서", value: num(deid.documents_processed_total), source: "deid" },
    { key: "restricted_chunks_total", label: "민감(RESTRICTED) 청크", value: num(deid.restricted_chunks_total), source: "deid" },
    { key: "llm_sensitive_block_total", label: "외부반출 차단", value: num(rag.llm_sensitive_block_total), source: "rag" },
    { key: "chunks_indexed_total", label: "인덱싱 청크", value: num(rag.chunks_indexed_total), source: "rag" },
  ];
}

export async function fetchKpis(): Promise<Kpi[]> {
  const [d, r] = await Promise.all([
    fetch(`${DEID_BASE}/metrics`, { cache: "no-store" }).then((x) => x.json()).catch(() => ({})),
    fetch(`${RAG_BASE}/metrics`, { cache: "no-store" }).then((x) => x.json()).catch(() => ({})),
  ]);
  return formatKpis(d, r);
}
