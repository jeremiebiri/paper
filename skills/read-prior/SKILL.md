---
name: read-prior
description: Check related-work claims against supplied local papers and report corpus limits.
author: PaperDoctor Research
license: MIT
argument-hint: [paper_dir]
allowed-tools: Read, Glob, Grep, Bash(python *)
---

# Offline Prior Work Check

Read `{paper_dir}/reports/check_claim.json`; include **every** claim whose
`evidence_type` contains `related_work`. Read only the local corpus under
`{paper_dir}/sources/` and its extracted text in
`{paper_dir}/metadata/sources/` (run `python tools/index_sources.py {paper_dir}`
if needed and if `sources/` exists). With no local corpus, mark claims
`unverifiable`. Copy each claim's `id`, `source`, `quote`, `claim`, and
`evidence_type` unchanged into `{paper_dir}/reports/check_prior.json`.

- For a cited fact or baseline number, mark `pass` only with a precise passage,
  table, or page in a supplied paper. Record its local `reference` path and
  the exact supporting detail in `reason`.
- Mark `warning` for an imprecise comparison or mismatched setting, and
  `error` only when a local paper clearly contradicts the claim. Give a
  concrete `suggest` for either.
- Mark `unverifiable` when evidence is absent or ambiguous.
- A "first" or global novelty claim cannot be established from a bounded
  offline corpus. Mark it `unverifiable` unless a local counterexample proves
  it false (`error`). Do not label it `novel` merely because no match was found.

Include `summary` counts and `results`. Never use WebSearch, WebFetch,
remote APIs, or URLs as substitutes for local evidence. Explicitly state the
number of indexed source documents and the corpus limitation in the summary.
