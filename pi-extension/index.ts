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

  pi.registerCommand("tau", {
    description: "Tau help",
    async run() {
      return textResult([
        "Tau tools installed:",
        "- TauDoctor: check LM Studio/Qwen readiness",
        "- TauPack: build compact secret-redacted context",
        "- TauStatus: show Tau state",
        "- TauEval: run Tau smoke checks",
        "",
        `Package root: ${root}`
      ].join("\n"));
    }
  });
}
