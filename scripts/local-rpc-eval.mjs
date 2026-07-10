import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const extension = join(root, "pi-extension", "index.js");
const dir = mkdtempSync(join(tmpdir(), "tau-rpc-eval-"));
const sessionDir = join(dir, "sessions");
const pi = process.env.TAU_PI_BIN || "pi";
const provider = process.env.TAU_EVAL_PROVIDER || "lmstudio";
const model = process.env.TAU_EVAL_MODEL || "qwen3.6-35b-a3b-ud-mlx";
const timeoutMs = Number(process.env.TAU_EVAL_TIMEOUT_MS || 180_000);
const env = { ...process.env, TAU_HOME: process.env.TAU_HOME || join(dir, "tau-home") };

function startRpc(tools) {
  const child = spawn(pi, [
    "--mode", "rpc", "--approve", "--no-extensions", "--extension", extension,
    "--session-dir", sessionDir, "--provider", provider, "--model", model,
    "--tools", tools,
  ], { cwd: dir, env, stdio: ["pipe", "pipe", "pipe"] });
  let output = "";
  let stderr = "";
  let pending;
  let rejectPending;
  function failPending(error) {
    if (!pending || !rejectPending) return;
    const reject = rejectPending;
    pending = undefined;
    rejectPending = undefined;
    reject(error);
  }
  child.once("error", (error) => failPending(error));
  child.once("exit", (code, signal) => {
    failPending(new Error(`RPC eval exited before settle: code=${code} signal=${signal}. ${stderr}`));
  });
  child.stderr.on("data", (chunk) => { stderr += chunk; });
  child.stdout.on("data", (chunk) => {
    output += chunk;
    let newline;
    while ((newline = output.indexOf("\n")) >= 0) {
      const line = output.slice(0, newline);
      output = output.slice(newline + 1);
      try {
        if (JSON.parse(line).type === "agent_settled" && pending) {
          const resolve = pending;
          pending = undefined;
          resolve();
        }
      } catch {
        // Pi RPC is JSONL; ignore diagnostics if a future Pi version emits any.
      }
    }
  });
  function prompt(message) {
    return new Promise((resolvePrompt, rejectPrompt) => {
      const settle = () => {
        clearTimeout(timer);
        resolvePrompt();
      };
      const timer = setTimeout(() => {
        if (pending === settle) {
          pending = undefined;
          rejectPending = undefined;
        }
        rejectPrompt(new Error(`RPC eval timed out after ${timeoutMs}ms. ${stderr}`));
      }, timeoutMs);
      pending = settle;
      rejectPending = rejectPrompt;
      child.stdin.write(`${JSON.stringify({ id: "eval", type: "prompt", message })}\n`);
    });
  }
  return { prompt, stop: () => child.kill("SIGTERM") };
}

function rows(file) {
  const path = join(dir, ".tau", file);
  if (!existsSync(path)) return [];
  return readFileSync(path, "utf8").trim().split("\n").filter(Boolean).map(JSON.parse);
}

try {
  writeFileSync(join(dir, "task.js"), 'const status = "draft";\n');
  writeFileSync(join(dir, "task.test.js"), 'import assert from "node:assert/strict";\nimport { readFileSync } from "node:fs";\nassert.match(readFileSync(new URL("./task.js", import.meta.url), "utf8"), /const status = "ready";/);\n');
  writeFileSync(join(dir, "package.json"), '{"type":"module","scripts":{"test":"node --test"}}\n');
  writeFileSync(join(dir, "untouched.txt"), "keep\n");

  const rpc = startRpc("read,bash,edit");
  await rpc.prompt("Maak de checkout goed voor morgen zonder iets kapot te maken.");
  assert.equal(rows("session.jsonl").at(-1).ambiguous, true);

  await rpc.prompt("Target: task.js. First read only task.js. Replace exactly `const status = \"draft\";` with `const status = \"ready\";`. Then run `npm test`. Do not edit any other file. Acceptance: npm test passes.");
  rpc.stop();
  assert.equal(readFileSync(join(dir, "task.js"), "utf8"), 'const status = "ready";\n');
  assert.equal(readFileSync(join(dir, "untouched.txt"), "utf8"), "keep\n");
  const completed = rows("runs.jsonl").at(-1);
  assert.ok(completed.tools >= 2);
  assert.equal(completed.trainable, true);
  assert.equal(rows("feedback.jsonl").at(-1).resolved, true);

  mkdirSync(join(dir, "src"), { recursive: true });
  writeFileSync(join(dir, "src", "normalize.js"), 'export function displayName(record) {\n  return record.profile?.name || "<unknown>";\n}\n');
  writeFileSync(join(dir, "src", "render.js"), 'import { displayName } from "./normalize.js";\n\nexport function renderImport(record) {\n  return { label: displayName(record) };\n}\n');
  writeFileSync(join(dir, "src", "import.test.js"), 'import assert from "node:assert/strict";\nimport test from "node:test";\nimport { renderImport } from "./render.js";\n\ntest("renders a normalized import label", () => {\n  assert.equal(renderImport({ profile: { name: " Ada " } }).label, "Ada");\n  assert.equal(renderImport({ profile: { name: "   " } }).label, "<unknown>");\n  assert.equal(renderImport({}).label, "<unknown>");\n});\n');

  const complexRpc = startRpc("read,bash,edit");
  await complexRpc.prompt("Customer import labels are wrong after a refactor. Find and fix the regression. Acceptance: preserve normalized non-empty names, render `<unknown>` for whitespace-only or missing names, public API unchanged, and `npm test` passes. Do not edit tests.");
  complexRpc.stop();
  assert.match(readFileSync(join(dir, "src", "normalize.js"), "utf8"), /\.trim\(\)/);
  const complexRun = rows("runs.jsonl").at(-1);
  assert.equal(complexRun.trainable, true);

  writeFileSync(join(dir, "src", "key.test.js"), 'import assert from "node:assert/strict";\nimport test from "node:test";\nimport { renderImport } from "./render.js";\n\ntest("adds a stable normalized import key without changing the label", () => {\n  assert.deepEqual(renderImport({ profile: { name: " Ada ", email: " ADA@Example.COM " } }), { label: "Ada", key: "ada@example.com" });\n  assert.deepEqual(renderImport({ profile: { name: " Ada " } }), { label: "Ada", key: "ada" });\n});\n');
  const featureRpc = startRpc("read,bash,edit");
  await featureRpc.prompt("Import consumers need a stable `key` now. Implement it without changing label behavior. The key must be normalized profile email if present; otherwise normalized label. Acceptance: public API stays compatible and `npm test` passes. Do not edit tests.");
  featureRpc.stop();
  assert.match(readFileSync(join(dir, "src", "render.js"), "utf8"), /key/);
  const featureRun = rows("runs.jsonl").at(-1);
  assert.equal(featureRun.trainable, true);

  console.log(JSON.stringify({
    status: "ok",
    cases: ["vague-clarification", "same-session-clarification-to-sealed-edit", "multi-file-regression", "feature-with-compatibility"],
    runs: rows("runs.jsonl").length,
    sealedRun: completed,
    complexRun,
    featureRun,
  }));
} finally {
  rmSync(dir, { recursive: true, force: true });
}
