"""Small end-to-end checks for the local preparation boundary."""

import json
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import fitz

from tools.index_sources import index
from tools.organize_paper import _prepare_from_latex_dir, _prepare_from_pdf


class OfflineWorkflowTest(unittest.TestCase):
    def test_pdf_preparation_and_source_index_need_no_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            paper_dir = Path(tmp) / "paper"
            paper_dir.mkdir()
            pdf = paper_dir / "paper.pdf"
            with fitz.open() as doc:
                page = doc.new_page()
                page.insert_text((50, 50), "Local Paper", fontsize=18)
                page.insert_text((50, 95), "Introduction", fontsize=14)
                page.insert_text((50, 120), "We evaluated a local prototype.", fontsize=10)
                page = doc.new_page()
                page.insert_text((50, 50), "References", fontsize=14)
                page.insert_text((50, 80), "[1] Jane Doe. Offline Source. 2024. doi:10.1000/example", fontsize=10)
                doc.new_page()  # should be reported as missing extractable text
                doc.save(pdf)

            source_dir = paper_dir / "sources"
            source_dir.mkdir()
            (source_dir / "reference.md").write_text(
                "# Offline Source\nJane Doe (2024). DOI: 10.1000/example.\n", encoding="utf-8"
            )
            with patch.object(socket.socket, "connect", side_effect=AssertionError("network used")):
                result = _prepare_from_pdf(pdf)
                corpus = index(paper_dir)

            self.assertEqual(result["pages_without_text"], [3])
            self.assertEqual(result["references_count"], 1)
            self.assertIn("Introduction", Path(result["full_md"]).read_text())
            self.assertEqual(corpus["count"], 1)
            self.assertIn("10.1000/example", corpus["sources"][0]["dois"])
            refs = json.loads(Path(result["references_file"]).read_text())
            self.assertEqual(refs[0]["id"], "ref-001")

    def test_multifile_latex_is_local_and_keeps_bibliography(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "chapters").mkdir()
            (root / "main.tex").write_text(
                "\\section{Aim}\n\\input{chapters/method}\n", encoding="utf-8"
            )
            (root / "chapters" / "method.tex").write_text(
                "\\subsection{Method}\nPrivate method text.\n", encoding="utf-8"
            )
            (root / "sources.bib").write_text(
                "@article{doe2024, title={Offline Source}, year={2024}}", encoding="utf-8"
            )
            with patch.object(socket.socket, "connect", side_effect=AssertionError("network used")):
                result = _prepare_from_latex_dir(root)
            text = Path(result["full_md"]).read_text()
            self.assertIn("# Aim", text)
            self.assertIn("## Method", text)
            self.assertIn("Private method text", text)
            self.assertEqual(result["references_count"], 1)


if __name__ == "__main__":
    unittest.main()
