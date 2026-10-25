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

    def test_home_restores_rich_contact_and_footer(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        for expected in (
            "contact-home-grid",
            'class="contact-card"',
            'class="footer-grid"',
            "Mari Terhubung",
            "Bersama Saya",
            "SMK Negeri 1 Surabaya, Jawa Timur",
            "Senin–Jumat, 07.00–16.00 WIB",
            'href="mailto:peserta.48808@ppg.belajar.id"',
            'href="https://wa.me/6281329792820"',
            'href="https://instagram.com/argya_353"',
        ):
            self.assertIn(expected, html)

    def test_identity_is_consolidated_on_home(self):
        home = (ROOT / "index.html").read_text(encoding="utf-8")
        semester_one = (ROOT / "semester1.html").read_text(encoding="utf-8")
        for expected in (
            "Nama saya Putranto Argya Kuncara Jati",
            "Memayu Hayuning Bawana",
            "NIM 2500103916524001",
            "img/gwehj_formal.jpg",
        ):
            self.assertIn(expected, home)
            self.assertNotIn(expected, semester_one)

    def test_semester_one_uses_redesigned_shell_and_cleaned_photos(self):
        html = (ROOT / "semester1.html").read_text(encoding="utf-8")
        self.assertIn('class="semester-one-page"', html)
        self.assertIn('href="assets/css/site.css"', html)
        self.assertIn('src="assets/js/site.js"', html)
        self.assertNotIn('id="nav"', html)
        clean_photos = (
            "assets/img/semester1/lokasi-ppl-bersih.webp",
            "assets/img/semester1/siklus-1-bersih.webp",
            "assets/img/semester1/siklus-2-bersih.webp",
            "assets/img/semester1/siklus-3-bersih.webp",
        )
        old_photos = (
            "img/dokumentasi/penyerahan_compressed.jpg",
            "img/dokumentasi/siklus1_compressed.jpg",
            "img/dokumentasi/siklus2_compressed.jpg",
            "img/dokumentasi/siklus3_compressed.jpg",
        )
        for photo in clean_photos:
            self.assertIn(photo, html)
            self.assertTrue((ROOT / photo).is_file())
        for photo in old_photos:
            self.assertNotIn(photo, html)

    def test_semester_one_gallery_uses_generated_thumbnails_and_keeps_targets(self):
        html = (ROOT / "semester1.html").read_text(encoding="utf-8")
        self.assertEqual(html.count("data-gallery-item"), 13)
        self.assertIn("assets/img/semester1/galeri-thumbnail-sprite.webp", html)
        for target in (
            "https://www.canva.com/design/DAHI2Mb3oIM/xeHDZKVV_-TH0JW_sUxQZw/edit",
            "img/dokumentasi/pendampingan_s1_compressed.jpg",
            "img/dokumentasi/presentasi_compressed.jpg",
            "https://drive.google.com/drive/folders/1t8cus5SVm0W649w4E3ivZWZCw6FMNh9L?usp=sharing",
            "https://drive.google.com/drive/folders/1MupMB2sFIP3u-dSLq7MGQhjB5CpD1u-_?usp=sharing",
            "img/dokumentasi/pendampingan_s3.jpg",
            "https://drive.google.com/drive/folders/1jzo7-CmldRK4OWIXUNcy_cERA9lFewe-?usp=drive_link",
            "https://drive.google.com/file/d/1h5-oXSsOpTZn_6Rt7xDOgQE8UM-4cifs/view?usp=drive_link",
            "img/dokumentasi/pendampingan_s2_compressed.jpg",
            "https://drive.google.com/drive/folders/1h_FwnzoiFgSb7hc30n90nlmWz0_9Imi2?usp=sharing",
            "https://docs.google.com/presentation/d/17M3nN8CrHjBP7FNGQYss4aVGO8YBZLiM8QOfDkVVyGQ/edit?usp=drive_link",
            "https://docs.google.com/presentation/d/1Q1NvHqGdhFs_OFx1gGEWUSEGIBDgjdlVk6Mk0I0s6eI/edit?usp=drive_link",
            "https://docs.google.com/presentation/d/1WkEibBgKK9MRgSEJMZFOBQK9uX9GlPnLIpn7nqnDaOk/edit?usp=drive_link",
        ):
            self.assertIn(f'href="{target}"', html)

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
