---
name: prepare-paper
description: Prepare a paper for review using local files only, without uploading the PDF.
author: PaperDoctor Research
license: MIT
argument-hint: [paper_dir]
allowed-tools: Read, Glob, Bash(python *)
---

# Prepare Paper Offline

Work from the repository root. Never call Mathpix, MinerU's hosted API, a web
search, or any other remote service. All input and output stays in the paper
directory. Do not add private paper directories to Git.

1. Find the main PDF in `{paper_dir}/`. If there is more than one, choose the
   main paper explicitly. Extract its text and reference entries locally:

   ```bash
   python tools/organize_paper.py --paper-file {paper_dir}/paper.pdf
   ```

   Replace `paper.pdf` with the real filename. For pages that contain only
   images, install Tesseract locally and add `--ocr`. If the author already has
   a higher-quality local Markdown extraction, add `--markdown-file PATH`.
   For LaTeX sources use `--latex-dir PATH --main-tex ROOT.tex`; that source directory gets its own
   `metadata/paper/` output. The PDF is still needed for visual review.
2. Render pages with `python tools/pdf_render.py {paper_dir}/paper.pdf`.
3. If the author has supplied a code repository, index it with
   `python tools/code_analyzer.py PATH --output {paper_dir}/metadata/code/index.json`.
   Otherwise skip code indexing and record that code checks cannot run.
4. If `{paper_dir}/sources/` contains local prior papers, run
   `python tools/index_sources.py {paper_dir}`. An empty or missing corpus is
   acceptable; bibliography and novelty claims then remain unverifiable.

The canonical paper text is `{paper_dir}/metadata/paper/full.md` and its
references are `{paper_dir}/metadata/paper/references.json`. Check for
`pages_without_text` in the organizer output. Missing text means the review is
incomplete; never treat missing extraction as evidence that a section is absent.
