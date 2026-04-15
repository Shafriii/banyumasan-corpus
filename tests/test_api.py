from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from banyumasan_corpus import (
    CorpusEntry,
    TranslationChunk,
    TranslationResult,
    find_indonesia,
    find_ngapak,
    load_entries,
    stats,
    translate_ngapak,
    translate_ngapak_detailed,
)
from banyumasan_corpus._api import _translate_with_entries


class ApiTests(unittest.TestCase):
    def test_load_entries_returns_expected_shape(self) -> None:
        entries = load_entries()
        self.assertEqual(len(entries), 2000)
        self.assertIsInstance(entries[0], CorpusEntry)
        self.assertEqual(entries[0].ngapak, "abab")
        self.assertEqual(entries[0].indonesia, "tiupan napas")

    def test_load_entries_returns_immutable_tuple(self) -> None:
        entries = load_entries()
        with self.assertRaises(AttributeError):
            entries[0].ngapak = "changed"  # type: ignore[misc]
        with self.assertRaises(TypeError):
            entries[0:0] = ()  # type: ignore[misc]

    def test_find_ngapak_preserves_duplicate_headwords(self) -> None:
        matches = find_ngapak("dhuwur")
        self.assertEqual(
            matches,
            [
                CorpusEntry(ngapak="dhuwur", indonesia="tinggi"),
                CorpusEntry(ngapak="dhuwur", indonesia="atas"),
            ],
        )

    def test_find_indonesia_exact_returns_all_matches(self) -> None:
        matches = find_indonesia("jatuh", exact=True)
        self.assertEqual(len(matches), 16)
        self.assertTrue(all(entry.indonesia == "jatuh" for entry in matches))

    def test_find_indonesia_substring_search(self) -> None:
        matches = find_indonesia("mencari")
        self.assertTrue(matches)
        self.assertIn(
            CorpusEntry(ngapak="didis", indonesia="mencari kutu"),
            matches,
        )
        self.assertIn(
            CorpusEntry(ngapak="golèk", indonesia="mencari"),
            matches,
        )

    def test_stats_reports_expected_counts(self) -> None:
        self.assertEqual(
            stats(),
            {
                "entry_count": 2000,
                "unique_ngapak": 1996,
                "unique_indonesia": 1444,
                "duplicate_ngapak_terms": 4,
            },
        )

    def test_blank_queries_return_empty_lists(self) -> None:
        self.assertEqual(find_ngapak("   "), [])
        self.assertEqual(find_indonesia("   "), [])

    def test_translate_ngapak_translates_tokens_and_preserves_punctuation(self) -> None:
        self.assertEqual(
            translate_ngapak("Abot, golèk!"),
            "Berat, mencari!",
        )

    def test_translate_ngapak_keeps_unknown_tokens(self) -> None:
        self.assertEqual(
            translate_ngapak("abot xyz"),
            "berat xyz",
        )

    def test_translate_ngapak_uses_first_translation_for_ambiguous_entries(self) -> None:
        self.assertEqual(
            translate_ngapak("dhuwur"),
            "tinggi",
        )

    def test_translate_ngapak_preserves_whitespace(self) -> None:
        self.assertEqual(
            translate_ngapak("abot   golèk"),
            "berat   mencari",
        )

    def test_translate_ngapak_detailed_returns_structured_result(self) -> None:
        result = translate_ngapak_detailed("Abot, golèk!")
        self.assertIsInstance(result, TranslationResult)
        self.assertEqual(result.translated_text, "Berat, mencari!")
        self.assertEqual(
            tuple(chunk.kind for chunk in result.chunks),
            ("token", "delimiter", "token", "delimiter"),
        )
        self.assertEqual("".join(chunk.translated_text for chunk in result.chunks), result.translated_text)

    def test_translate_ngapak_detailed_marks_ambiguous_matches(self) -> None:
        result = translate_ngapak_detailed("dhuwur")
        self.assertEqual(result.translated_text, "tinggi")
        self.assertEqual(len(result.chunks), 1)
        chunk = result.chunks[0]
        self.assertEqual(chunk.kind, "token")
        self.assertTrue(chunk.ambiguous)
        self.assertEqual(
            chunk.candidates,
            (
                CorpusEntry(ngapak="dhuwur", indonesia="tinggi"),
                CorpusEntry(ngapak="dhuwur", indonesia="atas"),
            ),
        )

    def test_translate_ngapak_detailed_keeps_unknown_tokens(self) -> None:
        result = translate_ngapak_detailed("xyz.")
        self.assertEqual(result.translated_text, "xyz.")
        self.assertEqual(
            result.chunks,
            (
                TranslationChunk(
                    source_text="xyz",
                    translated_text="xyz",
                    kind="untranslated",
                    token_start=0,
                    token_end=0,
                    candidates=(),
                    ambiguous=False,
                ),
                TranslationChunk(
                    source_text=".",
                    translated_text=".",
                    kind="delimiter",
                    token_start=None,
                    token_end=None,
                    candidates=(),
                    ambiguous=False,
                ),
            ),
        )

    def test_translate_ngapak_wrapper_matches_detailed_output(self) -> None:
        text = "Abot, golèk!"
        self.assertEqual(
            translate_ngapak(text),
            translate_ngapak_detailed(text).translated_text,
        )

    def test_translate_ngapak_detailed_phrase_prefers_longest_match(self) -> None:
        entries = (
            CorpusEntry(ngapak="wong", indonesia="orang"),
            CorpusEntry(ngapak="apik", indonesia="bagus"),
            CorpusEntry(ngapak="wong apik", indonesia="orang baik"),
        )
        result = _translate_with_entries("wong apik", entries)
        self.assertEqual(result.translated_text, "orang baik")
        self.assertEqual(len(result.chunks), 1)
        self.assertEqual(result.chunks[0].kind, "phrase")
        self.assertEqual(result.chunks[0].token_start, 0)
        self.assertEqual(result.chunks[0].token_end, 1)

    def test_translate_ngapak_detailed_phrase_stops_at_punctuation(self) -> None:
        entries = (
            CorpusEntry(ngapak="wong", indonesia="orang"),
            CorpusEntry(ngapak="apik", indonesia="bagus"),
            CorpusEntry(ngapak="wong apik", indonesia="orang baik"),
        )
        result = _translate_with_entries("wong, apik", entries)
        self.assertEqual(result.translated_text, "orang, bagus")
        self.assertEqual(
            tuple(chunk.kind for chunk in result.chunks),
            ("token", "delimiter", "token"),
        )

    def test_translate_ngapak_detailed_phrase_falls_back_to_tokens(self) -> None:
        entries = (
            CorpusEntry(ngapak="wong", indonesia="orang"),
            CorpusEntry(ngapak="apik", indonesia="bagus"),
        )
        result = _translate_with_entries("wong apik", entries)
        self.assertEqual(result.translated_text, "orang bagus")
        self.assertEqual(
            tuple(chunk.kind for chunk in result.chunks),
            ("token", "delimiter", "token"),
        )

    def test_translate_ngapak_detailed_preserves_uppercase_and_titlecase(self) -> None:
        entries = (CorpusEntry(ngapak="wong apik", indonesia="orang baik"),)
        upper = _translate_with_entries("WONG APIK", entries)
        title = _translate_with_entries("Wong apik", entries)
        self.assertEqual(upper.translated_text, "ORANG BAIK")
        self.assertEqual(title.translated_text, "Orang baik")


if __name__ == "__main__":
    unittest.main()
