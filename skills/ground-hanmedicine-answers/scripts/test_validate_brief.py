#!/usr/bin/env python3

import unittest

from validate_brief import validate


class ValidateBriefTests(unittest.TestCase):
    def test_rejects_unsourced_percentage(self) -> None:
        errors, _ = validate("치료율은 70%로 보고되었다.")
        self.assertTrue(any("percentage" in error for error in errors))

    def test_accepts_sourced_percentage(self) -> None:
        errors, _ = validate("반응률은 70%였다. https://example.org/study")
        self.assertEqual(errors, [])

    def test_warns_on_untraceable_rag_claim(self) -> None:
        _, warnings = validate("자체 RAG 데이터베이스를 검색하여 확인했다.")
        self.assertTrue(any("retrieval claim" in warning for warning in warnings))

    def test_warns_when_local_citation_omits_quality(self) -> None:
        _, warnings = validate("원문 인용: texts/donguibogam/source.md:123")
        self.assertTrue(any("quality-status" in warning for warning in warnings))

    def test_accepts_local_citation_with_quality(self) -> None:
        errors, warnings = validate("원문 인용: texts/donguibogam/source.md:123 — quality: raw_converted")
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])


if __name__ == "__main__":
    unittest.main()
