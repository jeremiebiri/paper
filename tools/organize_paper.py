#!/usr/bin/env python3
"""Prepare paper text, sections, and references without network access.

PDF text is extracted with PyMuPDF. For math-heavy papers, provide a locally
prepared Markdown file or LaTeX sources to preserve equations more faithfully.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


REFERENCE_HEADINGS = (
    "references",
    "reference",
    "bibliography",
    "works cited",
    "literature",
    "参考文献",
)


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text).strip("-")
    return text or "section"


def _is_heading(line: str) -> bool:
    return bool(re.match(r"^\s{0,3}#{1,6}\s+\S", line))


def _heading_text(line: str) -> str:
    return re.sub(r"^\s{0,3}#{1,6}\s+", "", line).strip().lower()


def _looks_like_reference_start(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    return bool(
        re.match(r"^(\[\d+\]|\d+\.\s|•\s|-?\s*[A-Z][^.]+?\(\d{4}[a-z]?\))", stripped)
    )


def _extract_reference_entries(ref_text: str) -> list[dict[str, Any]]:
    entries: list[str] = []
    current: list[str] = []

    for raw_line in ref_text.splitlines():
        line = raw_line.strip()
        if line.startswith("<!-- page "):
            continue
        if not line:
            if current:
                entries.append(" ".join(current).strip())
                current = []
            continue
        if _looks_like_reference_start(line) and current:
            entries.append(" ".join(current).strip())
            current = [line]
            continue
        current.append(line)

    if current:
        entries.append(" ".join(current).strip())

    parsed: list[dict[str, Any]] = []
    for idx, entry in enumerate(entries, start=1):
        year_match = re.search(r"\b(19|20)\d{2}[a-z]?\b", entry)
        parsed.append(
            {
                "id": f"ref-{idx:03d}",
                "year": year_match.group(0) if year_match else None,
                "raw_text": entry,
            }
        )
    return parsed


def extract_references_from_markdown(md_text: str) -> list[dict[str, Any]]:
    lines = md_text.splitlines()
    start_idx: int | None = None
    for idx, line in enumerate(lines):
        if _is_heading(line) and _heading_text(line) in REFERENCE_HEADINGS:
            start_idx = idx + 1
            break

    if start_idx is None:
        return []

    ref_lines: list[str] = []
    for line in lines[start_idx:]:
        if _is_heading(line):
            break
        ref_lines.append(line)

    return _extract_reference_entries("\n".join(ref_lines))


def _split_markdown_sections(md_text: str) -> list[dict[str, str]]:
    sections: list[dict[str, str]] = []
    current_title = "front-matter"
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_lines, current_title
        body = "\n".join(current_lines).strip()
        if body:
            sections.append({"title": current_title, "content": body + "\n"})
        current_lines = []

    for line in md_text.splitlines():
        if _is_heading(line):
            flush()
            current_title = re.sub(r"^\s{0,3}#{1,6}\s+", "", line).strip()
            current_lines.append(line)
        else:
            current_lines.append(line)

    flush()
    return sections


def _write_sections(sections_dir: Path, sections: list[dict[str, str]]) -> list[Path]:
    if sections_dir.exists():
        for existing in sections_dir.glob("*.md"):
            existing.unlink()
    sections_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for idx, section in enumerate(sections, start=1):
        slug = _slugify(section['title'])[:80]
        filename = f"{idx:02d}-{slug}.md"
        target = sections_dir / filename
        target.write_text(section["content"], encoding="utf-8")
        written.append(target)
    return written


def _pdf_to_markdown(paper_file: Path, ocr: bool = False) -> tuple[str, list[int]]:
    """Extract native PDF text; optionally OCR pages with no text locally."""
    import fitz

    parts: list[str] = []
    empty_pages: list[int] = []
    with fitz.open(paper_file) as doc:
        if not doc.page_count:
            raise ValueError("The PDF has no pages")
        for page_no, page in enumerate(doc, 1):
            page_dict = page.get_text("dict", sort=True)
            if not "".join(
                span.get("text", "")
                for block in page_dict["blocks"]
                for line in block.get("lines", [])
                for span in line.get("spans", [])
            ).strip() and ocr:
                try:
                    textpage = page.get_textpage_ocr(language="eng", dpi=200, full=True)
                except Exception as exc:
                    raise RuntimeError(
                        "Local OCR failed. Install Tesseract and its English language data, "
                        "or supply --markdown-file from a local parser."
                    ) from exc
                page_dict = page.get_text("dict", textpage=textpage, sort=True)

            blocks = [block for block in page_dict["blocks"] if block.get("lines")]
            sizes = Counter()
            for block in blocks:
                for line in block["lines"]:
                    for span in line["spans"]:
                        sizes[round(span["size"], 1)] += len(span["text"].strip())
            body_size = sizes.most_common(1)[0][0] if sizes else 0
            paragraphs: list[str] = []
            for block in blocks:
                lines = []
                for line in block["lines"]:
                    line_text = "".join(span["text"] for span in line["spans"]).strip()
                    if line_text:
                        lines.append(line_text)
                if not lines:
                    continue
                block_text = "\n".join(lines)
                first_line = block["lines"][0]
                max_size = max((s["size"] for s in first_line["spans"]), default=0)
                heading = (len(lines) == 1 and len(lines[0]) < 120 and
                           (max_size >= body_size + 1.5 or
                            re.match(r"^(?:\d+(?:\.\d+)*\s+)?(?:References|Bibliography|Works Cited)$", lines[0], re.I)))
                if heading:
                    title = re.sub(r"^\d+(?:\.\d+)*\s+", "", lines[0])
                    paragraphs.append(f"## {title}")
                else:
                    paragraphs.append(block_text)
            if not paragraphs:
                empty_pages.append(page_no)
            parts.append(f"<!-- page {page_no} -->\n\n" + "\n\n".join(paragraphs))
    if len(empty_pages) == len(parts):
        raise ValueError("No extractable PDF text. Try --ocr or --markdown-file with a local parser.")
    return "\n\n".join(parts).strip() + "\n", empty_pages


def _write_paper_metadata(paper_dir: Path, md_text: str) -> dict[str, Any]:
    metadata_paper_dir = paper_dir / "metadata" / "paper"
    full_md = metadata_paper_dir / "full.md"
    references_json = metadata_paper_dir / "references.json"
    sections_dir = metadata_paper_dir / "sections"
    metadata_paper_dir.mkdir(parents=True, exist_ok=True)
    full_md.write_text(md_text, encoding="utf-8")
    references = extract_references_from_markdown(md_text)
    _write_json(references_json, references)
    written_sections = _write_sections(sections_dir, _split_markdown_sections(md_text))
    return {
        "full_md": str(full_md),
        "sections_dir": str(sections_dir),
        "sections_count": len(written_sections),
        "references_file": str(references_json),
        "references_count": len(references),
    }


def _prepare_from_pdf(paper_file: Path, markdown_file: Path | None = None,
                      ocr: bool = False) -> dict[str, Any]:
    if not paper_file.is_file():
        raise FileNotFoundError(paper_file)
    if markdown_file:
        md_text = markdown_file.read_text(encoding="utf-8")
        empty_pages: list[int] = []
        source = str(markdown_file)
    else:
        md_text, empty_pages = _pdf_to_markdown(paper_file, ocr=ocr)
        source = "local-pdf-text" + ("-and-ocr" if ocr else "")
    result = _write_paper_metadata(paper_file.parent, md_text)
    return {"paper_file": str(paper_file), "source": source,
            "pages_without_text": empty_pages, **result}


def _prepare_from_latex_dir(latex_dir: Path, main_tex: Path | None = None) -> dict[str, Any]:
    tex_files = sorted(latex_dir.glob("*.tex"))
    if not tex_files:
        raise FileNotFoundError(f"No .tex files found in {latex_dir}")

    root = latex_dir.resolve()
    if main_tex:
        tex_path = (root / main_tex).resolve() if not main_tex.is_absolute() else main_tex.resolve()
    else:
        preferred = [root / name for name in ("main.tex", "dissertation.tex", "thesis.tex")]
        tex_path = next((path for path in preferred if path.is_file()),
                        max(tex_files, key=lambda p: p.stat().st_size))
    if not tex_path.is_relative_to(root):
        raise ValueError(f"Main LaTeX file leaves source directory: {tex_path}")
    if not tex_path.is_file():
        raise FileNotFoundError(tex_path)
    visited: set[Path] = set()

    def expand(path: Path) -> str:
        path = path.resolve()
        if not path.is_relative_to(root):
            raise ValueError(f"LaTeX include leaves source directory: {path}")
        if path in visited:
            return ""
        visited.add(path)
        source = path.read_text(encoding="utf-8")

        def include(match: re.Match[str]) -> str:
            target = (path.parent / match.group(2)).with_suffix(".tex")
            return "\n" + expand(target) + "\n"

        return re.sub(r"(?m)^(\s*)\\(?:input|include)\{([^}]+)\}", include, source)

    text = expand(tex_path)

    md_text = re.sub(r"\\section\*?\{([^}]*)\}", r"# \1", text)
    md_text = re.sub(r"\\subsection\*?\{([^}]*)\}", r"## \1", md_text)
    md_text = re.sub(r"\\subsubsection\*?\{([^}]*)\}", r"### \1", md_text)

    references: list[dict[str, Any]] = []
    bib_files = sorted(latex_dir.rglob("*.bib"))
    if bib_files:
        raw_bib = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in bib_files)
        entries = re.split(r"(?=@\w+\{)", raw_bib)
        for idx, entry in enumerate(entries, start=1):
            entry = entry.strip()
            if not entry:
                continue
            year_match = re.search(r"year\s*=\s*[{\"]?((?:19|20)\d{2}[a-z]?)", entry, flags=re.I)
            references.append(
                {
                    "id": f"ref-{idx:03d}",
                    "year": year_match.group(1) if year_match else None,
                    "raw_text": entry,
                }
            )

    result = _write_paper_metadata(latex_dir, md_text)
    if references:
        _write_json(Path(result["references_file"]), references)
        result["references_count"] = len(references)
    return {"latex_dir": str(latex_dir), "main_tex": str(tex_path), **result}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create metadata/paper/full.md, references.json, and sections/*.md."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--paper-file", type=Path, help="Path to a local PDF.")
    group.add_argument("--latex-dir", type=Path, help="Path to a LaTeX source directory.")
    parser.add_argument("--markdown-file", type=Path,
                        help="Use locally parsed Markdown instead of extracting PDF text.")
    parser.add_argument("--ocr", action="store_true",
                        help="OCR pages without text using locally installed Tesseract.")
    parser.add_argument("--main-tex", type=Path,
                        help="Main .tex file within --latex-dir, e.g. dissertation.tex.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    if args.paper_file:
        if args.main_tex:
            raise ValueError("--main-tex requires --latex-dir")
        result = _prepare_from_pdf(args.paper_file.resolve(),
                                   args.markdown_file.resolve() if args.markdown_file else None,
                                   ocr=args.ocr)
    else:
        if args.markdown_file or args.ocr:
            raise ValueError("--ocr and --markdown-file require --paper-file")
        result = _prepare_from_latex_dir(args.latex_dir.resolve(), args.main_tex)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"full.md: {result['full_md']}")
        print(f"sections: {result['sections_count']} -> {result['sections_dir']}")
        print(f"references: {result['references_count']} -> {result['references_file']}")
        if result.get("pages_without_text"):
            print(f"Warning: no text on PDF pages {result['pages_without_text']}; "
                  "use --ocr or --markdown-file for complete review", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise
