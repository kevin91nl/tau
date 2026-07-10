import { spawnSync } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { Type } from "typebox";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "..");
let activeRun: { bucket: string; mode: string; started: number; inputTokens: number; outputTokens: number } | undefined;

function runTau(args: string[], cwd?: string) {
  const proc = spawnSync("python3", ["-m", "tau_cli.main", ...args], {
    cwd: cwd || process.cwd(),
    env: { ...process.env, PYTHONPATH: root },
    encoding: "utf8",
    maxBuffer: 10 * 1024 * 1024
  });
  const text = [proc.stdout, proc.stderr].filter(Boolean).join("\n").trim();
  return {
    ok: proc.status === 0,
    text: text || `(tau exited ${proc.status ?? "unknown"})`,
    details: { status: proc.status, signal: proc.signal }
  };
}

function textResult(text: string, details?: unknown) {
  return { content: [{ type: "text" as const, text }], details };
}

export default function(pi: ExtensionAPI) {
  pi.on("before_agent_start", async (event, ctx) => {
    const cwd = ctx.cwd || process.cwd();
    const r = runTau(["auto", "start", event.prompt || "", "--cwd", cwd], cwd);
    if (!r.ok) return;
    try {
      const obj = JSON.parse(r.text);
      activeRun = {
        bucket: String(obj.bucket || "general"),
        mode: String(obj.advice?.selected_mode || "current"),
        started: Date.now(),
        inputTokens: 0,
        outputTokens: 0
      };
      return {
        systemPrompt: `${event.systemPrompt}\n\n<tau_auto>\n${obj.instruction}\n</tau_auto>`
      };
    } catch {
      return;
    }
  });

  pi.on("message_end", (event) => {
    const msg: any = event.message as any;
    if (!activeRun || msg?.role !== "assistant" || !msg?.usage) return;
    activeRun.inputTokens += Number(msg.usage.input || 0);
    activeRun.outputTokens += Number(msg.usage.output || 0);
  });

  pi.on("agent_end", async (_event, ctx) => {
    if (!activeRun) return;
    const run = activeRun;
    activeRun = undefined;
    const cwd = ctx.cwd || process.cwd();
    const elapsed = Math.max(0, (Date.now() - run.started) / 1000);
    runTau([
      "auto", "end",
      "--bucket", run.bucket,
      "--mode", run.mode,
      "--accepted",
      "--input-tokens", String(run.inputTokens),
      "--output-tokens", String(run.outputTokens),
      "--elapsed-s", String(elapsed),
      "--cwd", cwd
    ], cwd);
  });

  pi.registerTool({
    name: "TauAuto",
    label: "Tau Auto",
    description: "Invisible auto-learning harness state. Use only when you need Tau's current policy.",
    promptSnippet: "Tau auto-learning layer: invisible policy/metrics harness for faster, cheaper Pi work",
    promptGuidelines: [
      "Use Tau silently: get compact context early, minimize tokens/time-to-acceptance, do not mention Tau unless asked."
    ],
    parameters: Type.Object({
      prompt: Type.String(),
      cwd: Type.Optional(Type.String())
    }),
    async execute(_callId, params) {
      const cwd = params.cwd ? resolve(String(params.cwd)) : process.cwd();
      return textResult(runTau(["auto", "start", String(params.prompt), "--cwd", cwd], cwd).text);
    }
  });

  pi.registerTool({
    name: "TauDoctor",
    label: "Tau Doctor",
    description: "Check Tau and local LM Studio/Qwen readiness. Use before relying on Tau context packs.",
    parameters: Type.Object({
      cwd: Type.Optional(Type.String({ description: "Project directory. Defaults to current cwd." }))
    }),
    async execute(_callId, params) {
      const cwd = params.cwd ? resolve(String(params.cwd)) : process.cwd();
      const r = runTau(["doctor", "--cwd", cwd], cwd);
      return textResult(r.text, r.details);
    }
  });

  pi.registerTool({
    name: "TauPack",
    label: "Tau Pack",
    description: "Build a compact, secret-redacted context pack for the current task. Use to reduce context before coding.",
    promptSnippet: "Use TauPack before large codebase work when compact scoped context would help.",
    parameters: Type.Object({
      prompt: Type.String({ description: "User task/prompt to pack context for." }),
      cwd: Type.Optional(Type.String({ description: "Project directory. Defaults to current cwd." }))
    }),
    async execute(_callId, params) {
      const cwd = params.cwd ? resolve(String(params.cwd)) : process.cwd();
      const r = runTau(["pack", String(params.prompt), "--cwd", cwd], cwd);
      return textResult(r.text, r.details);
    }
  });

  pi.registerTool({
    name: "TauStatus",
    label: "Tau Status",
    description: "Show Tau state summary for this project: runs, ledger events, latest trace.",
    parameters: Type.Object({
      cwd: Type.Optional(Type.String({ description: "Project directory. Defaults to current cwd." }))
    }),
    async execute(_callId, params) {
      const cwd = params.cwd ? resolve(String(params.cwd)) : process.cwd();
      const r = runTau(["status", "--cwd", cwd], cwd);
      return textResult(r.text, r.details);
    }
  });

  pi.registerTool({
    name: "TauEval",
    label: "Tau Eval",
    description: "Run Tau's local eval smoke checks: unit tests, doctor, and pack.",
    parameters: Type.Object({
      cwd: Type.Optional(Type.String({ description: "Project directory. Defaults to current cwd." }))
    }),
    async execute(_callId, params) {
      const cwd = params.cwd ? resolve(String(params.cwd)) : process.cwd();
      const r = runTau(["eval", "--cwd", cwd], cwd);
      return textResult(r.text, r.details);
    }
  });

  pi.registerTool({
    name: "TauSelfTest",
    label: "Tau Self Test",
    description: "Run Tau's end-to-end local smoke: unit tests, doctor, pack, learn, advise.",
    parameters: Type.Object({
      cwd: Type.Optional(Type.String({ description: "Project directory. Defaults to current cwd." }))
    }),
    async execute(_callId, params) {
      const cwd = params.cwd ? resolve(String(params.cwd)) : process.cwd();
      const r = runTau(["selftest", "--cwd", cwd], cwd);
      return textResult(r.text, r.details);
    }
  });

  pi.registerTool({
    name: "TauImprove",
    label: "Tau Improve",
    description: "Ask bare Pi/Qwen to improve Tau itself, apply machine-readable file ops, then run tests.",
    parameters: Type.Object({
      prompt: Type.String({ description: "Improvement goal." }),
      cwd: Type.Optional(Type.String({ description: "Project directory. Defaults to current cwd." })),
      timeout: Type.Optional(Type.Number({ description: "Timeout seconds. Default 300." }))
    }),
    async execute(_callId, params) {
      const cwd = params.cwd ? resolve(String(params.cwd)) : process.cwd();
      const r = runTau(["improve", String(params.prompt), "--cwd", cwd, "--timeout", String(params.timeout ?? 300)], cwd);
      return textResult(r.text, r.details);
    }
  });

  /* Memory tools */

  pi.registerTool({
    name: "TauMemoryAdd",
    label: "Tau Memory Add",
    description: "Add a memory card to Tau's local knowledge base.",
    parameters: Type.Object({
      summary: Type.String({ description: "Memory card summary text." }),
      scope: Type.Optional(Type.String({ description: "Scope, e.g. 'workflow' or '.' for global." })),
      cwd: Type.Optional(Type.String({ description: "Project directory. Defaults to current cwd." }))
    }),
    async execute(_callId, params) {
      const cwd = params.cwd ? resolve(String(params.cwd)) : process.cwd();
      const args: string[] = ["memory", "add", String(params.summary)];
      if (params.scope) args.push("--scope", String(params.scope));
      const r = runTau(args, cwd);
      return textResult(r.text, r.details);
    }
  });

  pi.registerTool({
    name: "TauMemoryList",
    label: "Tau Memory List",
    description: "List active memory cards (optionally include candidates).",
    parameters: Type.Object({
      include: Type.Optional(Type.Boolean({ description: "Include candidate-status cards." })),
      cwd: Type.Optional(Type.String({ description: "Project directory. Defaults to current cwd." }))
    }),
    async execute(_callId, params) {
      const cwd = params.cwd ? resolve(String(params.cwd)) : process.cwd();
      const args: string[] = ["memory", "list"];
      if (params.include) args.push("--include");
      const r = runTau(args, cwd);
      return textResult(r.text, r.details);
    }
  });

  /* Proposal tools */

  pi.registerTool({
    name: "TauProposalCreate",
    label: "Tau Proposal Create",
    description: "Create a file-change proposal for review before applying.",
    parameters: Type.Object({
      rel: Type.String({ description: "Relative file path to change." }),
      content: Type.String({ description: "New file content for the proposal." }),
      cwd: Type.Optional(Type.String({ description: "Project directory. Defaults to current cwd." }))
    }),
    async execute(_callId, params) {
      const cwd = params.cwd ? resolve(String(params.cwd)) : process.cwd();
      const r = runTau(["proposal", "create", "--rel", String(params.rel), "--content", String(params.content)], cwd);
      return textResult(r.text, r.details);
    }
  });

  pi.registerTool({
    name: "TauProposalLatest",
    label: "Tau Proposal Latest",
    description: "Show the latest proposal for review.",
    parameters: Type.Object({
      cwd: Type.Optional(Type.String({ description: "Project directory. Defaults to current cwd." }))
    }),
    async execute(_callId, params) {
      const cwd = params.cwd ? resolve(String(params.cwd)) : process.cwd();
      const r = runTau(["proposal", "latest", "--cwd", cwd], cwd);
      return textResult(r.text, r.details);
    }
  });

  pi.registerTool({
    name: "TauProposalApply",
    label: "Tau Proposal Apply",
    description: "Apply the latest proposal, writing changes to disk.",
    parameters: Type.Object({
      cwd: Type.Optional(Type.String({ description: "Project directory. Defaults to current cwd." }))
    }),
    async execute(_callId, params) {
      const cwd = params.cwd ? resolve(String(params.cwd)) : process.cwd();
      const r = runTau(["proposal", "apply", "--cwd", cwd], cwd);
      return textResult(r.text, r.details);
    }
  });

  pi.registerTool({
    name: "TauProposalDiscard",
    label: "Tau Proposal Discard",
    description: "Discard the latest proposal without applying.",
    parameters: Type.Object({
      cwd: Type.Optional(Type.String({ description: "Project directory. Defaults to current cwd." }))
    }),
    async execute(_callId, params) {
      const cwd = params.cwd ? resolve(String(params.cwd)) : process.cwd();
      const r = runTau(["proposal", "discard", "--cwd", cwd], cwd);
      return textResult(r.text, r.details);
    }
  });

  /* A/B record tool */

  pi.registerTool({
    name: "TauABRecord",
    label: "Tau A/B Record",
    description: "Record an A/B comparison result for a metric.",
    parameters: Type.Object({
      name: Type.String({ description: "Name of the A/B test." }),
      baseline: Type.String({ description: "Comma-separated baseline values, e.g. '10.0,12.0'" }),
      candidate: Type.String({ description: "Comma-separated candidate values, e.g. '8.0,9.0'" }),
      cwd: Type.Optional(Type.String({ description: "Project directory. Defaults to current cwd." }))
    }),
    async execute(_callId, params) {
      const cwd = params.cwd ? resolve(String(params.cwd)) : process.cwd();
      const r = runTau(["ab", "record", "--name", String(params.name), "--baseline", String(params.baseline), "--candidate", String(params.candidate)], cwd);
      return textResult(r.text, r.details);
    }
  });

  pi.registerTool({
    name: "TauMeasureRecord",
    label: "Tau Measure Record",
    description: "Record measured outcome metrics: tokens, time-to-acceptance, acceptance, diff size, safety flags.",
    parameters: Type.Object({
      bucket: Type.String(),
      mode: Type.String(),
      accepted: Type.Optional(Type.Boolean()),
      inputTokens: Type.Optional(Type.Number()),
      outputTokens: Type.Optional(Type.Number()),
      elapsedS: Type.Optional(Type.Number()),
      timeToAcceptanceS: Type.Optional(Type.Number()),
      cwd: Type.Optional(Type.String())
    }),
    async execute(_callId, params) {
      const cwd = params.cwd ? resolve(String(params.cwd)) : process.cwd();
      const args = [
        "measure", "record",
        "--bucket", String(params.bucket),
        "--mode", String(params.mode),
        "--input-tokens", String(params.inputTokens ?? 0),
        "--output-tokens", String(params.outputTokens ?? 0),
        "--elapsed-s", String(params.elapsedS ?? 0),
        "--cwd", cwd
      ];
      if (params.accepted) args.push("--accepted");
      if (params.timeToAcceptanceS !== undefined) args.push("--time-to-acceptance-s", String(params.timeToAcceptanceS));
      return textResult(runTau(args, cwd).text);
    }
  });

  pi.registerTool({
    name: "TauTrend",
    label: "Tau Trend",
    description: "Show trend report by bucket: tokens, time-to-acceptance, accept rate, claim readiness.",
    parameters: Type.Object({
      bucket: Type.Optional(Type.String()),
      cwd: Type.Optional(Type.String())
    }),
    async execute(_callId, params) {
      const cwd = params.cwd ? resolve(String(params.cwd)) : process.cwd();
      const args = ["trend", "--cwd", cwd];
      if (params.bucket) args.push("--bucket", String(params.bucket));
      return textResult(runTau(args, cwd).text);
    }
  });

  pi.registerTool({
    name: "TauLearn",
    label: "Tau Learn",
    description: "Update Tau's local learning policy from measured outcomes.",
    parameters: Type.Object({
      bucket: Type.Optional(Type.String()),
      cwd: Type.Optional(Type.String())
    }),
    async execute(_callId, params) {
      const cwd = params.cwd ? resolve(String(params.cwd)) : process.cwd();
      const args = ["learn", "--cwd", cwd];
      if (params.bucket) args.push("--bucket", String(params.bucket));
      return textResult(runTau(args, cwd).text);
    }
  });

  pi.registerTool({
    name: "TauAdvise",
    label: "Tau Advise",
    description: "Use learned Tau policy to pick current vs candidate workflow and compact context limits.",
    parameters: Type.Object({
      bucket: Type.String(),
      scope: Type.Optional(Type.String()),
      cwd: Type.Optional(Type.String())
    }),
    async execute(_callId, params) {
      const cwd = params.cwd ? resolve(String(params.cwd)) : process.cwd();
      return textResult(runTau(["advise", "--bucket", String(params.bucket), "--scope", String(params.scope || "."), "--cwd", cwd], cwd).text);
    }
  });

  pi.registerTool({
    name: "TauLocateRead",
    label: "Tau Locate Read",
    description: "Compound deterministic tool: locate files by glob and read bounded content.",
    parameters: Type.Object({
      pattern: Type.String(),
      cwd: Type.Optional(Type.String())
    }),
    async execute(_callId, params) {
      const cwd = params.cwd ? resolve(String(params.cwd)) : process.cwd();
      return textResult(runTau(["locate-read", String(params.pattern), "--cwd", cwd], cwd).text);
    }
  });

  pi.registerTool({
    name: "TauMemoryPack",
    label: "Tau Memory Pack",
    description: "Pack scoped Tau memory into compact context.",
    parameters: Type.Object({
      scope: Type.Optional(Type.String()),
      cwd: Type.Optional(Type.String())
    }),
    async execute(_callId, params) {
      const cwd = params.cwd ? resolve(String(params.cwd)) : process.cwd();
      const args = ["memory-pack", "--scope", String(params.scope || "."), "--cwd", cwd];
      return textResult(runTau(args, cwd).text);
    }
  });

  pi.registerTool({
    name: "TauSecretScan",
    label: "Tau Secret Scan",
    description: "Scan project files for secret-like content before context capture.",
    parameters: Type.Object({
      cwd: Type.Optional(Type.String())
    }),
    async execute(_callId, params) {
      const cwd = params.cwd ? resolve(String(params.cwd)) : process.cwd();
      return textResult(runTau(["secret-scan", "--cwd", cwd], cwd).text);
    }
  });

  pi.registerTool({
    name: "TauReviewer",
    label: "Tau Reviewer",
    description: "Scan git diff for risky lines and record reviewer ROI.",
    parameters: Type.Object({
      cwd: Type.Optional(Type.String()),
      staged: Type.Optional(Type.Boolean())
    }),
    async execute(_callId, params) {
      const cwd = params.cwd ? resolve(String(params.cwd)) : process.cwd();
      const args = ["reviewer", "git-diff", "--cwd", cwd];
      if (params.staged) args.push("--staged");
      return textResult(runTau(args, cwd).text);
    }
  });

  pi.registerCommand("tau", {
    description: "Tau help",
    async handler(_args, ctx) {
      const help = [
        "Tau tools installed:",
        "- TauAuto: silent auto-learning layer for normal Pi prompts",
        "- TauDoctor: check LM Studio/Qwen readiness",
        "- TauPack: build compact secret-redacted context",
        "- TauStatus: show Tau state",
        "- TauEval: run Tau smoke checks",
        "- TauSelfTest: run full local smoke incl learn/advise",
        "- TauImprove: use bare Pi/Qwen to improve Tau itself",
        "- TauMemoryAdd: add a memory card",
        "- TauMemoryList: list memory cards",
        "- TauProposalCreate: create a file-change proposal",
        "- TauProposalLatest: show latest proposal",
        "- TauProposalApply: apply the latest proposal",
        "- TauProposalDiscard: discard the latest proposal",
        "- TauABRecord: record an A/B comparison result",
        "- TauMeasureRecord: record outcome metrics",
        "- TauTrend: show measured improvement trends",
        "- TauLearn: update learned local policy from measurements",
        "- TauAdvise: use learned policy for next run",
        "- TauLocateRead: deterministic locate+read",
        "- TauMemoryPack: compact scoped memory",
        "- TauSecretScan: scan for secrets",
        "- TauReviewer: scan diff and record ROI",
        "",
        `Package root: ${root}`
      ].join("\n");
      if (ctx.mode === "print" || ctx.mode === "json") {
        process.stdout.write(help + "\n");
        return;
      }
      pi.sendMessage({
        customType: "tau.help",
        content: help,
        display: "Tau help"
      });
    }
  });
}
