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
const timeout = Number(process.env.TAU_EVAL_TIMEOUT_MS || 180000);
const env = { ...process.env, TAU_HOME: process.env.TAU_HOME || join(dir, "tau-home") };

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
  const result = spawnSync(pi, args, { cwd: dir, encoding: "utf8", timeout, env });
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
  writeFileSync(join(dir, "task.js"), 'const status = "draft";\n');
  writeFileSync(join(dir, "untouched.txt"), "keep\n");

  const vague = run("vague", "Give the platform some love before demo day.");
  assert.match(vague, /\?|clarif|what|which|target/i, vague);
  assert.equal(rows("session.jsonl").at(-1).ambiguous, true);
  const vagueNl = run("vague-nl", "Maak het even goed voor morgen.");
  assert.match(vagueNl, /\?|welk|wat|doel|acceptatie/i, vagueNl);
  assert.equal(rows("session.jsonl").at(-1).ambiguous, true);
  const clarified = run("vague", "Perfect. Target: README.md. Acceptance: add one sentence. Without tools, state whether this is actionable.");
  assert.match(clarified, /actionable|ready|can/i, clarified);
  const feedback = rows("feedback.jsonl").at(-1);
  assert.equal(feedback.sessionId, "vague");
  assert.equal(feedback.pattern, "ambiguous");
  assert.equal(feedback.resolved, true);
  assert.equal(feedback.sentiment, "positive");

  const concrete = run("concrete", "Target: README.md. Acceptance: add one sentence. Without tools, state whether this is actionable.");
  assert.match(concrete, /actionable|ready|can/i, concrete);
  assert.equal(rows("session.jsonl").at(-1).ambiguous, false);

  run(
    "sealed-edit",
    "Target: task.js. Acceptance: replace exactly `const status = \"draft\";` with `const status = \"ready\";`, then use bash to print task.js. Do not edit any other file.",
    "bash"
  );
  assert.equal(readFileSync(join(dir, "task.js"), "utf8"), 'const status = "ready";\n');
  assert.equal(readFileSync(join(dir, "untouched.txt"), "utf8"), "keep\n");
  assert.ok(rows("session.jsonl").at(-1).tools >= 2);

  const failureOutput = run("failure", "Run false once with bash. Do not repeat it.", "bash");
  assert.match(failureOutput, /Verification guard/, failureOutput);
  const failure = rows("session.jsonl").at(-1);
  assert.deepEqual(failure.errors, ["bash"]);
  const followUp = run("failure", "Without tools, should the prior bash command be repeated?");
  assert.match(followUp, /^no\b/i, followUp);

  const runtime = run("runtime", "Does NaN raise TypeError? Do not use tools.");
  assert.match(runtime, /Evidence guard/, runtime);

  const attempts = rows("attempts.jsonl");
  const finished = attempts.filter((row) => row.status === "finished");
  assert.equal(attempts.filter((row) => row.status === "started").length, rows("runs.jsonl").length);
  assert.equal(finished.length, rows("runs.jsonl").length);

  console.log(JSON.stringify({
    status: "ok",
    cases: ["vague-clarification", "vague-clarification-nl", "clarification-feedback", "concrete-actionability", "sealed-edit", "live-failure-learning", "runtime-evidence-guard", "attempt-journal"],
    runs: rows("runs.jsonl").length,
  }));
} finally {
  rmSync(dir, { recursive: true, force: true });
}
