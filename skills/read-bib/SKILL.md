---
name: read-bib
description: Check references against user-supplied local source papers only.
allowed-tools: Read, Glob, Grep, Bash(python *)
---

# Offline Bibliography Check

Read `{paper_dir}/metadata/paper/references.json`. If local source papers are
present under `{paper_dir}/sources/`, run
`python tools/index_sources.py {paper_dir}` and inspect
`{paper_dir}/metadata/sources/index.json` and its extracted text files.

For **every** reference, copy `id`, `year`, and `raw_text` without changing them.
Use `pass` only after a local source's actual text supports the cited title,
authors, year, and identifier. Add `reference` with the local source path and
`reason` with the matching evidence. A DOI match in an index is a candidate,
not enough on its own to pass. Use `warning` for a confirmed mismatch in a
source that can be identified. Use `unverifiable` if no relevant local source
exists, text extraction failed, or the evidence is insufficient. **Do not mark
an absent local PDF as an invalid publication.** Never fabricate identifiers.

Do not use WebSearch, WebFetch, external APIs, or network commands. Save
`{paper_dir}/reports/check_bib.json` with a `summary` count and a `results`
array. Each result should include `status`, `reason`, and `reference` when
local evidence exists. Example:

```json
{
  "summary": {"total": 1, "pass": 0, "warning": 0, "error": 0, "unverifiable": 1},
  "results": [{"id": "ref-001", "year": "2024", "raw_text": "...", "status": "unverifiable", "reason": "No matching paper in the supplied local corpus"}]
}
```
