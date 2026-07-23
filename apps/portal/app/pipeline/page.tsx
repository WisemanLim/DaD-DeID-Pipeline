import Link from "next/link";

import { fetchDomains } from "@/lib/pipeline";
import PipelineClient from "./PipelineClient";

export const dynamic = "force-dynamic";

// PRD §1 한 줄 요약 흐름을 실행하는 포털 UI (§3 ⓖ). 업종 목록은 서버에서 deid /domains 로 선적재.
export default async function PipelinePage() {
  const domains = await fetchDomains();
  return (
    <main style={{ maxWidth: 960, margin: "0 auto", padding: 32, fontFamily: "system-ui" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <h1>DaD DeID Pipeline — 문서 비식별 파이프라인</h1>
        <Link href="/" style={{ fontSize: 14 }}>
          ← 대시보드
        </Link>
      </div>
      <p style={{ color: "#666" }}>
        업로드 → 파싱/OCR → 검출 → 정책 변환 → 민감도별 분리 인덱싱 → 검색 (PRD §1)
      </p>
      <PipelineClient domains={domains} />
    </main>
  );
}
