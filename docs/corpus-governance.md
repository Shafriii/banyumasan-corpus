# Corpus Governance

This document describes how community contributions are reviewed and what the
repository currently guarantees about the corpus.

## Canonical dataset file

The canonical dataset lives in:

```text
data/corpus.csv
```

The packaged runtime JSON at `src/banyumasan_corpus/data/corpus.json` is a
generated artifact built from that CSV.

## Provenance requirements

Every merged row must include:

- the Banyumasan form
- the Indonesian gloss
- the contributor responsible for the row
- a `source_type`
- a `source_detail`

Allowed `source_type` values are:

- `legacy_import`
- `original_submission`
- `published_reference`
- `field_collection`

`notes` is optional and is intended for ambiguity notes, review context, or
other short annotations.

## Review policy

Maintainers should merge rows only when they can defend:

- the contributor’s right to submit the row
- the provenance supplied in the row
- the lexical quality of the translation pair
- whether duplicate headwords reflect distinct meanings rather than accidental duplication

The build script enforces the structural checks. Semantic review still happens
in pull request review.

## Legacy import status

The existing corpus rows were bootstrapped from `korpus_clean_final.xlsx`
before the community workflow was introduced. Those rows now appear in
`data/corpus.csv` with `source_type=legacy_import`.

That workbook is kept as a historical import snapshot, not as the canonical
editing surface for future contributions.

## Code and data policy

The repository code is MIT-licensed.

The dataset side of the repository now requires provenance and contributor
sign-off, but it does not yet declare a separate public data license beyond the
repository’s current published files. If you want to market the corpus as fully
open data, publish that data license explicitly before broad third-party reuse.

Until then, maintainers should only accept rows from contributors who clearly
state they have the right to submit them.

## Release policy

- PRs run checks only
- pushes to `main` run checks only
- TestPyPI publishes require a maintainer-triggered workflow run
- production PyPI publishes require a maintainer-created tag and environment approval
