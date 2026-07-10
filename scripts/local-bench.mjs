import assert from "node:assert/strict";
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { spawn } from "node:child_process";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { bucketFromPrompt, modeFor } from "../pi-extension/index.js";

const root = resolve(import.meta.dirname, "..");
const extension = join(root, "pi-extension", "index.js");
const dir = mkdtempSync(join(tmpdir(), "tau-local-bench-"));
const sessionDir = join(dir, "sessions");
const pi = process.env.TAU_PI_BIN || "pi";
const provider = process.env.TAU_EVAL_PROVIDER || "lmstudio";
const model = process.env.TAU_EVAL_MODEL || "qwen3.6-35b-a3b-ud-mlx";
const timeout = Number(process.env.TAU_EVAL_TIMEOUT_MS || 180000);
const runs = Number(process.env.TAU_BENCH_RUNS || 4);
const prompt = "Target: task.js. Acceptance: replace exactly `const status = \"draft\";` with `const status = \"ready\";`, then run npm test. Do not edit any other file.";
const env = { ...process.env, TAU_HOME: process.env.TAU_HOME || join(dir, "tau-home") };

function median(values) {
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

function rows() {
  const path = join(dir, ".tau", "runs.jsonl");
  if (!existsSync(path)) return [];
  return readFileSync(path, "utf8").trim().split("\n").filter(Boolean).map(JSON.parse);
}

function run(index) {
  return new Promise((resolveRun, rejectRun) => {
    const child = spawn(pi, [
      "--mode", "rpc", "--approve", "--no-extensions", "--extension", extension,
      "--session-dir", sessionDir, "--session-id", `bench-${index}`,
      "--provider", provider, "--model", model, "--tools", "read,bash,edit",
    ], { cwd: dir, env, stdio: ["pipe", "pipe", "pipe"] });
    let output = "";
    let stderr = "";
    let settled = false;
    const timer = setTimeout(() => finish(new Error(`RPC benchmark timed out after ${timeout}ms. ${stderr}`)), timeout);
    function finish(error) {
      clearTimeout(timer);
      child.kill("SIGTERM");
      if (error) rejectRun(error);
      else resolveRun();
    }
    child.once("error", finish);
    child.once("exit", (code, signal) => {
      if (!settled) finish(new Error(`RPC benchmark exited before settle: code=${code} signal=${signal}. ${stderr}`));
    });
    child.stderr.on("data", (chunk) => { stderr += chunk; });
    child.stdout.on("data", (chunk) => {
      output += chunk;
      let newline;
      while ((newline = output.indexOf("\n")) >= 0) {
        const line = output.slice(0, newline);
        output = output.slice(newline + 1);
        try {
          if (JSON.parse(line).type === "agent_settled") {
            settled = true;
            finish();
          }
        } catch {
          // Ignore non-JSON diagnostics from a future Pi version.
        }
      }
    });
    child.stdin.write(`${JSON.stringify({ id: "bench", type: "prompt", message: prompt })}\n`);
  });
}

try {
  assert.ok(Number.isInteger(runs) && runs >= 2, "TAU_BENCH_RUNS must be at least 2");
  writeFileSync(join(dir, "task.test.js"), 'import assert from "node:assert/strict";\nimport { readFileSync } from "node:fs";\nassert.match(readFileSync(new URL("./task.js", import.meta.url), "utf8"), /const status = "ready";/);\n');
  writeFileSync(join(dir, "package.json"), '{"type":"module","scripts":{"test":"node task.test.js"}}\n');
  for (let index = 0; index < runs; index += 1) {
    writeFileSync(join(dir, "task.js"), 'const status = "draft";\n');
    await run(index);
    assert.equal(readFileSync(join(dir, "task.js"), "utf8"), 'const status = "ready";\n');
  }
  const byMode = Object.fromEntries(["current", "candidate"].map((mode) => {
    const matches = rows().filter((row) => row.mode === mode);
    return [mode, {
      runs: matches.length,
      medianTokens: matches.length ? median(matches.map((row) => row.totalTokens)) : null,
      medianElapsedMs: matches.length ? median(matches.map((row) => row.elapsedMs)) : null,
      medianTools: matches.length ? median(matches.map((row) => row.tools)) : null,
    }];
  }));
  // A candidate that is not Pareto-better must revert to current. Repeated
  // current runs are therefore expected and are part of the measurement.
  assert.ok(byMode.current.runs >= 1);
  assert.ok(byMode.candidate.runs >= 1);
  const report = {
    status: "ok",
    acceptance: "all sealed edits passed",
    modes: byMode,
    selectedMode: modeFor(dir, bucketFromPrompt(prompt)),
  };
  if (process.env.TAU_BENCH_REPORT) {
    writeFileSync(process.env.TAU_BENCH_REPORT, `${JSON.stringify(report, null, 2)}\n`);
  }
  console.log(JSON.stringify(report));
} finally {
  rmSync(dir, { recursive: true, force: true });
}
