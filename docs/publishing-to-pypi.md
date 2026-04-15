# Publishing `banyumasan-corpus` to PyPI

This repository uses a maintainer-controlled release flow:

- pull requests run build and test checks only,
- pushes to `main` run build and test checks only,
- TestPyPI publishes happen only through a manual GitHub Actions run,
- production PyPI publishes happen only from `v*` tags.

The workflow lives in:

```text
.github/workflows/release.yml
```

## 1. Fill in the package metadata

Before publishing, update the placeholders in `pyproject.toml` and `LICENSE`:

- replace `YOUR NAME`
- replace `your.email@example.com`
- replace the GitHub placeholder URLs

Also confirm that the package version is correct. The initial version in this
project is `0.1.0`.

## 2. Add the release workflow to GitHub

Commit and push:

```text
.github/workflows/release.yml
```

The workflow is configured so that:

- `pull_request` events build and test the project,
- pushes to `main` build and test the project,
- `workflow_dispatch` can optionally publish to TestPyPI,
- tag pushes matching `v*` publish to PyPI,
- only the publish jobs receive `id-token: write`.

## 3. Create the GitHub environments

In the GitHub repository settings, create these environments:

- `testpypi`
- `pypi`

Require manual approval for the `pypi` environment. That keeps production
releases maintainer-controlled even after a tag is pushed.

You can also require manual approval for `testpypi` if you want the same gate
on pre-release uploads, but it is optional.

## 4. Create PyPI and TestPyPI accounts

You need separate accounts for:

- PyPI: `https://pypi.org/account/register/`
- TestPyPI: `https://test.pypi.org/account/register/`

## 5. Configure trusted publishers

Use PyPI Trusted Publishing rather than storing API tokens in GitHub.

### PyPI

Go to:

```text
https://pypi.org/manage/account/publishing/
```

Register a GitHub publisher with:

- PyPI project name: `banyumasan-corpus`
- owner or organization: your GitHub owner
- repository name: `banyumasan-corpus`
- workflow filename: `release.yml`
- environment name: `pypi`

### TestPyPI

Go to:

```text
https://test.pypi.org/manage/account/publishing/
```

Register a GitHub publisher with:

- PyPI project name: `banyumasan-corpus`
- owner or organization: your GitHub owner
- repository name: `banyumasan-corpus`
- workflow filename: `release.yml`
- environment name: `testpypi`

If the project does not exist yet, create pending publishers in both services.

## 6. Run the local pre-release checks

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip build twine
python3 scripts/build_corpus.py
python3 -m unittest discover -s tests -v
python3 -m build
python3 -m twine check dist/*
```

This verifies that:

- `data/corpus.csv` is valid,
- the packaged JSON is up to date,
- the tests pass,
- both the wheel and sdist build cleanly,
- the metadata and README render cleanly for PyPI.

## 7. Release TestPyPI manually

After the release candidate is merged to `main`, go to the GitHub Actions UI
and run the `CI and Release` workflow manually on the desired ref with:

- `publish_target=testpypi`

That manual run will:

1. rebuild `src/banyumasan_corpus/data/corpus.json`,
2. fail if the generated JSON differs from what is committed,
3. run the test suite,
4. build `dist/*`,
5. upload the distributions to TestPyPI through Trusted Publishing.

Then smoke-test the TestPyPI release in a fresh environment:

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

## 8. Release production PyPI from a maintainer tag

When TestPyPI looks correct, create and push a version tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

That triggers the PyPI publish job, which waits for approval on the `pypi`
environment and then uploads through Trusted Publishing.

After the upload succeeds, verify the package page:

```text
https://pypi.org/project/banyumasan-corpus/
```

Then test a real install:

```bash
python3 -m pip install banyumasan-corpus
```

## 9. Release checklist for later versions

For later releases:

1. update the version in `pyproject.toml`,
2. update `data/corpus.csv` if the dataset changed,
3. rebuild the packaged JSON,
4. rerun tests and build checks locally,
5. merge the release candidate to `main`,
6. manually publish to TestPyPI,
7. push the matching `v*` tag for PyPI.

PyPI requires every uploaded release version to be unique. You cannot overwrite
an existing release by uploading the same version again.

## Security notes

- do not add `PYPI_API_TOKEN` or `TEST_PYPI_API_TOKEN` repository secrets for
  this workflow,
- do not grant publish permissions to PR jobs,
- keep PyPI publishing tag-based and maintainer-approved,
- review tag protection so only maintainers can create release tags that match
  `v*`.

Official references:

- Python Packaging User Guide:
  `https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/`
- PyPI Trusted Publishers:
  `https://docs.pypi.org/trusted-publishers/using-a-publisher/`
- PyPI pending publishers:
  `https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/`
