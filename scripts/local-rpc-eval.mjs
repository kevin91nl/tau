import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
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

function run(prompt, tools = "") {
  return new Promise((resolveRun, rejectRun) => {
    const args = [
      "--mode", "rpc", "--approve", "--no-extensions", "--extension", extension,
      "--session-dir", sessionDir, "--provider", provider, "--model", model,
    ];
    if (tools) args.push("--tools", tools);
    else args.push("--no-tools");
    const child = spawn(pi, args, { cwd: dir, env, stdio: ["pipe", "pipe", "pipe"] });
    let stdout = "";
    let stderr = "";
    let settled = false;
    const timer = setTimeout(() => finish(new Error(`RPC eval timed out after ${timeoutMs}ms. ${stderr}`)), timeoutMs);
    function finish(error) {
      clearTimeout(timer);
      child.kill("SIGTERM");
      if (error) rejectRun(error);
      else resolveRun({ stdout, stderr });
    }
    child.once("error", finish);
    child.once("exit", (code, signal) => {
      if (!settled) finish(new Error(`RPC agent exited before settle: code=${code} signal=${signal}. ${stderr}`));
    });
    child.stderr.on("data", (chunk) => { stderr += chunk; });
    child.stdout.on("data", (chunk) => {
      stdout += chunk;
      let newline;
      while ((newline = stdout.indexOf("\n")) >= 0) {
        const line = stdout.slice(0, newline);
        stdout = stdout.slice(newline + 1);
        try {
          if (JSON.parse(line).type === "agent_settled") {
            settled = true;
            finish();
          }
        } catch {
          // Pi RPC is JSONL; ignore diagnostics if a future Pi version emits any.
        }
      }
    });
    child.stdin.write(`${JSON.stringify({ id: "eval", type: "prompt", message: prompt })}\n`);
  });
}

function rows(file) {
  const path = join(dir, ".tau", file);
  if (!existsSync(path)) return [];
  return readFileSync(path, "utf8").trim().split("\n").filter(Boolean).map(JSON.parse);
}

try {
  writeFileSync(join(dir, "task.js"), 'const status = "draft";\n');
  writeFileSync(join(dir, "untouched.txt"), "keep\n");

  await run("Maak de checkout goed voor morgen zonder iets kapot te maken.");
  assert.equal(rows("session.jsonl").at(-1).ambiguous, true);

  await run(
    "Target: task.js. First read only task.js. Replace exactly `const status = \"draft\";` with `const status = \"ready\";`. Then use bash to print task.js. Do not edit any other file. Acceptance: task.js prints ready.",
    "read,bash,edit"
  );
  assert.equal(readFileSync(join(dir, "task.js"), "utf8"), 'const status = "ready";\n');
  assert.equal(readFileSync(join(dir, "untouched.txt"), "utf8"), "keep\n");
  const completed = rows("runs.jsonl").at(-1);
  assert.ok(completed.tools >= 2);
  assert.equal(completed.trainable, true);

  console.log(JSON.stringify({
    status: "ok",
    cases: ["vague-clarification", "sealed-multi-tool-edit"],
    runs: rows("runs.jsonl").length,
    sealedRun: completed,
  }));
} finally {
  rmSync(dir, { recursive: true, force: true });
}
