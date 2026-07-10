import assert from "node:assert/strict";
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { spawnSync } from "node:child_process";

const root = resolve(import.meta.dirname, "..");
const extension = join(root, "pi-extension", "index.js");
const dir = mkdtempSync(join(tmpdir(), "tau-local-eval-"));
const sessionDir = join(dir, "sessions");
const pi = process.env.TAU_PI_BIN || "pi";
const provider = process.env.TAU_EVAL_PROVIDER || "lmstudio";
const model = process.env.TAU_EVAL_MODEL || "qwen3.6-35b-a3b-ud-mlx";
const timeout = Number(process.env.TAU_EVAL_TIMEOUT_MS || 120000);

function run(sessionId, prompt, tools = "") {
  const args = [
    "--approve",
    "--no-extensions",
    "--extension", extension,
    "--session-dir", sessionDir,
    "--session-id", sessionId,
    "--provider", provider,
    "--model", model,
  ];
  if (tools) args.push("--tools", tools);
  else args.push("--no-tools");
  args.push("-p", prompt);
  const result = spawnSync(pi, args, { cwd: dir, encoding: "utf8", timeout, env: process.env });
  if (result.error) throw result.error;
  assert.equal(result.status, 0, result.stderr || result.stdout);
  return result.stdout.trim();
}

function rows(file) {
  const path = join(dir, ".tau", file);
  if (!existsSync(path)) return [];
  return readFileSync(path, "utf8").trim().split("\n").filter(Boolean).map(JSON.parse);
}

try {
  writeFileSync(join(dir, "README.md"), "# Tau local eval\n");

  const vague = run("vague", "Give the platform some love before demo day.");
  assert.match(vague, /\?|clarif|what|which|target/i, vague);
  assert.equal(rows("session.jsonl").at(-1).ambiguous, true);

  const concrete = run("concrete", "Target: README.md. Acceptance: add one sentence. Without tools, state whether this is actionable.");
  assert.match(concrete, /actionable|ready|can/i, concrete);
  assert.equal(rows("session.jsonl").at(-1).ambiguous, false);

  run("failure", "Run false once with bash. Do not repeat it.", "bash");
  const failure = rows("session.jsonl").at(-1);
  assert.deepEqual(failure.errors, ["bash"]);
  const followUp = run("failure", "Without tools, should the prior bash command be repeated?");
  assert.match(followUp, /^no\b/i, followUp);

  console.log(JSON.stringify({
    status: "ok",
    cases: ["vague-clarification", "concrete-actionability", "live-failure-learning"],
    runs: rows("runs.jsonl").length,
  }));
} finally {
  rmSync(dir, { recursive: true, force: true });
}
