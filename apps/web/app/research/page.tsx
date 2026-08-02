"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";

import { AnimatePresence, motion } from "motion/react";
import {
  Check,
  ChevronDown,
  ClipboardList,
  Gauge,
  History,
  Newspaper,
  Sparkles,
  TrendingUp,
  X,
  Zap
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import { toast } from "sonner";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { apiFetch, getApiBase } from "@/lib/api";
import { cn, relativeTime } from "@/lib/utils";

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
  provider: string;
  report_markdown: string | null;
  sections: ResearchSection[] | null;
  error: string | null;
  input_tokens: number;
  output_tokens: number;
  estimated_cost_usd: number;
  created_at: string;
  completed_at: string | null;
}

interface ResearchSummary {
  id: number;
  symbol: string;
  asset_type: AssetType;
  status: "running" | "completed" | "failed";
  provider: string;
  estimated_cost_usd: number;
  created_at: string;
}

interface ResearchBudget {
  spent_usd: number;
  budget_usd: number;
  remaining_usd: number;
  next_run_provider: "anthropic" | "groq" | "disabled";
}

const AGENT_META: Record<string, { icon: typeof TrendingUp; label: string }> = {
  technical: { icon: TrendingUp, label: "Technical Analyst" },
  sentiment: { icon: Newspaper, label: "News & Sentiment Analyst" },
  risk: { icon: Gauge, label: "Risk Analyst" }
};

const PROVIDER_META: Record<string, { icon: typeof Sparkles; label: string; variant: "brand" | "warning" }> = {
  anthropic: { icon: Sparkles, label: "Claude Haiku", variant: "brand" },
  groq: { icon: Zap, label: "Groq Llama", variant: "warning" }
};

function ProviderBadge({ provider }: { provider: string }) {
  const meta = PROVIDER_META[provider] ?? { icon: Sparkles, label: provider, variant: "brand" as const };
  const Icon = meta.icon;
  return (
    <Badge variant={meta.variant}>
      <Icon className="h-3 w-3" />
      {meta.label}
    </Badge>
  );
}

function formatCost(usd: number): string {
  return `$${usd.toFixed(4)}`;
}

function BudgetMeter({ budget }: { budget: ResearchBudget }) {
  const pct = budget.budget_usd > 0 ? Math.min(100, (budget.spent_usd / budget.budget_usd) * 100) : 0;
  const nextMeta = PROVIDER_META[budget.next_run_provider];
  return (
    <div className="flex flex-col gap-1.5 rounded-lg border bg-surface/40 px-3 py-2 text-[11px] text-muted sm:min-w-[200px]">
      <div className="flex items-center justify-between gap-2">
        <span>Daily Anthropic budget</span>
        <span className="font-medium text-foreground">
          {formatCost(budget.spent_usd)} / {formatCost(budget.budget_usd)}
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-hover">
        <motion.div
          className={cn("h-full rounded-full", pct >= 100 ? "bg-warning" : "bg-brand")}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.6, ease: "easeOut" }}
        />
      </div>
      {nextMeta && (
        <span className="flex items-center gap-1">
          Next run via <nextMeta.icon className="h-3 w-3" /> {nextMeta.label}
        </span>
      )}
      {budget.next_run_provider === "disabled" && <span>No provider configured.</span>}
    </div>
  );
}

const POLL_INTERVAL_MS = 3000;
const SHARED_REPORT_THRESHOLD_MS = 2 * 60 * 1000;

function formatSharedTimestamp(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit"
  });
}

type AgentLiveStatus = "idle" | "working" | "done" | "failed";

interface AgentLiveState {
  status: AgentLiveStatus;
  toolCalls: { tool: string; input: Record<string, unknown> }[];
}

function initialLiveAgents(): Record<string, AgentLiveState> {
  return {
    technical: { status: "idle", toolCalls: [] },
    sentiment: { status: "idle", toolCalls: [] },
    risk: { status: "idle", toolCalls: [] }
  };
}

