import { NextResponse } from "next/server";

import { runSearch } from "@/lib/pipeline";

export const dynamic = "force-dynamic";

// POST /api/search — 서버 프록시 → rag /search (외부반출 게이트).
export async function POST(req: Request) {
  try {
    const { query, project_id, external } = (await req.json()) as {
      query: string;
      project_id?: string;
      external?: boolean;
    };
    if (!query) return NextResponse.json({ error: "query 필요" }, { status: 400 });
    const result = await runSearch(query, project_id || "default", Boolean(external));
    return NextResponse.json(result);
  } catch (e) {
    return NextResponse.json({ error: String((e as Error).message ?? e) }, { status: 502 });
  }
}
