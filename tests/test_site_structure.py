import re
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).parents[1]
PAGES = {
    "index.html": {"home", "tentang", "pilihan", "semester", "kontak"},
    "semester1.html": {
        "home",
        "tentang",
        "implementasi",
        "sp1",
        "sp2",
        "sp3",
        "refleksi",
        "rl-learned",
        "rl-tantangan",
        "rl-feedback",
        "dokumentasi",
        "kontak",
    },
    "semester2.html": {"home", "sppg", "ppl-mandiri", "pembelajaran-mendalam"},
    "sppg.html": {
        "identifikasi",
        "refleksi-smt1",
        "pse",
        "pmal",
        "ppl-mandiri",
        "projek-kepemimpinan",
        "inklusi",
        "refleksi-ppg",
        "seminar",
    },
    "pplm.html": {
        "orientasi",
        "terbimbing",
        "siklus-1",
        "siklus-2",
        "siklus-3",
        "siklus-4",
        "nonmengajar",
        "analisis",
        "asesmen",
        "video-terbaik",
        "laporan",
        "dokumentasi",
    },
    "karya-inovasi.html": {"ringkasan", "karya", "lk", "perangkat", "dokumentasi"},
}


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.references = []
        self.main_count = 0
        self.skip_links = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if identifier := attributes.get("id"):
            self.ids.append(identifier)
        if tag == "main":
            self.main_count += 1
        if tag == "a" and "skip-link" in attributes.get("class", "").split():
            self.skip_links.append(attributes.get("href"))
        for attribute in ("href", "src"):
            if value := attributes.get(attribute):
                self.references.append(value)


def parse_page(path):
    parser = PageParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


class SiteStructureTests(unittest.TestCase):
    def test_required_pages_assets_and_anchors_exist(self):
        self.assertTrue((ROOT / "assets/css/site.css").is_file())
        self.assertTrue((ROOT / "assets/js/site.js").is_file())
        for page_name, required_ids in PAGES.items():
            page = ROOT / page_name
            self.assertTrue(page.is_file(), page_name)
            parsed = parse_page(page)
            self.assertEqual(parsed.main_count, 1, page_name)
            self.assertEqual(parsed.skip_links, ["#main-content"], page_name)
            self.assertEqual(len(parsed.ids), len(set(parsed.ids)), page_name)
            self.assertTrue(required_ids <= set(parsed.ids), (page_name, required_ids - set(parsed.ids)))

    def test_every_relative_page_asset_and_fragment_target_resolves(self):
        for page_name in PAGES:
            page = ROOT / page_name
            parsed = parse_page(page)
            for raw_reference in parsed.references:
                reference = unquote(raw_reference)
                parsed_reference = urlparse(reference)
                if parsed_reference.scheme or reference.startswith(("//", "mailto:", "tel:")):
                    continue
                target_path = page.parent / (parsed_reference.path or page.name)
                self.assertTrue(target_path.is_file(), (page_name, raw_reference))
                if parsed_reference.fragment and target_path.suffix.lower() == ".html":
                    target_ids = set(parse_page(target_path).ids)
                    self.assertIn(parsed_reference.fragment, target_ids, (page_name, raw_reference))

    def test_no_local_video_is_committed_or_linked(self):
        local_videos = [
            path for path in ROOT.rglob("*")
            if path.is_file() and path.suffix.lower() in {".mp4", ".mov", ".avi", ".mkv"}
        ]
        self.assertEqual(local_videos, [])
        for page_name in PAGES:
            html = (ROOT / page_name).read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"(?:href|src)=[\"'][^\"']+\.(?:mp4|mov|avi|mkv)", html, re.I))

    def test_video_best_is_one_section_and_uses_drive(self):
        html = (ROOT / "pplm.html").read_text(encoding="utf-8")
        self.assertEqual(html.count('id="video-terbaik"'), 1)
        self.assertIn("1llA0EbHu-nrHDkj3j_e1VAygaQnbxAcl", html)
        self.assertIn("1LT7C3WIzp0D9rMKvdqIRuNu-6o_j7mlOj2mjcerKGGA", html)

    def test_omitted_pplm_weeks_are_not_shown(self):
        html = (ROOT / "pplm.html").read_text(encoding="utf-8")
        self.assertNotIn("25 Agustus", html)
        self.assertNotIn("1 September", html)

    def test_semester_two_media_is_grouped_and_review_media_is_not_rendered(self):
        media = ROOT / "assets/media/semester2"
        for group in ("ppl", "sppg", "lainnya", "_review"):
            self.assertTrue((media / group).is_dir(), group)
        self.assertGreater(len(list(media.rglob("*.webp"))), 0)
        rendered = "\n".join((ROOT / page).read_text(encoding="utf-8") for page in PAGES)
        self.assertNotIn("assets/media/semester2/_review/", rendered)

    def test_public_media_tree_does_not_expose_source_manifest(self):
        self.assertFalse((ROOT / "assets/media/semester2/manifest.json").exists())

    def test_legacy_fragment_allowlist_is_explicit(self):
        script = (ROOT / "assets/js/site.js").read_text(encoding="utf-8")
        for fragment in (
            "implementasi",
            "sp1",
            "sp2",
            "sp3",
            "refleksi",
            "rl-learned",
            "rl-tantangan",
            "rl-feedback",
            "dokumentasi",
        ):
            self.assertIn(f'"{fragment}"', script)
        self.assertIn("semester1.html", script)


if __name__ == "__main__":
    unittest.main()