function primaryInputValue(input: Record<string, unknown>): string | null {
  if (!input) return null;
  if ("symbol" in input) return String(input.symbol);
  const values = Object.values(input);
  return values.length ? String(values[0]) : null;
}

type StreamEvent =
  | { type: "agent_started"; agent: string; title: string }
  | { type: "tool_call"; agent: string; tool: string; input: Record<string, unknown> }
  | { type: "agent_completed"; agent: string; ok: boolean }
  | { type: "synthesis_started" }
  | { type: "done"; status: "completed" | "failed"; report_id: number }
  | { type: "error"; message: string };

function LiveAgentRow({ name, state, index }: { name: string; state: AgentLiveState; index: number }) {
  const meta = AGENT_META[name] ?? { icon: Sparkles, label: name };
  const Icon = meta.icon;
  const isWorking = state.status === "working";
  const isDone = state.status === "done";
  const isFailed = state.status === "failed";

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08 }}
      className="rounded-xl border bg-surface/60 px-3.5 py-3"
    >
      <div className="flex items-center gap-3">
        <span
          className={cn(
            "relative flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
            isFailed
              ? "bg-negative/10 text-negative"
              : isDone
                ? "bg-positive/10 text-positive"
                : "bg-brand/10 text-brand-light"
          )}
        >
          {isWorking && (
            <motion.span
              className="absolute inset-0 rounded-full border border-brand/40"
              animate={{ scale: [1, 1.35], opacity: [0.6, 0] }}
              transition={{ duration: 1.4, repeat: Infinity, delay: index * 0.2 }}
            />
          )}
          {isDone ? <Check className="h-4 w-4" /> : isFailed ? <X className="h-4 w-4" /> : <Icon className="h-4 w-4" />}
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-foreground">{meta.label}</p>
          <p className="text-[11px] text-muted">
            {isFailed
              ? "Could not complete"
              : isDone
                ? "Done"
                : isWorking
                  ? "Gathering data and analyzing…"
                  : "Waiting…"}
          </p>
        </div>
        {isWorking && <Badge variant="brand">working</Badge>}
        {isDone && <Badge variant="positive">done</Badge>}
        {isFailed && <Badge variant="negative">failed</Badge>}
      </div>
      {state.toolCalls.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5 pl-11">
          {state.toolCalls.map((t, i) => {
            const primary = primaryInputValue(t.input);
            return (
              <span
                key={i}
                className="rounded-md bg-surface-hover px-1.5 py-0.5 font-mono text-[10px] text-muted"
              >
                {t.tool}
                {primary ? `(${primary})` : ""}
              </span>
            );
          })}
        </div>
      )}
    </motion.div>
  );
}

function AgentWorkingCard({ name, index }: { name: string; index: number }) {
  const meta = AGENT_META[name] ?? { icon: Sparkles, label: name };
  const Icon = meta.icon;
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08 }}
      className="flex items-center gap-3 rounded-xl border bg-surface/60 px-3.5 py-3"
    >
      <span className="relative flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand/10 text-brand-light">
        <motion.span
          className="absolute inset-0 rounded-full border border-brand/40"
          animate={{ scale: [1, 1.35], opacity: [0.6, 0] }}
          transition={{ duration: 1.4, repeat: Infinity, delay: index * 0.2 }}
        />
        <Icon className="h-4 w-4" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-foreground">{meta.label}</p>
        <p className="text-[11px] text-muted">Gathering data and analyzing…</p>
      </div>
    </motion.div>
  );
}

