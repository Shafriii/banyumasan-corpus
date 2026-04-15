## Summary

- describe the corpus or code change
- explain any provenance or source updates

## Checklist

- [ ] I updated `data/corpus.csv` instead of editing packaged JSON directly
- [ ] Each new or changed corpus row has contributor and source provenance
- [ ] I ran `python3 scripts/build_corpus.py`
- [ ] I ran `python3 -m unittest discover -s tests -v`
- [ ] I included a `Signed-off-by:` line in my commit message or PR description

## Notes for maintainers

- PRs do not publish to PyPI
- TestPyPI publishes are manual
- production PyPI publishes happen only from maintainer-created `v*` tags
