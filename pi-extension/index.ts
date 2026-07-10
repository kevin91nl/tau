import { spawnSync } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { Type } from "typebox";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "..");

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

  pi.registerCommand("tau", {
    description: "Tau help",
    async run() {
      return textResult([
        "Tau tools installed:",
        "- TauDoctor: check LM Studio/Qwen readiness",
        "- TauPack: build compact secret-redacted context",
        "- TauStatus: show Tau state",
        "- TauEval: run Tau smoke checks",
        "- TauMemoryAdd: add a memory card",
        "- TauMemoryList: list memory cards",
        "- TauProposalCreate: create a file-change proposal",
        "- TauProposalLatest: show latest proposal",
        "- TauProposalApply: apply the latest proposal",
        "- TauProposalDiscard: discard the latest proposal",
        "- TauABRecord: record an A/B comparison result",
        "",
        `Package root: ${root}`
      ].join("\n"));
    }
  });
}