function AgentNoteCard({ section }: { section: ResearchSection }) {
  const [open, setOpen] = useState(false);
  const meta = AGENT_META[section.name] ?? { icon: Sparkles, label: section.title };
  const Icon = meta.icon;

  return (
    <div className="rounded-xl border bg-surface/40">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex w-full items-center justify-between gap-2 px-3.5 py-3 text-left"
      >
        <span className="flex items-center gap-2.5">
          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-brand/10 text-brand-light">
            <Icon className="h-3.5 w-3.5" />
          </span>
          <span className="text-sm font-medium text-foreground">{section.title}</span>
          {section.error && <Badge variant="negative">unavailable</Badge>}
        </span>
        <ChevronDown className={cn("h-4 w-4 text-muted transition-transform", open && "rotate-180")} />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="space-y-2 border-t px-3.5 py-3">
              {section.tool_calls.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {section.tool_calls.map((t, i) => (
                    <Badge key={i} variant="outline">
                      {t.tool}
                    </Badge>
                  ))}
                </div>
              )}
              <p className="whitespace-pre-wrap text-xs leading-relaxed text-muted">{section.text}</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function ResearchPage() {
  const [symbol, setSymbol] = useState("");
  const [assetType, setAssetType] = useState<AssetType>("stock");
  const [report, setReport] = useState<ResearchReport | null>(null);
  const [history, setHistory] = useState<ResearchSummary[]>([]);
  const [starting, setStarting] = useState(false);
  const [budget, setBudget] = useState<ResearchBudget | null>(null);
  const [liveAgents, setLiveAgents] = useState<Record<string, AgentLiveState>>(initialLiveAgents());
  const [synthesizing, setSynthesizing] = useState(false);
  const [sseActive, setSseActive] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const esRef = useRef<EventSource | null>(null);

  const loadBudget = useCallback(async () => {
    try {
      const resp = await apiFetch("/api/v1/research/budget");
      if (resp.ok) setBudget(await resp.json());
    } catch {
      // ignore; meter just stays hidden
    }
  }, []);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const closeStream = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
    setSseActive(false);
  }, []);

  const loadHistory = useCallback(async () => {
    try {
      const resp = await apiFetch("/api/v1/research");
      if (resp.ok) setHistory(await resp.json());
    } catch {
      // ignore; history panel just stays empty
    }
  }, []);

  const loadReport = useCallback(
    async (id: number) => {
      try {
        const resp = await apiFetch(`/api/v1/research/${id}`);
        if (!resp.ok) return;
        const data: ResearchReport = await resp.json();
        setReport(data);
        if (data.status !== "running") {
          stopPolling();
          closeStream();
          loadHistory();
          loadBudget();
          if (data.status === "failed") {
            toast.error(`Research on ${data.symbol} failed: ${data.error ?? "unknown error"}`);
          } else {
            toast.success(`Research brief for ${data.symbol} is ready`);
          }
        }
      } catch {
        // transient network error; keep polling
      }
    },
    [loadHistory, loadBudget, stopPolling, closeStream]
  );

  const startPolling = useCallback(
    (id: number) => {
      stopPolling();
      pollRef.current = setInterval(() => loadReport(id), POLL_INTERVAL_MS);
    },
    [loadReport, stopPolling]
  );

  const startStream = useCallback(
    (id: number) => {
      closeStream();
      stopPolling();
      setLiveAgents(initialLiveAgents());
      setSynthesizing(false);

      const es = new EventSource(`${getApiBase()}/api/v1/research/${id}/stream`, { withCredentials: true });
      esRef.current = es;
      setSseActive(true);

      es.onmessage = (evt) => {
        let msg: StreamEvent;
        try {
          msg = JSON.parse(evt.data) as StreamEvent;
        } catch {
          return;
        }
        switch (msg.type) {
          case "agent_started":
            setLiveAgents((prev) => ({
              ...prev,
              [msg.agent]: { status: "working", toolCalls: prev[msg.agent]?.toolCalls ?? [] }
            }));
            break;
          case "tool_call":
            setLiveAgents((prev) => {
              const existing = prev[msg.agent] ?? { status: "working", toolCalls: [] };
              return {
                ...prev,
                [msg.agent]: {
                  ...existing,
                  toolCalls: [...existing.toolCalls, { tool: msg.tool, input: msg.input ?? {} }]
                }
              };
            });
            break;
          case "agent_completed":
            setLiveAgents((prev) => {
              const existing = prev[msg.agent] ?? { status: "working", toolCalls: [] };
              return { ...prev, [msg.agent]: { ...existing, status: msg.ok ? "done" : "failed" } };
            });
            break;
          case "synthesis_started":
            setSynthesizing(true);
            break;
          case "done":
            closeStream();
            loadReport(id);
            break;
          case "error":
            closeStream();
            startPolling(id);
            break;
          default:
            break;
        }
      };

      es.onerror = () => {
        closeStream();
        startPolling(id);
      };
    },
    [closeStream, stopPolling, loadReport, startPolling]
  );

  useEffect(() => {
    loadHistory();
    loadBudget();
    return () => {
      stopPolling();
      closeStream();
    };
  }, [loadHistory, loadBudget, stopPolling, closeStream]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = symbol.trim().toUpperCase();
    if (!trimmed || starting) return;
    setStarting(true);
    try {
      const resp = await apiFetch("/api/v1/research", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol: trimmed, asset_type: assetType })
      });
      const data = await resp.json();
      if (!resp.ok) {
        toast.error(data.message ?? "Could not start research. Please try again.");
        return;
      }
      const newReport: ResearchReport = data;
      setReport(newReport);
      if (newReport.status === "running") {
        toast(`Researching ${trimmed}…`, { description: "Three agents are gathering data in parallel." });
        startStream(newReport.id);
      } else {
        toast(`Showing existing research for ${trimmed}`, {
          description: `Generated ${newReport.completed_at ? relativeTime(newReport.completed_at) : "recently"}`
        });
        loadHistory();
        loadBudget();
      }
    } catch {
      toast.error("Could not reach the API. Please try again.");
    } finally {
      setStarting(false);
    }
  }

  function openReport(id: number) {
    stopPolling();
    closeStream();
    loadReport(id);
  }

  const isRunning = report?.status === "running";
  const isSharedReport =
    report?.status === "completed" &&
    !!report.completed_at &&
    Date.now() - new Date(report.completed_at).getTime() > SHARED_REPORT_THRESHOLD_MS;

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mx-auto max-w-5xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand/10 text-brand-light">
            <Sparkles className="h-4 w-4" />
          </span>
          <div>
            <h1 className="font-display text-2xl font-semibold tracking-tight text-foreground">AI Research Desk</h1>
            <p className="text-sm text-muted">
              Three specialist agents research a symbol in parallel using live platform data, then a lead
              analyst compiles the brief.
            </p>
          </div>
        </div>
        {budget && <BudgetMeter budget={budget} />}
      </div>

      <Card className="p-4">
        <form onSubmit={handleSubmit} className="flex flex-wrap gap-2.5">
          <Input
            type="text"
            placeholder={assetType === "crypto" ? "Symbol (e.g. BTC)" : "Symbol (e.g. NVDA)"}
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="min-w-[160px] flex-1"
          />
          <Select value={assetType} onChange={(e) => setAssetType(e.target.value as AssetType)} aria-label="Asset type">
            <option value="stock">Stock</option>
            <option value="crypto">Crypto</option>
          </Select>
          <Button type="submit" disabled={starting || isRunning || !symbol.trim()}>
            {starting ? "Starting…" : isRunning ? "Running…" : "Run research"}
          </Button>
        </form>
      </Card>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          {isRunning && (
            <Card className="space-y-2.5 p-4">
              <p className="mb-1 text-sm font-medium text-foreground">Researching {report?.symbol}…</p>
              {sseActive ? (
                <>
                  {["technical", "sentiment", "risk"].map((name, i) => (
                    <LiveAgentRow key={name} name={name} state={liveAgents[name]} index={i} />
                  ))}
                  {synthesizing && (
                    <motion.div
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="flex items-center gap-2 rounded-xl border border-brand/20 bg-brand/5 px-3.5 py-3 text-sm text-brand-light"
                    >
                      <Sparkles className="h-4 w-4" />
                      Lead analyst is compiling the brief…
                    </motion.div>
                  )}
                </>
              ) : (
                ["technical", "sentiment", "risk"].map((name, i) => (
                  <AgentWorkingCard key={name} name={name} index={i} />
                ))
              )}
            </Card>
          )}

          {report?.status === "failed" && (
            <Card className="border-negative/30 bg-negative/5 p-4 text-sm text-negative">
              Research failed: {report.error ?? "unknown error"}
            </Card>
          )}

          <AnimatePresence>
            {report?.status === "completed" && report.report_markdown && (
              <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}>
                <Card spotlight className="p-5">
                  {isSharedReport && report.completed_at && (
                    <div className="mb-3 flex flex-wrap items-center gap-2 rounded-lg border border-brand/20 bg-brand/5 px-3 py-2 text-xs">
                      <History className="h-3.5 w-3.5 shrink-0 text-brand-light" />
                      <span className="font-medium text-foreground">
                        Shared research from {formatSharedTimestamp(report.completed_at)}
                      </span>
                      <span className="text-muted">
                        Reused from the shared cache — reports are reused for 4 days to keep API costs down.
                      </span>
                    </div>
                  )}
                  <div className="mb-3 flex flex-wrap items-center justify-between gap-2 border-b pb-3">
                    <h2 className="flex items-center gap-2 text-lg font-semibold text-foreground">
                      {report.symbol}
                      <Badge variant="outline" className="uppercase">
                        {report.asset_type}
                      </Badge>
                    </h2>
                    <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-muted">
                      <ProviderBadge provider={report.provider} />
                      <Badge variant="outline">{report.model}</Badge>
                      <span>{report.input_tokens + report.output_tokens} tokens</span>
                      <span>· {formatCost(report.estimated_cost_usd)}</span>
                      {report.completed_at && (
                        <span>
                          ·{" "}
                          {new Date(report.completed_at).toLocaleString(undefined, {
                            month: "short",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit"
                          })}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="research-markdown text-sm leading-relaxed text-muted">
                    <ReactMarkdown>{report.report_markdown}</ReactMarkdown>
                  </div>
                </Card>
              </motion.div>
            )}
          </AnimatePresence>

          {report?.status === "completed" && report.sections && (
            <div className="space-y-2">
              <p className="flex items-center gap-1.5 px-1 text-xs font-medium uppercase tracking-wide text-muted">
                <ClipboardList className="h-3.5 w-3.5" /> Analyst working notes
              </p>
              {report.sections.map((section) => (
                <AgentNoteCard key={section.name} section={section} />
              ))}
            </div>
          )}

          {!report && (
            <EmptyState
              icon={<Sparkles className="h-5 w-5" />}
              title="No research yet"
              description="Run research on a symbol above, or open a past report from the list."
            />
          )}
        </div>

        <Card className="h-fit p-4">
          <h2 className="mb-3 text-sm font-medium text-foreground">Past reports</h2>
          <div className="space-y-1">
            {history.length === 0 && <p className="text-xs text-muted">No reports yet.</p>}
            {history.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => openReport(item.id)}
                className={cn(
                  "flex w-full items-center justify-between rounded-lg px-2.5 py-2 text-left text-xs transition-colors hover:bg-surface-hover",
                  report?.id === item.id && "bg-surface-hover"
                )}
              >
                <span className="min-w-0">
                  <span className="font-medium text-foreground">
                    {item.symbol}
                    <span className="ml-1.5 text-[10px] uppercase text-muted">{item.asset_type}</span>
                  </span>
                  {item.status === "completed" && (
                    <span className="block text-[10px] text-muted">{formatCost(item.estimated_cost_usd)}</span>
                  )}
                </span>
                <Badge
                  variant={
                    item.status === "completed" ? "positive" : item.status === "failed" ? "negative" : "warning"
                  }
                >
                  {item.status}
                </Badge>
              </button>
            ))}
          </div>
        </Card>
      </div>
    </motion.div>
  );
}
