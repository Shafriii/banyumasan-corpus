# Publishing `banyumasan-corpus` to PyPI

This guide assumes you are publishing from the project root and that the PyPI
distribution name will be `banyumasan-corpus`.

As of April 15, 2026, `https://pypi.org/project/banyumasan-corpus/` returned
`404 Not Found`, so the name appeared to be available at that time. Verify it
again right before your first upload.

## 1. Fill in the package metadata

Before publishing, update the placeholders in `pyproject.toml` and `LICENSE`:

- replace `YOUR NAME`
- replace `your.email@example.com`
- replace the GitHub placeholder URLs

Also confirm that the package version is correct. The initial version in this
project is `0.1.0`.

## 2. Create PyPI and TestPyPI accounts

You need separate accounts for:

- PyPI: `https://pypi.org/account/register/`
- TestPyPI: `https://test.pypi.org/account/register/`

TestPyPI is a separate service and may be cleaned periodically, so treat it as
a disposable testing environment.

## 3. Create API tokens

Create an API token in each service after logging in:

- PyPI token page: `https://pypi.org/manage/account/#api-tokens`
- TestPyPI token page: `https://test.pypi.org/manage/account/#api-tokens`

For the first upload of a new project, create a token that is not restricted to
an existing project, because the project does not exist there yet.

Keep both tokens somewhere safe. PyPI only shows the full token once.

## 4. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
```

## 5. Install release tooling

```bash
python3 -m pip install --upgrade build twine
```

## 6. Regenerate the packaged corpus data

Run the build script so the JSON bundled in the wheel matches the spreadsheet:

```bash
python3 scripts/build_corpus.py
```

This reads `korpus_clean_final.xlsx` and writes:

```text
src/banyumasan_corpus/data/corpus.json
```

## 7. Run the test suite

```bash
python3 -m unittest discover -s tests -v
```

If the tests fail, fix the issue before building a release.

## 8. Build the distribution files

If you want a clean rebuild, remove any old `dist/`, `build/`, and
`*.egg-info/` directories first.

Then build both the source distribution and the wheel:

```bash
python3 -m build
```

This creates artifacts under `dist/`.

## 9. Validate the package metadata and README

```bash
python3 -m twine check dist/*
```

This checks whether the built distributions have valid metadata and whether the
Markdown README renders in a PyPI-compatible way.

## 10. Upload to TestPyPI first

Export your TestPyPI token and upload the package:

```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD='pypi-your-testpypi-token'
python3 -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*
```

Notes:

- keep the `pypi-` prefix in the token value,
- `__token__` is the username when using API tokens,
- `https://test.pypi.org/legacy/` is the upload endpoint to use with Twine.

## 11. Smoke-test the TestPyPI release

Create a fresh environment and install from TestPyPI:

```bash
python3 -m venv /tmp/banyumasan-corpus-test
source /tmp/banyumasan-corpus-test/bin/activate
python3 -m pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  banyumasan-corpus
python3 - <<'PY'
from banyumasan_corpus import find_ngapak, load_entries

print(len(load_entries()))
print(find_ngapak("dhuwur"))
PY
deactivate
```

Confirm that:

- the package installs cleanly,
- `load_entries()` returns `2000`,
- a sample lookup such as `find_ngapak("dhuwur")` works.

## 12. Upload to production PyPI

Once TestPyPI looks correct, switch to your real PyPI token:

```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD='pypi-your-production-pypi-token'
python3 -m twine upload dist/*
```

After a successful upload, verify the package page:

```text
https://pypi.org/project/banyumasan-corpus/
```

Then test a real install:

```bash
python3 -m pip install banyumasan-corpus
```

## 13. Tag the release

If you are using Git, create a matching tag after the upload succeeds:

```bash
git tag v0.1.0
git push origin v0.1.0
```

For later releases:

1. update the version in `pyproject.toml`,
2. rebuild the corpus JSON if the spreadsheet changed,
3. rerun tests,
4. rebuild `dist/*`,
5. upload the new version.

PyPI requires every uploaded release version to be unique. You cannot overwrite
an existing release by uploading the same version again.

## Optional future improvement: Trusted Publishing

This project is currently documented for token-based uploads because it is the
simplest manual workflow.

If you later move releases into GitHub Actions, PyPI Trusted Publishing is worth
considering so the workflow can mint short-lived tokens instead of storing a
long-lived API token in CI.

Official references:

- Python Packaging User Guide:
  `https://packaging.python.org/en/latest/guides/distributing-packages-using-setuptools/`
- Using TestPyPI:
  `https://packaging.python.org/en/latest/guides/using-testpypi/`
- PyPI Trusted Publishers:
  `https://docs.pypi.org/trusted-publishers/using-a-publisher/`
