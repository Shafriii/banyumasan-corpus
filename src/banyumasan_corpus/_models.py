"""Typed models for corpus entries and translation results."""

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
