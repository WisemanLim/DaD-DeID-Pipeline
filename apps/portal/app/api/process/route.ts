import { NextResponse } from "next/server";

import { runFlow, type PipelineInput } from "@/lib/pipeline";

export const dynamic = "force-dynamic";

// POST /api/process — 브라우저 → 서버 프록시 → deid 처리 + rag 인덱싱 (CORS 회피).
export async function POST(req: Request) {
  try {
    const input = (await req.json()) as PipelineInput;
    if (!input.document_id) return NextResponse.json({ error: "document_id 필요" }, { status: 400 });
    const result = await runFlow(input);
    return NextResponse.json(result);
  } catch (e) {
    return NextResponse.json({ error: String((e as Error).message ?? e) }, { status: 502 });
  }
}
