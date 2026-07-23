"use client";

import { useState } from "react";

import type { DomainInfo, FlowResult, SearchResult } from "@/lib/pipeline";

type Mode = "text" | "document" | "image";

const box = { border: "1px solid #e2e2e2", borderRadius: 12, padding: 20, marginTop: 16 } as const;
const label = { display: "block", fontSize: 13, color: "#555", marginBottom: 4 } as const;

// 민감도 배지 색 (외부반출 차단 등급 강조).
function levelColor(level: string): string {
  if (level === "RESTRICTED" || level === "TRADE_SECRET") return "#c0392b";
  if (level === "CONFIDENTIAL") return "#e67e22";
  if (level === "INTERNAL") return "#2980b9";
  return "#27ae60";
}

async function fileToBase64(file: File): Promise<string> {
  const buf = await file.arrayBuffer();
  let binary = "";
  const bytes = new Uint8Array(buf);
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
  return btoa(binary);
}

export default function PipelineClient({ domains }: { domains: DomainInfo }) {
  const industryOptions = Object.values(domains.sections ?? {}).flat();

  const [mode, setMode] = useState<Mode>("text");
  const [industry, setIndustry] = useState("");
  const [text, setText] = useState(
    "환자 900101-1234567, 카드 4242 4242 4242 4242, 메일 a@b.com 촉매비율 17.3%",
  );
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [flow, setFlow] = useState<FlowResult | null>(null);

  const [query, setQuery] = useState("");
  const [external, setExternal] = useState(false);
  const [search, setSearch] = useState<SearchResult | null>(null);

  const projectId = "portal";
  const docId = `portal-${Date.now()}`;

  async function submit() {
    setBusy(true);
    setErr("");
    setFlow(null);
    setSearch(null);
    try {
      const body: Record<string, unknown> = {
        mode,
        document_id: docId,
        industry_code: industry || undefined,
        project_id: projectId,
        owner: "portal",
      };
      if (mode === "text") body.text = text;
      else if (file) {
        const b64 = await fileToBase64(file);
        if (mode === "image") body.image_base64 = b64;
        else {
          body.file_base64 = b64;
          body.content_type = file.type || "application/octet-stream";
        }
      } else {
        throw new Error("파일을 선택하세요");
      }
      const res = await fetch("/api/process", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
      setFlow(data);
    } catch (e) {
      setErr(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  }

  async function doSearch() {
    setErr("");
    setSearch(null);
    try {
      const res = await fetch("/api/search", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ query, project_id: projectId, external }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
      setSearch(data);
    } catch (e) {
      setErr(String((e as Error).message ?? e));
    }
  }

  return (
    <div>
      {/* 1) 입력 */}
      <section style={box}>
        <h3 style={{ marginTop: 0 }}>1. 문서 입력</h3>
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap", marginBottom: 12 }}>
          <div>
            <span style={label}>입력 방식</span>
            <select value={mode} onChange={(e) => setMode(e.target.value as Mode)}>
              <option value="text">텍스트</option>
              <option value="document">파일 (PDF/DOCX/TXT)</option>
              <option value="image">이미지 (손글씨 OCR)</option>
            </select>
          </div>
          <div>
            <span style={label}>업종 (KSIC)</span>
            <select value={industry} onChange={(e) => setIndustry(e.target.value)}>
              <option value="">(기본 · global+privacy)</option>
              {industryOptions.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>
        </div>
        {mode === "text" ? (
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={4}
            style={{ width: "100%", fontFamily: "inherit", padding: 8 }}
          />
        ) : (
          <input
            type="file"
            accept={mode === "image" ? "image/*" : ".pdf,.docx,.txt"}
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        )}
        <div style={{ marginTop: 12 }}>
          <button onClick={submit} disabled={busy} style={{ padding: "8px 16px" }}>
            {busy ? "처리 중…" : "비식별 실행"}
          </button>
        </div>
        {err && <p style={{ color: "#c0392b", marginTop: 12 }}>⚠ {err}</p>}
      </section>

      {/* 2) 검출/변환 결과 + 3) 인덱싱 */}
      {flow && (
        <section style={box}>
          <h3 style={{ marginTop: 0 }}>2. 검출·변환 → 3. 분리 인덱싱</h3>
          <p>
            문서 민감도:{" "}
            <b style={{ color: levelColor(flow.process.doc_sensitivity_level) }}>
              {flow.process.doc_sensitivity_level}
            </b>{" "}
            · 청크 {flow.process.chunk_count}개
          </p>
          {flow.process.chunks.map((c, i) => {
            const idx = flow.indexed[i];
            return (
              <div
                key={c.metadata.chunk_id}
                style={{ borderTop: "1px solid #eee", paddingTop: 12, marginTop: 12 }}
              >
                <div style={{ fontSize: 13, color: "#888", marginBottom: 4 }}>
                  <span style={{ color: levelColor(c.metadata.sensitivity_level), fontWeight: 700 }}>
                    {c.metadata.sensitivity_level}
                  </span>{" "}
                  · 변환: {c.metadata.transform_action || "(없음)"} · 룰:{" "}
                  {(c.metadata.lineage?.rule_ids ?? []).length}건
                  {idx?.export_blocked && (
                    <span style={{ color: "#c0392b" }}> · 🚫 외부반출 차단</span>
                  )}
                  {idx && <span> · namespace={idx.namespace}</span>}
                </div>
                <div style={{ fontFamily: "monospace", fontSize: 13, whiteSpace: "pre-wrap" }}>
                  {c.text}
                </div>
              </div>
            );
          })}
        </section>
      )}

      {/* 4) 검색 */}
      {flow && (
        <section style={box}>
          <h3 style={{ marginTop: 0 }}>4. 검색 (외부반출 게이트)</h3>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="검색어"
              style={{ flex: 1, minWidth: 200, padding: 8 }}
            />
            <label style={{ fontSize: 13 }}>
              <input
                type="checkbox"
                checked={external}
                onChange={(e) => setExternal(e.target.checked)}
              />{" "}
              외부 LLM 반출 컨텍스트
            </label>
            <button onClick={doSearch} style={{ padding: "8px 16px" }}>
              검색
            </button>
          </div>
          {search && (
            <div style={{ marginTop: 12 }}>
              <p>
                결과 {search.hits.length}건
                {search.external && (
                  <span style={{ color: "#c0392b" }}>
                    {" "}
                    · 차단 {search.export_blocked_count}건
                  </span>
                )}
              </p>
              {search.hits.map((h, i) => (
                <div key={i} style={{ borderTop: "1px solid #eee", paddingTop: 8, marginTop: 8 }}>
                  <span style={{ color: levelColor(h.sensitivity_level ?? ""), fontSize: 12 }}>
                    {h.sensitivity_level}
                  </span>{" "}
                  <span style={{ fontFamily: "monospace", fontSize: 13 }}>{h.text}</span>
                </div>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
