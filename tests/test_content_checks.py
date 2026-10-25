import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "check-content.py"


class ContentCheckTests(unittest.TestCase):
    def run_check(self, source, target, migrations=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "source.html"
            target_path = root / "target.html"
            source_path.write_text(source, encoding="utf-8")
            target_path.write_text(target, encoding="utf-8")
            command = [
                sys.executable,
                str(SCRIPT),
                "--source",
                str(source_path),
                "--target",
                str(target_path),
            ]
            if migrations is not None:
                migration_path = root / "migrations.json"
                migration_path.write_text(json.dumps(migrations), encoding="utf-8")
                command.extend(["--migrations", str(migration_path)])
            return subprocess.run(command, capture_output=True, text=True)

    def test_reports_missing_semester_one_content(self):
        result = self.run_check(
            "<main><h1>Semester 1</h1><p>Refleksi penting.</p></main>",
            "<main><h1>Semester 1</h1></main>",
        )

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("missing content", result.stdout)

    def test_external_href_change_requires_explicit_migration(self):
        source = '<main><a href="https://old.example/bukti">Buka bukti</a></main>'
        target = '<main><a href="https://new.example/bukti">Buka bukti</a></main>'

        without_migration = self.run_check(source, target)
        with_migration = self.run_check(
            source,
            target,
            {"https://old.example/bukti": "https://new.example/bukti"},
        )

        self.assertEqual(without_migration.returncode, 1, without_migration.stderr)
        self.assertIn("external href changed", without_migration.stdout)
        self.assertEqual(with_migration.returncode, 0, with_migration.stdout)

    def test_explicit_migration_can_replace_external_href_with_relative_href(self):
        result = self.run_check(
            '<main><a href="https://old.example/bukti">Buka bukti</a></main>',
            '<main><a href="bukti.html">Buka bukti</a></main>',
            {"https://old.example/bukti": "bukti.html"},
        )

        self.assertEqual(result.returncode, 0, result.stdout)

    def test_reports_swapped_link_destinations(self):
        result = self.run_check(
            '<main><a href="https://example.com/a">Bukti A</a>'
            '<a href="https://example.com/b">Bukti B</a></main>',
            '<main><a href="https://example.com/b">Bukti A</a>'
            '<a href="https://example.com/a">Bukti B</a></main>',
        )

        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("link context changed", result.stdout)

    def test_reports_swapped_image_and_caption_pairs(self):
        result = self.run_check(
            '<main><a href="detail-a.html"><img src="a.jpg" alt="Foto A"></a>'
            '<a href="detail-b.html"><img src="b.jpg" alt="Foto B"></a></main>',
            '<main><a href="detail-a.html"><img src="b.jpg" alt="Foto B"></a>'
            '<a href="detail-b.html"><img src="a.jpg" alt="Foto A"></a></main>',
        )

        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("image context changed", result.stdout)

    def test_reports_content_moved_between_anchored_panels(self):
        result = self.run_check(
            '<main><section id="sp1"><p>Isi satu.</p></section>'
            '<section id="sp2"><p>Isi dua.</p></section></main>',
            '<main><section id="sp1"><p>Isi dua.</p></section>'
            '<section id="sp2"><p>Isi satu.</p></section></main>',
        )

        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("anchored content changed", result.stdout)

    def test_inline_markup_does_not_change_rendered_content(self):
        result = self.run_check(
            "<main><p>Refleksi <em>penting</em>.</p></main>",
            "<main><p>Refleksi penting.</p></main>",
        )

        self.assertEqual(result.returncode, 0, result.stdout)

    def test_reports_duplicate_anchor_or_id(self):
        result = self.run_check(
            '<main><section id="sp1"></section></main>',
            '<main><section id="sp1"></section><div id="sp1"></div></main>',
        )

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("duplicate anchor/id", result.stdout)

    def test_reports_removed_list_structure(self):
        result = self.run_check(
            "<main><ul><li>Refleksi</li></ul></main>",
            "<main><div><li>Refleksi</li></div></main>",
        )

        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("content structure changed", result.stdout)

    def test_identical_document_reports_preserved_counts(self):
        document = (
            '<main id="home"><h1>Semester 1</h1><p>Isi.</p>'
            '<a href="https://example.com/bukti">Bukti</a>'
            '<img src="img/bukti.jpg" alt="Bukti"></main>'
        )

        result = self.run_check(document, document)

        self.assertEqual(result.returncode, 0, result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(
            report["preserved"],
            {
                "anchor_ids": 1,
                "content_blocks": 2,
                "external_hrefs": 1,
                "images": 1,
                "links": 1,
                "text_segments": 3,
            },
        )

    def test_baseline_sha_uses_git_line_ending_normalization(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.html"
            target = root / "target.html"
            baseline = root / "baseline.json"
            source.write_bytes(b"<p>Isi</p>\r\n")
            target.write_bytes(b"<p>Isi</p>\r\n")
            baseline.write_text(
                json.dumps(
                    {
                        "pages": [
                            {
                                "name": "source.html",
                                "sha": "65bbe68b069b279a40a039a10a0d7d88ef781cf2",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--source",
                    str(source),
                    "--target",
                    str(target),
                    "--baseline",
                    str(baseline),
                ],
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 0, result.stdout)


if __name__ == "__main__":
    unittest.main()
