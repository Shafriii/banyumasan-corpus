"""Public API for the banyumasan-corpus package."""

from ._api import (
    find_indonesia,
    find_ngapak,
    load_entries,
    stats,
    translate_ngapak,
    translate_ngapak_detailed,
)
from ._models import CorpusEntry, TranslationChunk, TranslationResult

__all__ = [
    "CorpusEntry",
    "TranslationChunk",
    "TranslationResult",
    "find_indonesia",
    "find_ngapak",
    "load_entries",
    "stats",
    "translate_ngapak",
    "translate_ngapak_detailed",
]
