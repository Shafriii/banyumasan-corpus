# Contributing

This repository accepts community pull requests for both code and corpus data.

## Corpus source of truth

Edit `data/corpus.csv`. Do not edit:

- `src/banyumasan_corpus/data/corpus.json`
- `korpus_clean_final.xlsx`

The packaged JSON is generated from the CSV by `scripts/build_corpus.py`.

## Required CSV columns

Each row in `data/corpus.csv` must include:

- `ngapak`: the Banyumasan form
- `indonesia`: the Indonesian gloss
- `contributor`: the person or handle responsible for the row
- `source_type`: one of `legacy_import`, `original_submission`, `published_reference`, `field_collection`
- `source_detail`: enough detail for a reviewer to understand where the row came from
- `notes`: optional notes for context, ambiguity, or review history

## Rights and provenance

Only submit rows you have the right to contribute.

Do not submit:

- copyrighted dictionary content you cannot redistribute
- scraped material with unclear licensing
- private or sensitive field data without permission

Every row needs enough provenance for a maintainer to review it. If the origin
is unclear, the PR should not be merged.

## Local checks

Before opening a PR, run:

```bash
python3 scripts/build_corpus.py
python3 -m unittest discover -s tests -v
```

If you are preparing a release candidate, also run:

```bash
python3 -m build
python3 -m twine check dist/*
```

## Pull request expectations

- keep changes focused on the requested correction or addition
- preserve duplicate headwords when they represent distinct meanings
- update docs when the contribution model or release process changes
- include a sign-off line in your commit message or PR description:

```text
Signed-off-by: Your Name <you@example.com>
```

That sign-off is your statement that you have the right to contribute the
change under this project’s published policies.

## Release policy

- PRs do not publish to PyPI
- merges to `main` do not publish to PyPI
- TestPyPI publishes are maintainer-triggered from GitHub Actions
- production PyPI publishes happen only from maintainer-created `v*` tags

For governance details, see [docs/corpus-governance.md](docs/corpus-governance.md).
