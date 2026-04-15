# Local Testing Guide

This guide shows how to set up a local environment, run the tests, and try the
package interactively before publishing.

## 1. Create the local environment

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip build twine
```

## 2. Regenerate the packaged corpus data

If `data/corpus.csv` changed, rebuild the packaged JSON:

```bash
python3 scripts/build_corpus.py
```

This writes:

```text
src/banyumasan_corpus/data/corpus.json
```

## 3. Install the package locally

For local development, install it in editable mode:

```bash
python3 -m pip install -e .
```

## 4. Run the full test suite

```bash
python3 -m unittest discover -s tests -v
```

This covers:

- corpus loading,
- exact and reverse lookup,
- full-text translation,
- detailed translation output,
- intrinsic metrics,
- batch translation,
- CSV-to-JSON build validation and provenance checks.

## 5. Try the package in Python

### Quick translation

```bash
python3 - <<'PY'
from banyumasan_corpus import translate_ngapak

print(translate_ngapak("Abot, golèk!"))
PY
```

Expected output:

```text
Berat, mencari!
```

### Detailed translation and metrics

```bash
python3 - <<'PY'
from banyumasan_corpus import (
    analyze_translation,
    translate_ngapak_batch,
    translate_ngapak_detailed,
)

result = translate_ngapak_detailed("dhuwur xyz")
print(result.translated_text)
print(result.chunks)
print(analyze_translation(result))

batch = translate_ngapak_batch(["Abot, golèk!", "dhuwur xyz"])
print(batch.metrics)
PY
```

What to expect:

- known Banyumasan words are translated,
- unknown words such as `xyz` stay unchanged,
- ambiguous words such as `dhuwur` use the first corpus meaning in the final
  string,
- metrics report coverage and ambiguity ratios.

## 6. Test the built package artifact

If you want to verify the exact wheel that would be published:

```bash
python3 -m build
python3 -m twine check dist/*
python3 -m pip install --force-reinstall dist/banyumasan_corpus-0.1.0-py3-none-any.whl
```

Then run the same Python snippets again to confirm the installed wheel behaves
correctly.

## 7. Deactivate the environment

```bash
deactivate
```
