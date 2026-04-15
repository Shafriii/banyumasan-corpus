#!/usr/bin/env python3
"""Convert the canonical CSV corpus into packaged JSON using only the stdlib."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

EXPECTED_HEADERS = (
    "ngapak",
    "indonesia",
    "contributor",
    "source_type",
    "source_detail",
    "notes",
)
ALLOWED_SOURCE_TYPES = {
    "legacy_import",
    "original_submission",
    "published_reference",
    "field_collection",
}
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = REPO_ROOT / "data" / "corpus.csv"
DEFAULT_OUTPUT = REPO_ROOT / "src" / "banyumasan_corpus" / "data" / "corpus.json"


def _normalize_row(row_number: int, row: dict[str, str]) -> dict[str, str]:
    normalized = {key: (row.get(key) or "").strip() for key in EXPECTED_HEADERS}

    if not normalized["ngapak"] or not normalized["indonesia"]:
        raise ValueError(f"Row {row_number} must include non-empty ngapak and indonesia values.")

    if not normalized["contributor"]:
        raise ValueError(f"Row {row_number} must include a contributor value.")

    if normalized["source_type"] not in ALLOWED_SOURCE_TYPES:
        allowed = ", ".join(sorted(ALLOWED_SOURCE_TYPES))
        raise ValueError(
            f"Row {row_number} has unsupported source_type {normalized['source_type']!r}. "
            f"Expected one of: {allowed}."
        )

    if not normalized["source_detail"]:
        raise ValueError(f"Row {row_number} must include a source_detail value.")

    return normalized


def build_payload(source: Path) -> dict[str, object]:
    with source.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = tuple(reader.fieldnames or ())
        if headers != EXPECTED_HEADERS:
            raise ValueError(
                "Unexpected CSV headers. "
                f"Expected {EXPECTED_HEADERS!r}, found {headers!r}."
            )

        rows = [_normalize_row(row_number, row) for row_number, row in enumerate(reader, start=2)]

    if not rows:
        raise ValueError("Corpus CSV does not contain any data rows.")

    entries = [
        {
            "ngapak": row["ngapak"],
            "indonesia": row["indonesia"],
        }
        for row in rows
    ]
    ngapak_counts = Counter(entry["ngapak"] for entry in entries)
    payload: dict[str, object] = {
        "metadata": {
            "source_file": source.name,
            "entry_count": len(entries),
            "unique_ngapak": len(ngapak_counts),
            "unique_indonesia": len({entry["indonesia"] for entry in entries}),
            "duplicate_ngapak_terms": sum(1 for count in ngapak_counts.values() if count > 1),
            "contributor_count": len({row["contributor"] for row in rows}),
            "source_types": sorted({row["source_type"] for row in rows}),
        },
        "entries": entries,
    }
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert the Banyumasan corpus CSV into packaged JSON."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Path to the canonical corpus CSV. Default: {DEFAULT_INPUT}",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Path to the generated JSON file. Default: {DEFAULT_OUTPUT}",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation level. Default: 2",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_payload(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=args.indent)
        handle.write("\n")

    print(f"Wrote {payload['metadata']['entry_count']} entries to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
