---
name: run-exp
description: Run experiments based on the plan from read-exp. Reads check_exp.json and check_code.json, creates environment, runs experiments, compares against paper numbers.
author: PaperDoctor Research
license: MIT
argument-hint: [paper_dir]
dependencies: [read-exp, read-code]
allowed-tools: Read, Grep, Glob, Bash
---

# Run Experiments

**This skill requires explicit user approval before execution.** Do not start automatically after Phase 2 — present the reproduction plan summary and wait for the user to confirm.

## Prerequisites

- `{paper_dir}/reports/check_exp.json` — experiment plan from read-exp (priority, feasibility, commands)
- `{paper_dir}/reports/check_code.json` — code issues from read-code (fix before running)

## Workflow

```text
- [ ] Step 1: Create environment
- [ ] Step 2: Run experiments
```

---

## Step 1: Create Environment

Use an environment and dependencies already installed locally. If the needed
environment cannot be created from local caches, report the reproduction as
`blocked` and identify the missing package. Do not run a package manager that
may reach the internet in this offline workflow.

Use only data and checkpoints already available locally. If a required input
is missing, mark that experiment `blocked` and record the missing file. Do not
download data, checkpoints, packages, or remote container images while offline.
Fix any `warning`/`error` items from check_code.json before running.

---

## Step 2: Run Experiments

Run experiments from `check_exp.json` in priority order (high first). Prefer eval over training.

For each experiment, compare output against the paper's numbers. Update `check_exp.json` with:

```json
{
  "our_result": {"metric": 0.0},
  "status": "pass",
  "note": "..."
}
```

| Status | Meaning |
|--------|---------|
| `pass` | Matches paper within ~1-2% |
| `warning` | Partial match or needed fixes |
| `error` | Significant difference or could not run |
| `blocked` | Required local inputs or environment are unavailable |

## Tips

- Follow the repo's README — do not guess
- OOM is `error` — note cause, do not retry endlessly
- Record exact command and hardware used
