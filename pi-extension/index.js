import { mkdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { join } from "node:path";

const TAU_DIR = ".tau";
const RUNS = "runs.jsonl";
const MEMORIES = "memory.jsonl";

function schema(properties = {}) {
  return { type: "object", properties, additionalProperties: false };
}

function optionalString() {
  return { type: "string" };
}

function runKey(ctx) {
  const session = ctx?.sessionManager?.getSessionId?.() || "session";
  const cwd = ctx?.cwd || process.cwd();
  return `${session}:${cwd}`;
}

function tauDir(cwd) {
  return join(cwd, TAU_DIR);
}

function appendJsonl(cwd, file, row) {
  mkdirSync(tauDir(cwd), { recursive: true });
  writeFileSync(join(tauDir(cwd), file), `${JSON.stringify(row)}\n`, { flag: "a" });
}

function readJsonl(cwd, file) {
  const path = join(tauDir(cwd), file);
  if (!existsSync(path)) return [];
  return readFileSync(path, "utf8")
    .split("\n")
    .filter(Boolean)
    .map((line) => JSON.parse(line));
}

function bucketFromPrompt(prompt) {
  const words = String(prompt || "")
    .toLowerCase()
    .split(/\W+/)
    .filter((word) => word.length > 2)
    .slice(0, 3);
  return words.join("-") || "general";
}

function median(values) {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.floor(sorted.length / 2)];
}

function trend(cwd, bucket) {
  const rows = readJsonl(cwd, RUNS).filter((row) => !bucket || row.bucket === bucket);
  const groups = {};
  for (const row of rows) {
    groups[row.bucket] ??= {};
    groups[row.bucket][row.mode] ??= { runs: 0, tokens: [], elapsed: [], tools: [] };
    groups[row.bucket][row.mode].runs += 1;
    groups[row.bucket][row.mode].tokens.push(row.totalTokens || 0);
    groups[row.bucket][row.mode].elapsed.push(row.elapsedMs || 0);
    groups[row.bucket][row.mode].tools.push(row.tools || 0);
  }
  return Object.fromEntries(Object.entries(groups).map(([bucketName, modes]) => {
    const modeStats = Object.fromEntries(Object.entries(modes).map(([mode, value]) => [mode, {
      runs: value.runs,
      medianTokens: median(value.tokens),
      medianElapsedMs: median(value.elapsed),
      medianTools: median(value.tools),
    }]));
    return [bucketName, { modes: modeStats, selectedMode: modeFor(cwd, bucketName) }];
  }));
}

function modeFor(cwd, bucket) {
  const rows = readJsonl(cwd, RUNS).filter((row) => row.bucket === bucket);
  const current = rows.filter((row) => row.mode === "current");
  const candidate = rows.filter((row) => row.mode === "candidate");
  if (current.length >= 1 && candidate.length < 3) return "candidate";
  if (current.length >= 1 && candidate.length >= 3) {
    const currentTokens = median(current.map((row) => row.totalTokens || 0)) ?? Infinity;
    const candidateTokens = median(candidate.map((row) => row.totalTokens || 0)) ?? Infinity;
    const currentElapsed = median(current.map((row) => row.elapsedMs || 0)) ?? Infinity;
    const candidateElapsed = median(candidate.map((row) => row.elapsedMs || 0)) ?? Infinity;
    return candidateTokens <= currentTokens && candidateElapsed <= currentElapsed ? "candidate" : "current";
  }
  return "current";
}

function instruction(cwd, prompt) {
  const bucket = bucketFromPrompt(prompt);
  const mode = modeFor(cwd, bucket);
  const maxFiles = mode === "candidate" ? 8 : 16;
  const simple = isSimplePrompt(prompt);
  return {
    bucket,
    mode,
    simple,
    text: [
      "Tau is active silently.",
      `bucket=${bucket}; mode=${mode}; max_files=${maxFiles}.`,
      simple && mode === "candidate" ? "Answer directly without tools." : "",
      "Keep context small. Read only files needed. Prefer targeted grep/read over broad scans.",
      "Do not mention Tau unless the user asks.",
    ].filter(Boolean).join(" "),
  };
}

function isSimplePrompt(prompt) {
  const text = String(prompt || "").toLowerCase();
  if (text.includes("reply exactly")) return true;
  const coding = /\b(fix|bug|test|repo|file|code|edit|implement|debug|build|run)\b/.test(text);
  return text.length < 120 && !coding;
}

function status(cwd) {
  const runs = readJsonl(cwd, RUNS);
  const memories = readJsonl(cwd, MEMORIES);
  const last = runs[runs.length - 1];
  return {
    cwd,
    runs: runs.length,
    memories: memories.length,
    lastBucket: last?.bucket || null,
    lastMode: last?.mode || null,
  };
}

