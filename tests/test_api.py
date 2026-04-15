from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from banyumasan_corpus import (
    CorpusEntry,
    TranslationBatchResult,
    TranslationChunk,
    TranslationMetrics,
    TranslationResult,
    analyze_translation,
    find_indonesia,
    find_ngapak,
    load_entries,
    stats,
    translate_ngapak,
    translate_ngapak_batch,
    translate_ngapak_detailed,
)
from banyumasan_corpus._api import _metrics_from_results, _translate_with_entries


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

    def test_analyze_translation_single_translated_token(self) -> None:
        result = translate_ngapak_detailed("abot")
        self.assertEqual(
            analyze_translation(result),
            TranslationMetrics(
                text_count=1,
                source_token_count=1,
                translated_token_count=1,
                untranslated_token_count=0,
                ambiguous_token_count=0,
                phrase_chunk_count=0,
                token_chunk_count=1,
                untranslated_chunk_count=0,
                delimiter_chunk_count=0,
                coverage_ratio=1.0,
                ambiguity_ratio=0.0,
            ),
        )

    def test_analyze_translation_ambiguous_token(self) -> None:
        result = translate_ngapak_detailed("dhuwur")
        metrics = analyze_translation(result)
        self.assertEqual(metrics.ambiguous_token_count, 1)
        self.assertEqual(metrics.translated_token_count, 1)
        self.assertEqual(metrics.ambiguity_ratio, 1.0)

    def test_analyze_translation_untranslated_token(self) -> None:
        result = translate_ngapak_detailed("xyz")
        metrics = analyze_translation(result)
        self.assertEqual(metrics.source_token_count, 1)
        self.assertEqual(metrics.translated_token_count, 0)
        self.assertEqual(metrics.untranslated_token_count, 1)
        self.assertEqual(metrics.coverage_ratio, 0.0)
        self.assertEqual(metrics.ambiguity_ratio, 0.0)

    def test_analyze_translation_phrase_chunk_counts_full_span(self) -> None:
        entries = (CorpusEntry(ngapak="wong apik", indonesia="orang baik"),)
        result = _translate_with_entries("wong apik", entries)
        metrics = analyze_translation(result)
        self.assertEqual(metrics.source_token_count, 2)
        self.assertEqual(metrics.translated_token_count, 2)
        self.assertEqual(metrics.phrase_chunk_count, 1)
        self.assertEqual(metrics.coverage_ratio, 1.0)

    def test_analyze_translation_empty_result_returns_zero_metrics(self) -> None:
        result = translate_ngapak_detailed("")
        self.assertEqual(
            analyze_translation(result),
            TranslationMetrics(
                text_count=1,
                source_token_count=0,
                translated_token_count=0,
                untranslated_token_count=0,
                ambiguous_token_count=0,
                phrase_chunk_count=0,
                token_chunk_count=0,
                untranslated_chunk_count=0,
                delimiter_chunk_count=0,
                coverage_ratio=0.0,
                ambiguity_ratio=0.0,
            ),
        )

    def test_translate_ngapak_batch_preserves_input_order(self) -> None:
        batch = translate_ngapak_batch(("abot", "xyz", "dhuwur"))
        self.assertIsInstance(batch, TranslationBatchResult)
        self.assertEqual(
            tuple(result.source_text for result in batch.results),
            ("abot", "xyz", "dhuwur"),
        )
        self.assertEqual(
            tuple(result.translated_text for result in batch.results),
            ("berat", "xyz", "tinggi"),
        )

    def test_translate_ngapak_batch_aggregates_mixed_metrics(self) -> None:
        batch = translate_ngapak_batch(("abot", "xyz", "dhuwur"))
        self.assertEqual(
            batch.metrics,
            TranslationMetrics(
                text_count=3,
                source_token_count=3,
                translated_token_count=2,
                untranslated_token_count=1,
                ambiguous_token_count=1,
                phrase_chunk_count=0,
                token_chunk_count=2,
                untranslated_chunk_count=1,
                delimiter_chunk_count=0,
                coverage_ratio=2 / 3,
                ambiguity_ratio=1 / 2,
            ),
        )

    def test_translate_ngapak_batch_handles_empty_strings(self) -> None:
        batch = translate_ngapak_batch(("", "abot"))
        self.assertEqual(len(batch.results), 2)
        self.assertEqual(batch.results[0].translated_text, "")
        self.assertEqual(batch.metrics.text_count, 2)
        self.assertEqual(batch.metrics.source_token_count, 1)
        self.assertEqual(batch.metrics.coverage_ratio, 1.0)

    def test_translate_ngapak_batch_synthetic_phrase_and_ambiguity_fixture(self) -> None:
        results = (
            _translate_with_entries(
                "wong apik",
                (
                    CorpusEntry(ngapak="wong", indonesia="orang"),
                    CorpusEntry(ngapak="apik", indonesia="bagus"),
                    CorpusEntry(ngapak="wong apik", indonesia="orang baik"),
                ),
            ),
            _translate_with_entries(
                "dhuwur xyz",
                (
                    CorpusEntry(ngapak="dhuwur", indonesia="tinggi"),
                    CorpusEntry(ngapak="dhuwur", indonesia="atas"),
                ),
            ),
        )
        metrics = _metrics_from_results(results)
        self.assertEqual(
            metrics,
            TranslationMetrics(
                text_count=2,
                source_token_count=4,
                translated_token_count=3,
                untranslated_token_count=1,
                ambiguous_token_count=1,
                phrase_chunk_count=1,
                token_chunk_count=1,
                untranslated_chunk_count=1,
                delimiter_chunk_count=1,
                coverage_ratio=3 / 4,
                ambiguity_ratio=1 / 3,
            ),
        )


if __name__ == "__main__":
    unittest.main()
