"""Runtime API backed by the packaged JSON corpus."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from importlib.resources import files
from typing import Any, NamedTuple

from ._models import CorpusEntry, TranslationChunk, TranslationResult

_STATS_KEYS = (
    "entry_count",
    "unique_ngapak",
    "unique_indonesia",
    "duplicate_ngapak_terms",
)
_TOKEN_RE = re.compile(r"[\w]+(?:[-'][\w]+)*", re.UNICODE)


class _Segment(NamedTuple):
    text: str
    is_token: bool


class _NormalizedToken(NamedTuple):
    original: str
    normalized: str
    segment_index: int
    source_index: int


@lru_cache(maxsize=1)
def _load_payload() -> dict[str, Any]:
    resource = files("banyumasan_corpus").joinpath("data/corpus.json")
    with resource.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def load_entries() -> tuple[CorpusEntry, ...]:
    """Load the packaged corpus as immutable dataclass entries."""
    payload = _load_payload()
    return tuple(CorpusEntry(**item) for item in payload["entries"])


@lru_cache(maxsize=1)
def _ngapak_index() -> dict[str, tuple[CorpusEntry, ...]]:
    return _build_ngapak_index(load_entries())


@lru_cache(maxsize=1)
def _phrase_index() -> dict[tuple[str, ...], tuple[CorpusEntry, ...]]:
    return _build_phrase_index(load_entries())


def _build_ngapak_index(entries: tuple[CorpusEntry, ...]) -> dict[str, tuple[CorpusEntry, ...]]:
    index: dict[str, list[CorpusEntry]] = {}
    for entry in entries:
        index.setdefault(entry.ngapak.casefold(), []).append(entry)
    return {key: tuple(value) for key, value in index.items()}


def _build_phrase_index(entries: tuple[CorpusEntry, ...]) -> dict[tuple[str, ...], tuple[CorpusEntry, ...]]:
    index: dict[tuple[str, ...], list[CorpusEntry]] = {}
    for entry in entries:
        tokens = _normalize_phrase_tokens(entry.ngapak)
        if len(tokens) <= 1:
            continue
        index.setdefault(tokens, []).append(entry)
    return {key: tuple(value) for key, value in index.items()}


def _normalize_phrase_tokens(text: str) -> tuple[str, ...]:
    return tuple(match.group(0).casefold() for match in _TOKEN_RE.finditer(text))


def _match_case(source: str, translated: str) -> str:
    if source.isupper():
        return translated.upper()
    if len(source) > 1 and source[0].isupper() and source[1:].islower():
        return translated[:1].upper() + translated[1:]
    return translated


def _split_segments(text: str) -> list[_Segment]:
    segments: list[_Segment] = []
    cursor = 0
    for match in _TOKEN_RE.finditer(text):
        start, end = match.span()
        if start > cursor:
            segments.append(_Segment(text=text[cursor:start], is_token=False))
        segments.append(_Segment(text=match.group(0), is_token=True))
        cursor = end
    if cursor < len(text):
        segments.append(_Segment(text=text[cursor:], is_token=False))
    return segments


def _collect_tokens(segments: list[_Segment]) -> list[_NormalizedToken]:
    tokens: list[_NormalizedToken] = []
    source_index = 0
    for segment_index, segment in enumerate(segments):
        if not segment.is_token:
            continue
        tokens.append(
            _NormalizedToken(
                original=segment.text,
                normalized=segment.text.casefold(),
                segment_index=segment_index,
                source_index=source_index,
            )
        )
        source_index += 1
    return tokens


def _phrase_source_text(segments: list[_Segment], tokens: list[_NormalizedToken], start: int, end: int) -> str:
    start_segment = tokens[start].segment_index
    end_segment = tokens[end].segment_index
    return "".join(segment.text for segment in segments[start_segment : end_segment + 1])


def _match_phrase(
    segments: list[_Segment],
    tokens: list[_NormalizedToken],
    token_index: int,
    phrase_index: dict[tuple[str, ...], tuple[CorpusEntry, ...]],
) -> tuple[int, tuple[CorpusEntry, ...], str] | None:
    best: tuple[int, tuple[CorpusEntry, ...], str] | None = None
    normalized_phrase: list[str] = []

    for current in range(token_index, len(tokens)):
        if current > token_index:
            prev_segment = tokens[current - 1].segment_index
            next_segment = tokens[current].segment_index
            between = "".join(segment.text for segment in segments[prev_segment + 1 : next_segment])
            if not between or not between.isspace():
                break

        normalized_phrase.append(tokens[current].normalized)
        candidates = phrase_index.get(tuple(normalized_phrase))
        if candidates:
            source_text = _phrase_source_text(segments, tokens, token_index, current)
            best = (current, candidates, source_text)

    return best


def _translate_with_entries(text: str, entries: tuple[CorpusEntry, ...]) -> TranslationResult:
    segments = _split_segments(text)
    tokens = _collect_tokens(segments)
    ngapak_index = _build_ngapak_index(entries)
    phrase_index = _build_phrase_index(entries)

    chunks: list[TranslationChunk] = []
    token_cursor = 0
    segment_cursor = 0

    while segment_cursor < len(segments):
        segment = segments[segment_cursor]
        if not segment.is_token:
            chunks.append(
                TranslationChunk(
                    source_text=segment.text,
                    translated_text=segment.text,
                    kind="delimiter",
                    token_start=None,
                    token_end=None,
                    candidates=(),
                    ambiguous=False,
                )
            )
            segment_cursor += 1
            continue

        phrase_match = _match_phrase(segments, tokens, token_cursor, phrase_index)
        if phrase_match is not None:
            phrase_end, candidates, source_text = phrase_match
            translated_text = _match_case(source_text, candidates[0].indonesia)
            chunks.append(
                TranslationChunk(
                    source_text=source_text,
                    translated_text=translated_text,
                    kind="phrase",
                    token_start=tokens[token_cursor].source_index,
                    token_end=tokens[phrase_end].source_index,
                    candidates=candidates,
                    ambiguous=len(candidates) > 1,
                )
            )
            segment_cursor = tokens[phrase_end].segment_index + 1
            token_cursor = phrase_end + 1
            continue

        token = tokens[token_cursor]
        candidates = ngapak_index.get(token.normalized, ())
        if candidates:
            chunks.append(
                TranslationChunk(
                    source_text=token.original,
                    translated_text=_match_case(token.original, candidates[0].indonesia),
                    kind="token",
                    token_start=token.source_index,
                    token_end=token.source_index,
                    candidates=candidates,
                    ambiguous=len(candidates) > 1,
                )
            )
        else:
            chunks.append(
                TranslationChunk(
                    source_text=token.original,
                    translated_text=token.original,
                    kind="untranslated",
                    token_start=token.source_index,
                    token_end=token.source_index,
                    candidates=(),
                    ambiguous=False,
                )
            )

        segment_cursor += 1
        token_cursor += 1

    translated_text = "".join(chunk.translated_text for chunk in chunks)
    return TranslationResult(
        source_text=text,
        translated_text=translated_text,
        chunks=tuple(chunks),
    )


def find_ngapak(term: str) -> list[CorpusEntry]:
    """Case-insensitive exact lookup on the Banyumasan column."""
    query = term.strip().casefold()
    if not query:
        return []
    return list(_ngapak_index().get(query, ()))


def find_indonesia(term: str, exact: bool = False) -> list[CorpusEntry]:
    """Search the Indonesian gloss column."""
    query = term.strip().casefold()
    if not query:
        return []

    if exact:
        return [entry for entry in load_entries() if entry.indonesia.casefold() == query]

    return [entry for entry in load_entries() if query in entry.indonesia.casefold()]


def translate_ngapak(text: str) -> str:
    """Translate Banyumasan text into Indonesian and return only the final string."""
    return translate_ngapak_detailed(text).translated_text


def translate_ngapak_detailed(text: str) -> TranslationResult:
    """Translate Banyumasan text with structured chunk metadata.

    The translation is deterministic and research-oriented:
    - exact case-insensitive matching only,
    - greedy longest phrase match before token fallback,
    - first corpus meaning wins for the final string,
    - all candidate corpus rows are preserved in chunk metadata,
    - punctuation and whitespace are preserved.
    """

    if not text:
        return TranslationResult(source_text=text, translated_text=text, chunks=())

    return _translate_with_entries(text, load_entries())


def stats() -> dict[str, int]:
    """Return core corpus statistics derived at build time."""
    metadata = _load_payload()["metadata"]
    return {key: int(metadata[key]) for key in _STATS_KEYS}
