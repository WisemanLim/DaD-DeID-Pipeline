import { describe, expect, it } from "vitest";

import { formatKpis } from "@/lib/metrics";

describe("formatKpis", () => {
  it("normalizes deid+rag metrics into KPI cards (PRD §5)", () => {
    const kpis = formatKpis(
      { entities_detected_total: 12, transform_rate_avg: 1, documents_processed_total: 3, restricted_chunks_total: 2 },
      { llm_sensitive_block_total: 5, chunks_indexed_total: 7 },
    );
    const by = Object.fromEntries(kpis.map((k) => [k.key, k.value]));
    expect(by["entities_detected_total"]).toBe("12");
    expect(by["transform_rate_avg"]).toBe("100%");
    expect(by["llm_sensitive_block_total"]).toBe("5");
    expect(by["chunks_indexed_total"]).toBe("7");
  });

  it("defaults missing metrics to 0 / 0%", () => {
    const kpis = formatKpis({}, {});
    expect(kpis.find((k) => k.key === "transform_rate_avg")?.value).toBe("0%");
    expect(kpis.find((k) => k.key === "documents_processed_total")?.value).toBe("0");
    expect(kpis).toHaveLength(6);
  });

  it("tags source per KPI", () => {
    const kpis = formatKpis({}, {});
    expect(kpis.find((k) => k.key === "llm_sensitive_block_total")?.source).toBe("rag");
    expect(kpis.find((k) => k.key === "entities_detected_total")?.source).toBe("deid");
  });
});
