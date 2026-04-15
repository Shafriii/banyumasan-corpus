from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = PROJECT_ROOT / "scripts" / "build_corpus.py"
SOURCE_XLSX = PROJECT_ROOT / "korpus_clean_final.xlsx"
WORKBOOK_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"main": WORKBOOK_NS, "rel": REL_NS}


def _load_shared_strings(path: Path) -> tuple[ET.Element, list[str], int]:
    with ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rel_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}
        sheet = workbook.find("main:sheets", NS)[0]
        sheet_target = rel_map[sheet.attrib[f"{{{REL_NS}}}id"]]
        if not sheet_target.startswith("xl/"):
            sheet_target = f"xl/{sheet_target}"
        worksheet = ET.fromstring(archive.read(sheet_target))
        first_row = worksheet.find("main:sheetData", NS)[0]
        first_cell = first_row.find("main:c", NS)
        shared_index = int(first_cell.find("main:v", NS).text)

        shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        values = [
            "".join(node.text or "" for node in item.iter(f"{{{WORKBOOK_NS}}}t"))
            for item in shared_root
        ]
        return shared_root, values, shared_index


def _rewrite_header(path: Path, new_header: str) -> None:
    shared_root, _, shared_index = _load_shared_strings(path)
    item = shared_root[shared_index]
    text_node = next(item.iter(f"{{{WORKBOOK_NS}}}t"))
    text_node.text = new_header

    with tempfile.NamedTemporaryFile(delete=False) as temp_handle:
        temp_path = Path(temp_handle.name)

    try:
        with ZipFile(path) as source, ZipFile(temp_path, "w") as target:
            for info in source.infolist():
                data = source.read(info.filename)
                if info.filename == "xl/sharedStrings.xml":
                    data = ET.tostring(shared_root, encoding="utf-8", xml_declaration=True)
                target.writestr(info, data)
        shutil.move(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


class BuildScriptTests(unittest.TestCase):
    def run_build(self, input_path: Path, output_path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(BUILD_SCRIPT),
                "--input",
                str(input_path),
                "--output",
                str(output_path),
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_build_script_generates_expected_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "corpus.json"
            result = self.run_build(SOURCE_XLSX, output_path)
            self.assertEqual(result.returncode, 0, msg=result.stderr)

            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["metadata"]["entry_count"], 2000)
            self.assertEqual(payload["metadata"]["sheet_name"], "Sheet1")
            self.assertEqual(payload["entries"][0], {"ngapak": "abab", "indonesia": "tiupan napas"})
            self.assertEqual(payload["entries"][-1], {"ngapak": "egot", "indonesia": "kaku"})
            self.assertIn(
                {"ngapak": "golèk", "indonesia": "mencari"},
                payload["entries"],
            )
            self.assertEqual(
                [entry["indonesia"] for entry in payload["entries"] if entry["ngapak"] == "dhuwur"],
                ["tinggi", "atas"],
            )

    def test_build_script_rejects_unexpected_headers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            mutated_xlsx = temp_dir_path / "broken.xlsx"
            shutil.copy2(SOURCE_XLSX, mutated_xlsx)
            _rewrite_header(mutated_xlsx, "wrong_header")

            output_path = temp_dir_path / "corpus.json"
            result = self.run_build(mutated_xlsx, output_path)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Unexpected workbook headers", result.stderr)


if __name__ == "__main__":
    unittest.main()
