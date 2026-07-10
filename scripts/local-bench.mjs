import assert from "node:assert/strict";
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const extension = join(root, "pi-extension", "index.js");
const dir = mkdtempSync(join(tmpdir(), "tau-local-bench-"));
const sessionDir = join(dir, "sessions");
const pi = process.env.TAU_PI_BIN || "pi";
const provider = process.env.TAU_EVAL_PROVIDER || "lmstudio";
const model = process.env.TAU_EVAL_MODEL || "qwen3.6-35b-a3b-ud-mlx";
const timeout = Number(process.env.TAU_EVAL_TIMEOUT_MS || 180000);
const runs = Number(process.env.TAU_BENCH_RUNS || 4);
const prompt = "Target: task.js. Acceptance: replace exactly `const status = \"draft\";` with `const status = \"ready\";`, then use bash to print task.js. Do not edit any other file.";

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
  const result = spawnSync(pi, [
    "--approve", "--no-extensions", "--extension", extension,
    "--session-dir", sessionDir, "--session-id", `bench-${index}`,
    "--provider", provider, "--model", model, "--tools", "bash", "-p", prompt,
  ], { cwd: dir, encoding: "utf8", timeout, env: process.env });
  if (result.error) throw result.error;
  assert.equal(result.status, 0, result.stderr || result.stdout);
  assert.equal(readFileSync(join(dir, "task.js"), "utf8"), 'const status = "ready";\n');
}

try {
  assert.ok(Number.isInteger(runs) && runs >= 2, "TAU_BENCH_RUNS must be at least 2");
  for (let index = 0; index < runs; index += 1) {
    writeFileSync(join(dir, "task.js"), 'const status = "draft";\n');
    run(index);
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
  assert.equal(byMode.current.runs, 1);
  assert.ok(byMode.candidate.runs >= 1);
  const report = { status: "ok", acceptance: "all sealed edits passed", modes: byMode };
  if (process.env.TAU_BENCH_REPORT) {
    writeFileSync(process.env.TAU_BENCH_REPORT, `${JSON.stringify(report, null, 2)}\n`);
  }
  console.log(JSON.stringify(report));
} finally {
  rmSync(dir, { recursive: true, force: true });
}
