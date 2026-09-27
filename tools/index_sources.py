#!/usr/bin/env python3
"""Index user-supplied source papers for offline citation and prior-work checks."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

DOI = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.I)
EXTENSIONS = {".pdf", ".md", ".txt"}


def _read_source(path: Path) -> tuple[str, str]:
    if path.suffix.lower() == ".pdf":
        import fitz

        with fitz.open(path) as doc:
            title = (doc.metadata or {}).get("title", "").strip()
            text = "\n\n".join(
                f"<!-- page {i} -->\n{page.get_text(sort=True)}"
                for i, page in enumerate(doc, 1)
            )
    else:
        text = path.read_text(encoding="utf-8", errors="replace")
        title = ""
    if not title:
        title = next((line.lstrip("# ").strip() for line in text.splitlines()
                      if len(line.strip()) > 8 and not line.startswith("<!--")), path.stem)
    return title, text


def index(paper_dir: Path) -> dict:
    paper_dir = paper_dir.resolve()
    sources = paper_dir / "sources"
    if not sources.is_dir():
        raise FileNotFoundError(f"Create {sources} and put local source PDFs/Markdown there")
    output = paper_dir / "metadata" / "sources"
    output.mkdir(parents=True, exist_ok=True)
    for stale in output.glob("*.txt"):
        stale.unlink()
    records = []
    for path in sorted(sources.rglob("*")):
        if path.suffix.lower() not in EXTENSIONS or not path.is_file():
            continue
        if not path.resolve().is_relative_to(sources.resolve()):
            raise ValueError(f"Source symlink leaves the local corpus: {path}")
        title, text = _read_source(path)
        relative = path.relative_to(paper_dir).as_posix()
        digest = hashlib.sha256(relative.encode()).hexdigest()[:12]
        text_path = output / f"{digest}.txt"
        text_path.write_text(text, encoding="utf-8")
        dois = sorted({match.group(0).rstrip(".,;)").lower() for match in DOI.finditer(text)})
        records.append({"source_path": relative, "text_path": text_path.relative_to(paper_dir).as_posix(),
                        "title_hint": title, "dois": dois,
                        "text_extracted": bool(text.strip())})
    result = {"sources": records, "count": len(records),
              "note": "Candidates only. A reviewer must compare the actual local text before marking a claim verified."}
    (output / "index.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paper_dir", type=Path)
    args = parser.parse_args()
    result = index(args.paper_dir)
    print(f"Indexed {result['count']} local sources in {args.paper_dir}/metadata/sources/index.json")


if __name__ == "__main__":
    main()
