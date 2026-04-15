from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = PROJECT_ROOT / "scripts" / "build_corpus.py"
SOURCE_CSV = PROJECT_ROOT / "data" / "corpus.csv"
EXPECTED_HEADERS = [
    "ngapak",
    "indonesia",
    "contributor",
    "source_type",
    "source_detail",
    "notes",
]


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_rows(path: Path, rows: list[dict[str, str]], headers: list[str] | None = None) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers or EXPECTED_HEADERS)
        writer.writeheader()
        writer.writerows(rows)


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
            result = self.run_build(SOURCE_CSV, output_path)
            self.assertEqual(result.returncode, 0, msg=result.stderr)

            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["metadata"]["source_file"], "corpus.csv")
            self.assertEqual(payload["metadata"]["entry_count"], 2000)
            self.assertEqual(payload["metadata"]["contributor_count"], 1)
            self.assertEqual(payload["metadata"]["source_types"], ["legacy_import"])
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
            mutated_csv = temp_dir_path / "broken.csv"
            lines = SOURCE_CSV.read_text(encoding="utf-8").splitlines()
            lines[0] = ",".join(
                [
                    "wrong_header",
                    "indonesia",
                    "contributor",
                    "source_type",
                    "source_detail",
                    "notes",
                ]
            )
            mutated_csv.write_text("\n".join(lines) + "\n", encoding="utf-8")

            output_path = temp_dir_path / "corpus.json"
            result = self.run_build(mutated_csv, output_path)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Unexpected CSV headers", result.stderr)

    def test_build_script_requires_contributor_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            mutated_csv = temp_dir_path / "broken.csv"
            rows = _read_rows(SOURCE_CSV)
            rows[0]["contributor"] = ""
            _write_rows(mutated_csv, rows)

            output_path = temp_dir_path / "corpus.json"
            result = self.run_build(mutated_csv, output_path)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must include a contributor value", result.stderr)

    def test_build_script_rejects_unknown_source_type(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            mutated_csv = temp_dir_path / "broken.csv"
            rows = _read_rows(SOURCE_CSV)
            rows[0]["source_type"] = "blog_post"
            _write_rows(mutated_csv, rows)

            output_path = temp_dir_path / "corpus.json"
            result = self.run_build(mutated_csv, output_path)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unsupported source_type", result.stderr)


if __name__ == "__main__":
    unittest.main()
