#!/usr/bin/env python3

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from search_corpus import default_repo_root, search


class SearchCorpusTests(unittest.TestCase):
    def make_repo(self) -> Path:
        root = Path(self.temp_dir.name)
        text_dir = root / "texts" / "sample"
        text_dir.mkdir(parents=True)
        (root / "catalog.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "texts": [
                        {
                            "id": "sample",
                            "title_ko": "표본",
                            "title_hanja": "標本",
                            "markdown_path": "texts/sample/source.md",
                            "quality_status": "raw_converted",
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (text_dir / "metadata.json").write_text(
            json.dumps({"quality_status": "reviewed", "quality_note": "일부 대조"}, ensure_ascii=False),
            encoding="utf-8",
        )
        (text_dir / "source.md").write_text("첫째 줄\n桂枝湯 원문\n셋째 줄\n", encoding="utf-8")
        return root

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_returns_locator_and_metadata(self) -> None:
        result = search("桂枝湯", self.make_repo(), max_results=1, context=1)
        self.assertEqual(result["match_count"], 1)
        self.assertFalse(result["truncated"])
        match = result["matches"][0]
        self.assertEqual(match["source_id"], "sample")
        self.assertEqual(match["line"], 2)
        self.assertEqual(match["quality_status"], "reviewed")
        self.assertIn("첫째 줄", match["excerpt"])

    def test_rejects_unknown_source_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "not registered"):
            search("桂枝湯", self.make_repo(), source_id="missing")

    def test_no_match_reports_search_scope(self) -> None:
        result = search("없는말", self.make_repo())
        self.assertEqual(result["match_count"], 0)
        self.assertEqual(result["searched_sources"], ["sample"])

    def test_environment_selects_global_install_corpus_root(self) -> None:
        root = self.make_repo()
        with patch.dict(os.environ, {"KOREAN_MEDICINE_TEXTS_ROOT": str(root)}):
            self.assertEqual(default_repo_root(), root)


if __name__ == "__main__":
    unittest.main()
