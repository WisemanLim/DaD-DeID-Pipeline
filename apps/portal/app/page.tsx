import Link from "next/link";

import { fetchKpis } from "@/lib/metrics";

export const dynamic = "force-dynamic";

export default async function Dashboard() {
  const kpis = await fetchKpis();
  return (
    <main style={{ maxWidth: 960, margin: "0 auto", padding: 32, fontFamily: "system-ui" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <h1>DaD DeID Pipeline — 거버넌스 대시보드</h1>
        <Link href="/pipeline" style={{ fontSize: 14 }}>
          문서 비식별 파이프라인 →
        </Link>
      </div>
      <p style={{ color: "#666" }}>PRD §5 운영지표 (deid:8001 · rag:8002 /metrics 실시간)</p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginTop: 24 }}>
        {kpis.map((k) => (
          <div key={k.key} style={{ border: "1px solid #e2e2e2", borderRadius: 12, padding: 20 }}>
            <div style={{ fontSize: 13, color: "#888" }}>
              {k.label} <span style={{ fontSize: 11, color: "#bbb" }}>({k.source})</span>
            </div>
            <div style={{ fontSize: 32, fontWeight: 700, marginTop: 8 }}>{k.value}</div>
          </div>
        ))}
      </div>
    </main>
  );
}
