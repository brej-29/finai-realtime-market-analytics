"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";

import ReactMarkdown from "react-markdown";

type AssetType = "stock" | "crypto";

interface ResearchSection {
  name: string;
  title: string;
  text: string;
  tool_calls: { tool: string; input: Record<string, unknown> }[];
  error: string | null;
}

interface ResearchReport {
  id: number;
  symbol: string;
  asset_type: AssetType;
  status: "running" | "completed" | "failed";
  model: string;
  report_markdown: string | null;
  sections: ResearchSection[] | null;
  error: string | null;
  input_tokens: number;
  output_tokens: number;
  created_at: string;
  completed_at: string | null;
}

interface ResearchSummary {
  id: number;
  symbol: string;
  asset_type: AssetType;
  status: "running" | "completed" | "failed";
  created_at: string;
}

function getApiBase(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? `${window.location.origin}`;
}

const POLL_INTERVAL_MS = 3000;

export default function ResearchPage() {
  const [symbol, setSymbol] = useState("");
  const [assetType, setAssetType] = useState<AssetType>("stock");
  const [report, setReport] = useState<ResearchReport | null>(null);
  const [history, setHistory] = useState<ResearchSummary[]>([]);
  const [banner, setBanner] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const loadHistory = useCallback(async () => {
    try {
      const resp = await fetch(`${getApiBase()}/api/v1/research`);
      if (resp.ok) setHistory(await resp.json());
    } catch {
      // ignore; history panel just stays empty
    }
  }, []);

  const loadReport = useCallback(
    async (id: number) => {
      try {
        const resp = await fetch(`${getApiBase()}/api/v1/research/${id}`);
        if (!resp.ok) return;
        const data: ResearchReport = await resp.json();
        setReport(data);
        if (data.status !== "running") {
          stopPolling();
          loadHistory();
        }
      } catch {
        // transient network error; keep polling
      }
    },
    [loadHistory, stopPolling]
  );

  const startPolling = useCallback(
    (id: number) => {
      stopPolling();
      pollRef.current = setInterval(() => loadReport(id), POLL_INTERVAL_MS);
    },
    [loadReport, stopPolling]
  );

  useEffect(() => {
    loadHistory();
    return stopPolling;
  }, [loadHistory, stopPolling]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = symbol.trim().toUpperCase();
    if (!trimmed || starting) return;
    setBanner(null);
    setStarting(true);
    try {
      const resp = await fetch(`${getApiBase()}/api/v1/research`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol: trimmed, asset_type: assetType })
      });
      const data = await resp.json();
      if (!resp.ok) {
        setBanner(data.message ?? "Could not start research. Please try again.");
        return;
      }
      setReport(data);
      startPolling(data.id);
    } catch {
      setBanner("Could not reach the API. Please try again.");
    } finally {
      setStarting(false);
    }
  }

  function openReport(id: number) {
    stopPolling();
    loadReport(id);
  }

  const isRunning = report?.status === "running";

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">AI Research Desk</h1>
        <p className="text-sm text-slate-400">
          Three specialist agents — technical, news &amp; sentiment, and risk — research a
          symbol in parallel using live platform data, then a lead analyst compiles the brief.
        </p>
      </div>

      <form
        onSubmit={handleSubmit}
        className="flex flex-wrap gap-3 rounded-lg border border-slate-800 bg-slate-900/60 p-4 text-sm"
      >
        <input
          type="text"
          placeholder={assetType === "crypto" ? "Symbol (e.g. BTC)" : "Symbol (e.g. NVDA)"}
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          className="min-w-[140px] flex-1 rounded-md border border-slate-700 bg-slate-900 px-3 py-2 outline-none focus:border-brand-light"
        />
        <select
          value={assetType}
          onChange={(e) => setAssetType(e.target.value as AssetType)}
          className="rounded-md border border-slate-700 bg-slate-900 px-3 py-2 outline-none focus:border-brand-light"
          aria-label="Asset type"
        >
          <option value="stock">Stock</option>
          <option value="crypto">Crypto</option>
        </select>
        <button
          type="submit"
          disabled={starting || isRunning}
          className="rounded-md bg-brand px-4 py-2 font-medium text-slate-50 hover:bg-brand-light disabled:cursor-not-allowed disabled:opacity-50"
        >
          {starting ? "Starting…" : isRunning ? "Running…" : "Run research"}
        </button>
      </form>

      {banner && (
        <div className="rounded-lg border border-amber-700/60 bg-amber-900/20 p-3 text-sm text-amber-200">
          {banner}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          {isRunning && (
            <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-6 text-sm text-slate-300">
              <p className="font-medium">
                Researching {report?.symbol}… <span className="animate-pulse">●</span>
              </p>
              <p className="mt-2 text-xs text-slate-500">
                The technical, sentiment, and risk analysts are gathering data in parallel.
                This usually takes 20–60 seconds.
              </p>
            </div>
          )}

          {report?.status === "failed" && (
            <div className="rounded-lg border border-red-800/60 bg-red-900/20 p-4 text-sm text-red-200">
              Research failed: {report.error ?? "unknown error"}
            </div>
          )}

          {report?.status === "completed" && report.report_markdown && (
            <article className="rounded-lg border border-slate-800 bg-slate-900/60 p-5">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
                <h2 className="text-lg font-semibold">
                  {report.symbol}{" "}
                  <span className="rounded-full border border-slate-700 bg-slate-800/80 px-2 py-0.5 text-[11px] uppercase tracking-wide text-slate-300">
                    {report.asset_type}
                  </span>
                </h2>
                <p className="text-[11px] text-slate-500">
                  {report.model} · {report.input_tokens + report.output_tokens} tokens ·{" "}
                  {report.completed_at &&
                    new Date(report.completed_at).toLocaleString(undefined, {
                      month: "short",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit"
                    })}
                </p>
              </div>
              <div className="research-markdown text-sm leading-relaxed text-slate-300">
                <ReactMarkdown>{report.report_markdown}</ReactMarkdown>
              </div>
            </article>
          )}

          {report?.status === "completed" && report.sections && (
            <details className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 text-sm">
              <summary className="cursor-pointer font-medium text-slate-200">
                Analyst working notes &amp; tool calls
              </summary>
              <div className="mt-3 space-y-4">
                {report.sections.map((section) => (
                  <div key={section.name} className="border-t border-slate-800 pt-3">
                    <p className="font-medium text-slate-200">{section.title}</p>
                    <p className="mt-1 text-[11px] text-slate-500">
                      Tools used:{" "}
                      {section.tool_calls.length > 0
                        ? section.tool_calls.map((t) => t.tool).join(", ")
                        : "none"}
                    </p>
                    <p className="mt-2 whitespace-pre-wrap text-xs text-slate-400">
                      {section.text}
                    </p>
                  </div>
                ))}
              </div>
            </details>
          )}

          {!report && (
            <div className="rounded-lg border border-dashed border-slate-800 p-8 text-center text-sm text-slate-500">
              Run research on a symbol to see a multi-agent brief here, or open a past
              report from the list.
            </div>
          )}
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 text-sm">
          <h2 className="font-medium text-slate-200">Past reports</h2>
          <div className="mt-3 space-y-1">
            {history.length === 0 && (
              <p className="text-xs text-slate-500">No reports yet.</p>
            )}
            {history.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => openReport(item.id)}
                className={`flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left text-xs hover:bg-slate-800/60 ${
                  report?.id === item.id ? "bg-slate-800/60" : ""
                }`}
              >
                <span className="font-medium text-slate-200">
                  {item.symbol}
                  <span className="ml-1 uppercase text-[10px] text-slate-500">
                    {item.asset_type}
                  </span>
                </span>
                <span
                  className={
                    item.status === "completed"
                      ? "text-emerald-400"
                      : item.status === "failed"
                        ? "text-red-400"
                        : "text-amber-300"
                  }
                >
                  {item.status}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
