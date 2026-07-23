// 포털 E2E 파이프라인 (PRD §1 한 줄 요약 / §3 ⓖ) — 서버 사이드에서 deid/rag REST 소비.
// 브라우저는 Next.js 라우트 핸들러(/api/*)만 호출 → deid/rag 직접 호출 없음(CORS 회피).

const DEID_BASE =
  process.env.DEID_API_BASE ?? process.env.NEXT_PUBLIC_DEID_API_BASE ?? "http://localhost:8001";
const RAG_BASE =
  process.env.RAG_API_BASE ?? process.env.NEXT_PUBLIC_RAG_API_BASE ?? "http://localhost:8002";

// deid /process 가 돌려주는 청크 (metadata 는 rag ChunkMetadata 계약과 일치).
export interface ChunkRecord {
  text: string;
  metadata: {
    chunk_id: string;
    sensitivity_level: string;
    transform_action: string;
    lineage: { rule_ids?: string[] };
    [k: string]: unknown;
  };
}

export interface ProcessResult {
  document_id: string;
  doc_sensitivity_level: string;
  chunk_count: number;
  chunks: ChunkRecord[];
}

export interface PipelineInput {
  mode: "text" | "document" | "image";
  document_id: string;
  industry_code?: string;
  project_id?: string;
  owner?: string;
  text?: string; // mode=text
  file_base64?: string; // mode=document
  content_type?: string; // mode=document
  image_base64?: string; // mode=image
}

export interface IndexOutcome {
  chunk_id: string;
  namespace: string;
  export_blocked: boolean;
}

export interface FlowResult {
  process: ProcessResult;
  indexed: IndexOutcome[];
}

function deidEndpoint(mode: PipelineInput["mode"]): string {
  if (mode === "document") return "/process-document";
  if (mode === "image") return "/process-image";
  return "/process";
}

// deid 검출→변환→청크. 입력 mode 별 페이로드 구성. 순수 매핑 — 테스트 대상.
export function buildDeidPayload(input: PipelineInput): Record<string, unknown> {
  const base = {
    document_id: input.document_id,
    industry_code: input.industry_code || null,
    project_id: input.project_id || "default",
    owner: input.owner || "portal",
  };
  if (input.mode === "document")
    return { ...base, file_base64: input.file_base64, content_type: input.content_type };
  if (input.mode === "image") return { ...base, image_base64: input.image_base64 };
  return { ...base, text: input.text ?? "" };
}

// 파이프라인: deid 처리 → 민감도별 rag 인덱싱 → 요약.
export async function runFlow(input: PipelineInput): Promise<FlowResult> {
  const proc = await fetch(`${DEID_BASE}${deidEndpoint(input.mode)}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(buildDeidPayload(input)),
    cache: "no-store",
  });
  if (!proc.ok) throw new Error(`deid ${input.mode} 실패: ${proc.status} ${await proc.text()}`);
  const process: ProcessResult = await proc.json();

  const indexed: IndexOutcome[] = [];
  for (const c of process.chunks) {
    const res = await fetch(`${RAG_BASE}/index`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ text: c.text, metadata: c.metadata }),
      cache: "no-store",
    });
    if (!res.ok) throw new Error(`rag /index 실패: ${res.status} ${await res.text()}`);
    indexed.push(await res.json());
  }
  return { process, indexed };
}

export interface SearchHit {
  chunk_id?: string;
  text?: string;
  sensitivity_level?: string;
  [k: string]: unknown;
}

export interface SearchResult {
  hits: SearchHit[];
  export_blocked_count: number;
  external: boolean;
}

export async function runSearch(
  query: string,
  project_id: string,
  external: boolean,
): Promise<SearchResult> {
  const res = await fetch(`${RAG_BASE}/search`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ query, project_id, external, top_k: 5 }),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`rag /search 실패: ${res.status} ${await res.text()}`);
  return res.json();
}

export interface DomainInfo {
  sections: Record<string, string[]>;
  ksic_map: Record<string, string>;
}

export async function fetchDomains(): Promise<DomainInfo> {
  const res = await fetch(`${DEID_BASE}/domains`, { cache: "no-store" });
  if (!res.ok) return { sections: {}, ksic_map: {} };
  return res.json();
}
