#!/usr/bin/env python3
"""Convert the source XLSX workbook into packaged JSON using only the stdlib."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET
from zipfile import ZipFile

WORKBOOK_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {
    "main": WORKBOOK_NS,
    "rel": REL_NS,
    "pkgrel": PKG_REL_NS,
}
EXPECTED_HEADERS = ("ngapak", "indonesia")
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = REPO_ROOT / "korpus_clean_final.xlsx"
DEFAULT_OUTPUT = REPO_ROOT / "src" / "banyumasan_corpus" / "data" / "corpus.json"


def _column_index(reference: str) -> int:
    letters = "".join(char for char in reference if char.isalpha())
    index = 0
    for char in letters:
        index = index * 26 + (ord(char.upper()) - 64)
    return index - 1


def _read_shared_strings(archive: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []

    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    shared_strings: list[str] = []
    for item in root:
        text = "".join(node.text or "" for node in item.iter(f"{{{WORKBOOK_NS}}}t"))
        shared_strings.append(text)
    return shared_strings


def _resolve_sheet_path(archive: ZipFile) -> tuple[str, str]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    sheets = workbook.find("main:sheets", NS)
    if sheets is None or len(sheets) != 1:
        count = 0 if sheets is None else len(sheets)
        raise ValueError(f"Expected exactly one worksheet, found {count}.")

    sheet = sheets[0]
    sheet_name = sheet.attrib["name"]
    relationship_id = sheet.attrib[f"{{{REL_NS}}}id"]

    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    target = None
    for rel in rels:
        if rel.attrib.get("Id") == relationship_id:
            target = rel.attrib["Target"]
            break
    if target is None:
        raise ValueError(f"Worksheet relationship {relationship_id!r} could not be resolved.")

    if target.startswith("/"):
        target = target.lstrip("/")
    elif not target.startswith("xl/"):
        target = f"xl/{target}"

    return sheet_name, target


def _cell_text(cell: ET.Element, shared_strings: list[str]) -> str | None:
    cell_type = cell.attrib.get("t")
    value = cell.find("main:v", NS)
    if value is not None:
        raw = value.text or ""
        if cell_type == "s":
            return shared_strings[int(raw)]
        return raw

    inline = cell.find("main:is", NS)
    if inline is not None:
        return "".join(node.text or "" for node in inline.iter(f"{{{WORKBOOK_NS}}}t"))
    return None


def _iter_sheet_rows(archive: ZipFile, sheet_path: str, shared_strings: list[str]) -> Iterable[dict[int, str]]:
    worksheet = ET.fromstring(archive.read(sheet_path))
    sheet_data = worksheet.find("main:sheetData", NS)
    if sheet_data is None:
        raise ValueError("Worksheet does not contain any sheetData rows.")

    for row in sheet_data:
        cells: dict[int, str] = {}
        for cell in row.findall("main:c", NS):
            value = _cell_text(cell, shared_strings)
            if value is None:
                continue
            cells[_column_index(cell.attrib.get("r", ""))] = value
        if cells:
            yield cells


def build_payload(source: Path) -> dict[str, object]:
    with ZipFile(source) as archive:
        shared_strings = _read_shared_strings(archive)
        sheet_name, sheet_path = _resolve_sheet_path(archive)
        rows = list(_iter_sheet_rows(archive, sheet_path, shared_strings))

    if not rows:
        raise ValueError("Workbook does not contain any non-empty rows.")

    header_row = rows[0]
    if set(header_row) != {0, 1}:
        raise ValueError(
            f"Expected exactly two header columns in A and B, found columns {sorted(header_row)}."
        )

    headers = (header_row[0].strip(), header_row[1].strip())
    if headers != EXPECTED_HEADERS:
        raise ValueError(
            "Unexpected workbook headers. "
            f"Expected {EXPECTED_HEADERS!r}, found {headers!r}."
        )

    entries: list[dict[str, str]] = []
    for row_number, row in enumerate(rows[1:], start=2):
        if set(row) != {0, 1}:
            raise ValueError(
                f"Row {row_number} must contain exactly two populated columns in A and B."
            )
        ngapak = row[0].strip()
        indonesia = row[1].strip()
        if not ngapak or not indonesia:
            raise ValueError(f"Row {row_number} contains an empty value.")
        entries.append({"ngapak": ngapak, "indonesia": indonesia})

    ngapak_counts = Counter(entry["ngapak"] for entry in entries)
    payload: dict[str, object] = {
        "metadata": {
            "source_file": source.name,
            "sheet_name": sheet_name,
            "entry_count": len(entries),
            "unique_ngapak": len(ngapak_counts),
            "unique_indonesia": len({entry["indonesia"] for entry in entries}),
            "duplicate_ngapak_terms": sum(1 for count in ngapak_counts.values() if count > 1),
        },
        "entries": entries,
    }
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert the Banyumasan corpus workbook into packaged JSON."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Path to the source workbook. Default: {DEFAULT_INPUT}",
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

    print(
        f"Wrote {payload['metadata']['entry_count']} entries to {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
