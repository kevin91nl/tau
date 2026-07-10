# Tau

Tau is a local harness layer for bare Pi. It measures runs, builds compact context packs, records traces, and can use bare Pi to propose improvements to Tau itself.

## Install for Pi

```bash
pi install git:github.com/kevin91nl/tau
```

Requirements:

- `python3` on PATH
- LM Studio running at `http://127.0.0.1:1234/v1`
- model loaded: `qwen3.6-35b-a3b-ud-mlx`

Then ask Pi:

```bash
pi "Use TauDoctor, then TauPack for this task before editing."
```

Available Pi tools:

```text
TauDoctor
TauPack
TauStatus
TauEval
TauMemoryAdd
TauMemoryList
TauProposalCreate
TauProposalLatest
TauProposalApply
TauProposalDiscard
TauABRecord
```

Or run the sidecar CLI:

```bash
python -m tau_cli.main doctor
python -m tau_cli.main status
python -m tau_cli.main eval
python -m tau_cli.main pack "Reply exactly: TAU_PACK_OK" --cwd /Users/kevin/projects/tau
/Users/kevin/projects/tau/bin/pi-bare -p "$(python -m tau_cli.main pack 'Reply exactly: TAU_PACK_OK' --cwd /Users/kevin/projects/tau)"
python -m tau_cli.main improve "Improve Tau tests or docs"
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
