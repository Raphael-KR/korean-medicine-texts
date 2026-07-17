#!/usr/bin/env python3
import json
import tempfile
import unittest
from pathlib import Path

from chunk_corpus import make_chunks


class ChunkCorpusTests(unittest.TestCase):
    def make_source(self, text: str) -> Path:
        directory = Path(tempfile.mkdtemp())
        path = directory / "source.md"
        path.write_text(text, encoding="utf-8")
        self.addCleanup(lambda: __import__("shutil").rmtree(directory))
        return path

    def test_neijing_uses_pian_then_zhang_and_preserves_lines(self) -> None:
        source = self.make_source("---\nid: x\n---\n# 제목\n\n上古天眞論篇 第一\n第一章\n본문 하나\n\n第二章\n본문 둘\n")
        chunks = make_chunks("huangdineijingsuwen", source, "a" * 64)
        self.assertEqual([chunk["headings"] for chunk in chunks], [["上古天眞論篇 第一", "第一章"], ["上古天眞論篇 第一", "第二章"]])
        lines = source.read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[chunks[0]["line_start"] - 1], "본문 하나")
        self.assertEqual(lines[chunks[1]["line_end"] - 1], "본문 둘")

    def test_donguibogam_uses_book_topic_and_item(self) -> None:
        source = self.make_source("# 제목\n東醫寶鑑內景篇卷之一\n{身形}\n【形氣之始】\n본문\n")
        chunks = make_chunks("donguibogam", source, "b" * 64)
        self.assertEqual(chunks[0]["headings"], ["東醫寶鑑內景篇卷之一", "身形", "形氣之始"])

    def test_repeated_running_heading_does_not_split(self) -> None:
        source = self.make_source("# 제목\n性命論\n본문 하나\n性命論\n본문 둘\n")
        chunks = make_chunks("donguisusebowon", source, "c" * 64)
        self.assertEqual(len(chunks), 1)
        self.assertIn("본문 둘", chunks[0]["text"])

    def test_chunk_records_are_json_serializable_and_stable(self) -> None:
        source = self.make_source("# 제목\n上古天眞論篇 第一\n第一章\n본문\n")
        chunks = make_chunks("huangdineijingsuwen", source, "d" * 64)
        self.assertEqual(chunks[0]["chunk_id"], "huangdineijingsuwen:00001")
        json.dumps(chunks[0], ensure_ascii=False)

    def test_size_split_and_short_tail_merge_preserve_exact_source_slice(self) -> None:
        source = self.make_source(
            "# 제목\n性命論\n첫 문단의 긴 본문\n\n두 번째 문단의 긴 본문\n\n짧은 꼬리\n"
        )
        chunks = make_chunks("donguisusebowon", source, "e" * 64, max_chars=18, min_chars=20)
        source_lines = source.read_text(encoding="utf-8").splitlines()
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            exact_slice = "\n".join(source_lines[chunk["line_start"] - 1 : chunk["line_end"]])
            self.assertEqual(chunk["text"], exact_slice)


if __name__ == "__main__":
    unittest.main()
