import { describe, expect, it } from "vitest";

import { buildDeidPayload } from "@/lib/pipeline";

describe("buildDeidPayload", () => {
  it("text mode → /process payload", () => {
    const p = buildDeidPayload({ mode: "text", document_id: "d1", text: "hi", industry_code: "finance-banking" });
    expect(p).toMatchObject({ document_id: "d1", text: "hi", industry_code: "finance-banking", owner: "portal" });
  });

  it("document mode carries file_base64 + content_type", () => {
    const p = buildDeidPayload({ mode: "document", document_id: "d2", file_base64: "QUJD", content_type: "application/pdf" });
    expect(p).toMatchObject({ file_base64: "QUJD", content_type: "application/pdf" });
    expect(p).not.toHaveProperty("text");
  });

  it("image mode carries image_base64", () => {
    const p = buildDeidPayload({ mode: "image", document_id: "d3", image_base64: "SU1H" });
    expect(p).toMatchObject({ image_base64: "SU1H" });
  });

  it("defaults industry_code=null, project_id=default when omitted", () => {
    const p = buildDeidPayload({ mode: "text", document_id: "d4", text: "x" });
    expect(p.industry_code).toBeNull();
    expect(p.project_id).toBe("default");
  });
});
