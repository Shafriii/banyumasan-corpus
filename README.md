# banyumasan-corpus

`banyumasan-corpus` packages a Banyumasan (Ngapak) to Indonesian corpus as a
small, dependency-free Python library.

The source of truth is the spreadsheet `korpus_clean_final.xlsx`. During
development or release preparation, the project converts that workbook into a
packaged UTF-8 JSON file. At runtime, the library reads the generated JSON, not
the original Excel file.

## What the corpus contains

- 2,000 translation pairs
- 1 worksheet with the columns `ngapak` and `indonesia`
- Unicode entries preserved exactly as written, including forms such as
  `golèk` and `lènggèr`
- A few duplicate Banyumasan headwords with multiple Indonesian meanings

This package is intended as a base resource for Banyumasan NLP research. It
gives you the original row-level pairs, lookup helpers, and a deterministic
baseline translator for full-text and word-level experiments.

## Installation

```bash
python3 -m pip install banyumasan-corpus
```

## Quick start

```python
from banyumasan_corpus import (
    TranslationResult,
    find_indonesia,
    find_ngapak,
    load_entries,
    stats,
    translate_ngapak,
    translate_ngapak_detailed,
)

entries = load_entries()
print(len(entries))
# 2000

print(find_ngapak("dhuwur"))
# [
#   CorpusEntry(ngapak='dhuwur', indonesia='tinggi'),
#   CorpusEntry(ngapak='dhuwur', indonesia='atas'),
# ]

print(find_indonesia("jatuh", exact=True)[:3])
# [
#   CorpusEntry(...),
#   CorpusEntry(...),
#   CorpusEntry(...),
# ]

print(find_indonesia("mencari"))
# substring match on the Indonesian gloss

print(translate_ngapak("Abot, golèk!"))
# "Berat, mencari!"

result = translate_ngapak_detailed("Abot, golèk!")
print(isinstance(result, TranslationResult))
# True
print(result.translated_text)
# "Berat, mencari!"
print(result.chunks[0])
# TranslationChunk(...)

print(stats())
# {
#   'entry_count': 2000,
#   'unique_ngapak': 1996,
#   'unique_indonesia': 1444,
#   'duplicate_ngapak_terms': 4,
# }
```

## API

### `load_entries() -> tuple[CorpusEntry, ...]`

Returns the whole corpus as immutable dataclass instances in the original row
order.

### `find_ngapak(term: str) -> list[CorpusEntry]`

Performs a case-insensitive exact lookup on the Banyumasan column.

The return type is always a list because the source corpus contains duplicate
headwords. For example:

- `dhuwur` maps to `tinggi` and `atas`
- `dolan` maps to `main / jalan` and `jalan-jalan`
- `dunya` maps to `harta benda` and `dunia`
- `enggal` maps to `sebentar lagi` and `cepat`

### `find_indonesia(term: str, exact: bool = False) -> list[CorpusEntry]`

Searches the Indonesian gloss column.

- `exact=False` performs a case-insensitive substring match
- `exact=True` performs a case-insensitive exact match

### `stats() -> dict[str, int]`

Returns basic corpus statistics:

- `entry_count`
- `unique_ngapak`
- `unique_indonesia`
- `duplicate_ngapak_terms`

### `translate_ngapak(text: str) -> str`

Provides a deterministic Banyumasan-to-Indonesian translation string for quick
use.

Behavior:

- exact case-insensitive matching
- greedy longest phrase match before token fallback
- preserves punctuation and whitespace
- preserves unknown tokens unchanged
- chooses the first corpus meaning when a headword is ambiguous

Example:

```python
translate_ngapak("Abot, golèk!")
# "Berat, mencari!"

translate_ngapak("dhuwur")
# "tinggi"
```

### `translate_ngapak_detailed(text: str) -> TranslationResult`

Provides structured translation output for research workflows.

The returned `TranslationResult` contains:

- `source_text`
- `translated_text`
- `chunks`

Each `TranslationChunk` records:

- the original source span,
- the chosen translated span,
- whether the chunk came from a `phrase`, `token`, `untranslated`, or
  `delimiter`,
- token offsets,
- all candidate corpus rows used for deterministic disambiguation,
- whether the match was ambiguous.

This is useful for:

- full-text lexical baselines,
- rule-based translation experiments,
- corpus bootstrapping,
- weak supervision,
- alignment-like inspection for future models.

It is still not a grammar-aware sentence translator. Ambiguous words, idioms,
and unseen multiword expressions still need downstream modeling.

## How the corpus works

The package preserves the spreadsheet as row-level bilingual pairs:

1. the first column is the Banyumasan term,
2. the second column is the Indonesian gloss,
3. row order is preserved exactly,
4. duplicate Banyumasan headwords are preserved rather than merged.

That means the package is useful for:

- exact term lookup,
- reverse lookup from Indonesian glosses,
- deterministic full-text baseline translation,
- exporting the data into your own NLP or lexicon pipelines,
- inspecting ambiguous Banyumasan entries without losing the original rows.

## Regenerate the packaged JSON

If you update `korpus_clean_final.xlsx`, rebuild the packaged corpus file:

```bash
python3 scripts/build_corpus.py
```

The script validates that:

- the workbook has exactly one sheet,
- the header is exactly `ngapak`, `indonesia`,
- every data row has exactly two populated cells.

The generated JSON is written to:

```text
src/banyumasan_corpus/data/corpus.json
```

## Run tests

```bash
python3 -m unittest discover -s tests -v
```

## Publish to PyPI

See [docs/publishing-to-pypi.md](docs/publishing-to-pypi.md) for the full
release workflow, including TestPyPI and production PyPI uploads.
