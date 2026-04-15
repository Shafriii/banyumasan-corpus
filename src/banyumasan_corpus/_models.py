"""Typed models for corpus entries, translation results, and research metrics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class CorpusEntry:
    """A single Banyumasan-to-Indonesian row from the corpus."""

    ngapak: str
    indonesia: str


ChunkKind = Literal["phrase", "token", "untranslated", "delimiter"]


@dataclass(frozen=True, slots=True)
class TranslationChunk:
    """A translated span or preserved delimiter from the source text."""

    source_text: str
    translated_text: str
    kind: ChunkKind
    token_start: int | None
    token_end: int | None
    candidates: tuple[CorpusEntry, ...]
    ambiguous: bool


@dataclass(frozen=True, slots=True)
class TranslationResult:
    """Structured output for reproducible text translation experiments."""

    source_text: str
    translated_text: str
    chunks: tuple[TranslationChunk, ...]


@dataclass(frozen=True, slots=True)
class TranslationMetrics:
    """Intrinsic metrics derived from structured translation output."""

    text_count: int
    source_token_count: int
    translated_token_count: int
    untranslated_token_count: int
    ambiguous_token_count: int
    phrase_chunk_count: int
    token_chunk_count: int
    untranslated_chunk_count: int
    delimiter_chunk_count: int
    coverage_ratio: float
    ambiguity_ratio: float


@dataclass(frozen=True, slots=True)
class TranslationBatchResult:
    """Batch translation output plus aggregate intrinsic metrics."""

    results: tuple[TranslationResult, ...]
    metrics: TranslationMetrics