function textResult(text, details) {
  return { content: [{ type: "text", text }], details };
}

const activeRuns = new Map();
let rememberedTools;

export default function tau(pi) {
  pi.on("before_agent_start", (event, ctx) => {
    const cwd = ctx.cwd || process.cwd();
    if (!rememberedTools && typeof pi.getActiveTools === "function") {
      rememberedTools = pi.getActiveTools();
    }
    const next = instruction(cwd, event.prompt || "");
    activeRuns.set(runKey(ctx), {
      cwd,
      bucket: next.bucket,
      mode: next.mode,
      startedAt: Date.now(),
      inputTokens: 0,
      outputTokens: 0,
      tools: 0,
    });
    if (next.simple && next.mode === "candidate" && typeof pi.setActiveTools === "function") {
      pi.setActiveTools([]);
    } else if (rememberedTools && typeof pi.setActiveTools === "function") {
      pi.setActiveTools(rememberedTools);
    }
    return { systemPrompt: `${event.systemPrompt}\n\n<tau>\n${next.text}\n</tau>` };
  });

  pi.on("message_end", (event, ctx) => {
    const msg = event.message;
    const active = activeRuns.get(runKey(ctx));
    if (!active || msg?.role !== "assistant" || !msg?.usage) return;
    active.inputTokens += Number(msg.usage.input || 0);
    active.outputTokens += Number(msg.usage.output || 0);
  });

  pi.on("tool_result", (_event, ctx) => {
    const active = activeRuns.get(runKey(ctx));
    if (active) active.tools += 1;
  });

  pi.on("agent_end", (_event, ctx) => {
    const key = runKey(ctx);
    const active = activeRuns.get(key);
    if (!active) return;
    activeRuns.delete(key);
    const run = {
      ts: new Date().toISOString(),
      bucket: active.bucket,
      mode: active.mode,
      elapsedMs: Date.now() - active.startedAt,
      inputTokens: active.inputTokens,
      outputTokens: active.outputTokens,
      totalTokens: active.inputTokens + active.outputTokens,
      tools: active.tools,
    };
    appendJsonl(active.cwd, RUNS, run);
  });

  pi.registerTool({
    name: "TauStatus",
    label: "Tau Status",
    description: "Show Tau local learning status for this project.",
    parameters: schema({ cwd: optionalString() }),
    async execute(_id, params, _signal, _update, ctx) {
      const cwd = params.cwd || ctx.cwd || process.cwd();
      return textResult(JSON.stringify(status(cwd), null, 2));
    },
  });

  pi.registerTool({
    name: "TauTrend",
    label: "Tau Trend",
    description: "Show Tau token/time trends by task bucket.",
    parameters: schema({ bucket: optionalString(), cwd: optionalString() }),
    async execute(_id, params, _signal, _update, ctx) {
      const cwd = params.cwd || ctx.cwd || process.cwd();
      return textResult(JSON.stringify(trend(cwd, params.bucket), null, 2));
    },
  });

  pi.registerTool({
    name: "TauMemoryAdd",
    label: "Tau Memory Add",
    description: "Add one short project memory. Keep it factual and actionable.",
    parameters: schema({ text: { type: "string" }, cwd: optionalString() }),
    async execute(_id, params, _signal, _update, ctx) {
      const cwd = params.cwd || ctx.cwd || process.cwd();
      const row = { ts: new Date().toISOString(), text: String(params.text || "").slice(0, 500) };
      appendJsonl(cwd, MEMORIES, row);
      return textResult(JSON.stringify(row, null, 2));
    },
  });

  pi.registerTool({
    name: "TauMemoryList",
    label: "Tau Memory List",
    description: "List short project memories.",
    parameters: schema({ cwd: optionalString() }),
    async execute(_id, params, _signal, _update, ctx) {
      const cwd = params.cwd || ctx.cwd || process.cwd();
      return textResult(JSON.stringify(readJsonl(cwd, MEMORIES), null, 2));
    },
  });

  pi.registerCommand("tau", {
    description: "Tau status",
    async handler(_args, ctx) {
      const cwd = ctx.cwd || process.cwd();
      const body = [
        "Tau minimal auto-learning layer",
        `runs: ${status(cwd).runs}`,
        `memories: ${status(cwd).memories}`,
        "tools: TauStatus, TauTrend, TauMemoryAdd, TauMemoryList",
      ].join("\n");
      if (ctx.mode === "print" || ctx.mode === "json") {
        process.stdout.write(`${body}\n`);
        return;
      }
      pi.sendMessage({ customType: "tau.status", content: body, display: "Tau" });
    },
  });
}

export { bucketFromPrompt, instruction, isSimplePrompt, median, modeFor, runKey, status, tauDir, trend };
