# Tau

Tau is a local auto-improving harness layer for Pi. After install, users keep using Pi normally. Tau runs underneath: it injects compact workflow policy, measures tokens/time-to-acceptance, learns better modes per task bucket, and updates local policy.

## Install for Pi

```bash
pi install git:github.com/kevin91nl/tau -l --approve
```

Requirements:

- `python3` on PATH
- LM Studio running at `http://127.0.0.1:1234/v1`
- model loaded: `qwen3.6-35b-a3b-ud-mlx`

Then ask Pi:

```bash
pi "fix this bug"
```

Tau should stay invisible in normal use.

Available Pi tools:

```text
TauDoctor
TauPack
TauStatus
TauEval
TauSelfTest
TauImprove
TauAuto
TauMemoryAdd
TauMemoryList
TauProposalCreate
TauProposalLatest
TauProposalApply
TauProposalDiscard
TauABRecord
TauMeasureRecord
TauTrend
TauLearn
TauAdvise
TauLocateRead
TauMemoryPack
TauSecretScan
TauReviewer
```

Or run the sidecar CLI:

```bash
python -m tau_cli.main doctor
python -m tau_cli.main status
python -m tau_cli.main eval
python -m tau_cli.main selftest
python -m tau_cli.main pack "Reply exactly: TAU_PACK_OK" --cwd /Users/kevin/projects/tau
/Users/kevin/projects/tau/bin/pi-bare -p "$(python -m tau_cli.main pack 'Reply exactly: TAU_PACK_OK' --cwd /Users/kevin/projects/tau)"
python -m tau_cli.main improve "Improve Tau tests or docs"
```

## Auto-learning loop

Tau learns only from measured outcomes. Keep it simple:

1. Pi receives a silent Tau policy instruction before each turn.
2. Agent does the work with compact context.
3. Tau records tokens and elapsed time after the turn.
4. Tau updates `.tau/policy.json`.
5. `TauTrend` proves whether tokens/time improved.

CLI:

```bash
python -m tau_cli.main advise --bucket fix-test
python -m tau_cli.main measure record --bucket fix-test --mode current --accepted --input-tokens 12000 --output-tokens 800 --time-to-acceptance-s 90
python -m tau_cli.main measure record --bucket fix-test --mode candidate --accepted --input-tokens 9000 --output-tokens 500 --time-to-acceptance-s 60
python -m tau_cli.main learn --bucket fix-test
python -m tau_cli.main trend --bucket fix-test
```

### Memory commands

```bash
python -m tau_cli.main memory add "Use context pack for self-improvement" --scope workflow
python -m tau_cli.main memory list
python -m tau_cli.main memory list --include
```

### Proposal commands

```bash
python -m tau_cli.main proposal create --rel README.md --content "Updated readme"
python -m tau_cli.main proposal latest
python -m tau_cli.main proposal apply
python -m tau_cli.main proposal discard
```

### A/B record command

```bash
python -m tau_cli.main ab record --name pack_speed --baseline "10.0,12.0,11.0" --candidate "8.0,9.0,8.5"
```

### Measurement/trend commands

```bash
python -m tau_cli.main measure record --bucket fix-test --mode baseline --accepted --input-tokens 12000 --output-tokens 800 --time-to-acceptance-s 90
python -m tau_cli.main measure record --bucket fix-test --mode candidate --accepted --input-tokens 9000 --output-tokens 500 --time-to-acceptance-s 60
python -m tau_cli.main trend --bucket fix-test
```

### Compound/reviewer commands

```bash
python -m tau_cli.main locate-read README.md
python -m tau_cli.main memory-pack --scope .
python -m tau_cli.main secret-scan
python -m tau_cli.main proposal-check
python -m tau_cli.main reviewer git-diff
```
