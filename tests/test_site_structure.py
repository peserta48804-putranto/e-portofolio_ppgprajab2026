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
        "video-terbaik",
        "laporan",
        "dokumentasi",
    },
    "karya-inovasi.html": {
        "ringkasan",
        "identitas",
        "gagasan-riset",
        "rancangan",
        "evaluasi",
        "dokumen",
    },
}


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.references = []
        self.main_count = 0
        self.skip_links = []
        self.site_nav_fragments = []
        self.in_site_nav = False

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "nav" and "site-nav" in attributes.get("class", "").split():
            self.in_site_nav = True
        if identifier := attributes.get("id"):
            self.ids.append(identifier)
        if tag == "main":
            self.main_count += 1
        if tag == "a" and "skip-link" in attributes.get("class", "").split():
            self.skip_links.append(attributes.get("href"))
        if self.in_site_nav and tag == "a" and attributes.get("href", "").startswith("#"):
            self.site_nav_fragments.append(attributes["href"])
        for attribute in ("href", "src"):
            if value := attributes.get(attribute):
                self.references.append(value)

    def handle_endtag(self, tag):
        if tag == "nav" and self.in_site_nav:
            self.in_site_nav = False


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

    def test_shared_script_realigns_fragment_after_web_fonts_settle(self):
        script = (ROOT / "assets/js/site.js").read_text(encoding="utf-8")

        self.assertIn(
            'document.querySelector(":target")?.scrollIntoView({ behavior: "instant" })',
            script,
        )
        self.assertIn("document.fonts.ready.then(realignFragment)", script)

    def test_every_sidebar_exposes_sections_for_scroll_tracking(self):
        for page_name in PAGES:
            parsed = parse_page(ROOT / page_name)
            self.assertGreaterEqual(len(parsed.site_nav_fragments), 2, page_name)
            for href in parsed.site_nav_fragments:
                self.assertIn(href[1:], parsed.ids, (page_name, href))

    def test_shared_sidebar_scroll_spy_listens_to_viewport_changes(self):
        script = (ROOT / "assets/js/site.js").read_text(encoding="utf-8")

        self.assertIn('window.addEventListener("scroll", schedule', script)
        self.assertIn('window.addEventListener("resize", schedule', script)
        self.assertIn("requestAnimationFrame(updateCurrentSection)", script)
        self.assertNotIn("currentLink.scrollIntoView", script)
        self.assertIn('nav.closest(".site-sidebar")', script)
        self.assertIn("sidebar.scrollTop", script)
        self.assertIn("Math.min(window.innerHeight * 0.2, 96)", script)
        self.assertIn("window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 2", script)

    def test_sidebar_wheel_keeps_scrolling_the_page_after_navigation(self):
        script = (ROOT / "assets/js/site.js").read_text(encoding="utf-8")

        self.assertIn('sidebar.addEventListener("wheel"', script)
        self.assertIn(
            'window.scrollBy({ top: event.deltaY, behavior: "instant" })', script
        )
        self.assertIn("event.preventDefault()", script)
        self.assertIn('{ passive: false }', script)

    def test_pplm_uses_compact_sections_and_aligned_documentation_cards(self):
        html = (ROOT / "pplm.html").read_text(encoding="utf-8")
        css = (ROOT / "assets/css/site.css").read_text(encoding="utf-8")

        self.assertIn('<body class="pplm-page" data-reveal-page>', html)
        self.assertIn(".pplm-page .section { padding-block: 3rem; }", css)
        self.assertIn(
            ".pplm-page .section > .page-width > .lead { margin: 1rem 0 1.5rem; }",
            css,
        )
        self.assertIn(
            "#terbimbing .photo-grid, #siklus-2 .photo-grid, #siklus-4 .photo-grid { grid-template-columns: repeat(2,minmax(0,1fr)); }",
            css,
        )
        self.assertIn(".pplm-page #dokumentasi .portal { min-height: 112px; align-items: center; }", css)
        self.assertIn(".pplm-page #dokumentasi .portal-number { flex: 0 0 2.5rem; }", css)

    def test_pplm_uses_compact_cycle_grid_and_prominent_video_resources(self):
        html = (ROOT / "pplm.html").read_text(encoding="utf-8")
        css = (ROOT / "assets/css/site.css").read_text(encoding="utf-8")

        self.assertEqual(html.count("cycle-summary-card"), 4)
        self.assertIn('class="cycle-summary-grid"', html)
        self.assertIn(
            ".cycle-summary-grid { display: grid; grid-template-columns: repeat(2,minmax(0,1fr));",
            css,
        )
        self.assertEqual(html.count('class="document-link video-resource'), 2)
        self.assertIn("video-feature-grid", html)
        self.assertIn(".video-feature-grid { display: grid;", css)
        self.assertIn("Tonton video pembelajaran", html)
        self.assertIn("Baca analisis pembelajaran", html)

    def test_pplm_exposes_lms_eportfolio_two_components(self):
        html = (ROOT / "pplm.html").read_text(encoding="utf-8")
        section_match = re.search(
            r'<section id="eportfolio-2".*?</section>', html, re.S
        )

        self.assertEqual(html.count('id="eportfolio-2"'), 1)
        self.assertIsNotNone(section_match)
        section = section_match.group(0)
        self.assertEqual(
            section.count('data-eportfolio-component="cycle"'), 4
        )
        for number in (1, 2, 3, 4):
            self.assertIn(f'href="#siklus-{number}"', section)
        self.assertEqual(
            section.count('data-eportfolio-component="video"'), 1
        )
        self.assertIn('href="#video-terbaik"', section)

        for source_id in (
            "1UtACCuiQO7W_AXsZVTzKbhulU2Oiea32",
            "1umR-6-vZLciqv3Nuvk8nKrW2xFahjXe2",
            "1q5Mbaryfyo0g0PkcCj5QG2ew6k6sLcPi",
            "1XkvZz3Rhj9vJroAele4KSJ9CylfoaGy0",
            "160yLHo5uyBKEIFz844m8U9tFpV5yKOlO",
            "13J2RW656XRuLFnq6TschhchhMKpO4EhR",
            "1g7Gok8SmELsrvTBQmswnfjaTrJsvgedt",
            "1LTnRwDcREptBlUY2OznwtLp0FER_yyOU",
            "1LT7C3WIzp0D9rMKvdqIRuNu-6o_j7mlOj2mjcerKGGA",
        ):
            self.assertEqual(html.count(source_id), 1, source_id)
        self.assertNotIn("1llA0EbHu-nrHDkj3j_e1VAygaQnbxAcl", html)
        self.assertIsNone(
            re.search(
                r'(?:href|src)=["\'][^"\']+\.(?:mp4|mov|avi|mkv)',
                html,
                re.I,
            )
        )

    def test_pplm_sidebar_fragments_follow_document_section_order(self):
        page = ROOT / "pplm.html"
        html = page.read_text(encoding="utf-8")
        fragments = parse_page(page).site_nav_fragments
        positions = [html.index(f'id="{fragment[1:]}"') for fragment in fragments]

        self.assertEqual(positions, sorted(positions))

    def test_pplm_mobile_nav_exposes_every_cycle(self):
        html = (ROOT / "pplm.html").read_text(encoding="utf-8")
        mobile_nav = re.search(
            r'<details class="mobile-nav">.*?</details>', html, re.S
        ).group(0)

        for cycle in range(1, 5):
            self.assertIn(f'href="#siklus-{cycle}"', mobile_nav)

    def test_pplm_uses_final_signed_sources_and_cycle_support_folders(self):
        html = (ROOT / "pplm.html").read_text(encoding="utf-8")

        for source_id in (
            "1ppYZKxQu2VZQAv8LeuYY5RIEyGfJhNX1",
            "1gTdemDP5aBsqgYQ17E97NNUB2nWjV-hC",
            "1x96k3oJWUWBrh3jcBWLMk3KXX_jDODtJ",
            "1S55NSAc80JNqwbZXmgsyfTDeE923jiIM",
            "160yLHo5uyBKEIFz844m8U9tFpV5yKOlO",
            "13J2RW656XRuLFnq6TschhchhMKpO4EhR",
            "1g7Gok8SmELsrvTBQmswnfjaTrJsvgedt",
            "1WaPFn7QDjtJgnMlc5WEmExLJGdiJ04-2",
            "1UtACCuiQO7W_AXsZVTzKbhulU2Oiea32",
            "1umR-6-vZLciqv3Nuvk8nKrW2xFahjXe2",
            "1q5Mbaryfyo0g0PkcCj5QG2ew6k6sLcPi",
            "1XkvZz3Rhj9vJroAele4KSJ9CylfoaGy0",
        ):
            self.assertIn(source_id, html)

        for folder_id in (
            "1YFrblZR5f_HR6fcHQTPvnJVK_6kEzH9I",
            "1WTAwKRsezmMGeN3V6uI1QtYWkpv2kdB-",
            "1NEFTn3_iBXsy8Ezsc3tX4ubekaQX29XL",
            "1OuOioMfY6zhTXwXnCpdCnHEMBR71G5CP",
            "1PrDV_ePSa0nQMGeIdOfzmsvjiZRHpyJq",
        ):
            self.assertIn(folder_id, html)
        self.assertEqual(html.count("<strong>Dokumen Pendukung</strong>"), 4)
        self.assertIn("<strong>Data Asesmen Siklus 4</strong>", html)
        self.assertIn(
            "<strong>Sorting sederhana</strong> tercantum sebagai rencana Pertemuan III dalam modul, tetapi belum terlaksana.",
            html,
        )
        self.assertNotIn("karena belum ada log pendukung", html)

        for superseded_id in (
            "1iZlZqm5rRkRJSHg-N2SZgZtthEO2UveD",
            "1MC-qmASKK9vqbFm2QwSNZ-a5FTOykMVs",
            "1udHaDEWryDkse-br6FQy1hJgO-74-Iz1",
            "1cC8tFtRVC1rdcrgJCEqSO1clvSW5xv0dJrHh_q2M82g",
            "1ynEQA4w7YYy3z51WszGYrmJ8UOa2IhMWtK5cipfldhQ",
            "1DvICG-92-IPa3cwCRNVf2m8pYxAV5LTgewGNE2URapg",
            "1OGYM6Oz0tmrA6tecjkLjTEqszRh3_C6b3C-eskKyJzU",
            "1MapSmPcFtkpIUmB_n85fyKc3KUu9nWEo",
            "1RC8XBBv8BKmei2tJUa2XzfJcqvDusX_J",
            "1_AJ-ou-W_zwLUtx3qiIGncHNBdMF1k4y",
            "1QYDbF-5gWrywcF5-zIAzYrScGfa4s94n",
            "1Ijlc3a4_zpf5p0qkVTkitQoflS0AQl6I",
            "1fQIe3WWAYL1GxuVB01Tf2oeo7qUMjYB-",
            "1On-upcmUWdLU2-JlFgfh22a1bJiUux93",
            "1KhTpbqUXmJ9jYTi8_dD29okfs_GXBk4A",
            "1-bPGkqTbo-M4Z_5WP0E-O7sX4t5SX7xd",
            "1MFlXar4dwa0qWPicIrXBwaPCdDkMyJqr",
            "1n0AxDB9gQQaqw7gnHjBMuHLqq9wbCFjg",
            "1YZGjZbUBBr_YGWdtxCVk-cXZ0PNCaYFA",
            "1MbR85fAwEVZE52cgbghGPIOrta7yGMrCeqYQIvu-ehY",
            "1HmJXW_DLGhruVu1OxPFcCoXKlwEQuV0MgQcEUxYB2Ss",
            "1hn-u0MHrl-yo2FBtb9zxwPCzDg9Heg1dV9QU5Y7J6MM",
        ):
            self.assertNotIn(superseded_id, html)
        self.assertNotIn('href="#asesmen"', html)
        self.assertNotIn('id="asesmen"', html)
        self.assertNotIn('id="analisis"', html)

        semester_two = (ROOT / "semester2.html").read_text(encoding="utf-8")
        self.assertNotIn("pplm.html#asesmen", semester_two)
        self.assertNotIn("pplm.html#analisis", semester_two)
        self.assertIn("pplm.html#siklus-4", semester_two)

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
        self.assertIn("1LTnRwDcREptBlUY2OznwtLp0FER_yyOU", html)
        self.assertNotIn("1llA0EbHu-nrHDkj3j_e1VAygaQnbxAcl", html)
        self.assertIn("1LT7C3WIzp0D9rMKvdqIRuNu-6o_j7mlOj2mjcerKGGA", html)

    def test_omitted_pplm_weeks_are_not_shown(self):
        html = (ROOT / "pplm.html").read_text(encoding="utf-8")
        self.assertNotIn("25 Agustus", html)
        self.assertNotIn("1 September", html)

    def test_home_restores_rich_contact_and_footer(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        for expected in (
            "contact-compact",
            "contact-compact-links",
            'class="footer-grid"',
            "Mari Terhubung",
            "SMK Negeri 1 Surabaya, Jawa Timur",
            "Senin–Jumat, 07.00–16.00 WIB",
            'href="mailto:peserta.48808@ppg.belajar.id"',
            'href="https://wa.me/6281329792820"',
            'href="https://instagram.com/argya_353"',
        ):
            self.assertIn(expected, html)
        self.assertNotIn('class="contact-card"', html)

    def test_checkpoint_one_makes_deep_learning_visible_from_home(self):
        home = (ROOT / "index.html").read_text(encoding="utf-8")

        self.assertIn('id="pembelajaran-mendalam"', home)
        self.assertIn("Pembelajaran Mendalam", home)
        self.assertIn('href="semester1.html#pembelajaran-mendalam"', home)
        self.assertIn('href="semester2.html#pembelajaran-mendalam"', home)

    def test_checkpoint_one_maps_deep_learning_across_three_semester_one_cycles(self):
        html = (ROOT / "semester1.html").read_text(encoding="utf-8")

        self.assertIn('id="pembelajaran-mendalam"', html)
        self.assertEqual(html.count('class="deep-learning-step"'), 3)
        for number in (1, 2, 3):
            self.assertIn(
                f'class="deep-learning-step" href="#sp{number}" onclick="showSik({number})"',
                html,
            )

    def test_checkpoint_one_uses_compact_home_portals_and_rose_gallery_transition(self):
        home = (ROOT / "index.html").read_text(encoding="utf-8")
        semester_one = (ROOT / "semester1.html").read_text(encoding="utf-8")
        css = (ROOT / "assets/css/site.css").read_text(encoding="utf-8")

        self.assertEqual(home.count('class="portal-grid home-portal-grid"'), 2)
        self.assertIn('class="semester-one-gallery rosewash"', semester_one)
        self.assertIn(".home-portal-grid .portal", css)

    def test_home_and_semester_two_use_the_shared_reveal_animation(self):
        home = (ROOT / "index.html").read_text(encoding="utf-8")
        semester_two = (ROOT / "semester2.html").read_text(encoding="utf-8")
        css = (ROOT / "assets/css/site.css").read_text(encoding="utf-8")

        self.assertGreaterEqual(home.count(" rv"), 10)
        self.assertGreaterEqual(semester_two.count(" rv"), 6)
        self.assertIn(".rv {", css)
        self.assertIn(".rv.in {", css)

    def test_semester_two_reveals_catalog_cards_individually_with_fresh_assets(self):
        html = (ROOT / "semester2.html").read_text(encoding="utf-8")
        catalog_cards = re.findall(r'<article class="([^"]*catalog-card[^"]*)"', html)

        self.assertEqual(len(catalog_cards), 12)
        self.assertTrue(all("rv" in classes.split() for classes in catalog_cards))
        self.assertIn(
            'href="assets/css/site.css?v=20261029-semester2-route-v1"', html
        )
        self.assertIn('src="assets/js/site.js?v=20261027-scrollspy-v6"', html)

    def test_semester_two_routes_group_copy_and_actions_in_a_compact_layout(self):
        html = (ROOT / "semester2.html").read_text(encoding="utf-8")
        css = (ROOT / "assets/css/site.css").read_text(encoding="utf-8")

        self.assertEqual(html.count('class="semester-route-copy"'), 2)
        self.assertIn(
            ".semester-route-copy { display: flex; align-items: center;",
            css,
        )
        self.assertIn(
            "grid-template-columns: minmax(300px,.72fr) minmax(0,1.28fr);",
            css,
        )
        self.assertIn(
            'href="assets/css/site.css?v=20261029-semester2-route-v1"',
            html,
        )

    def test_every_public_page_uses_fresh_shared_animation_assets(self):
        for page_name in PAGES:
            html = (ROOT / page_name).read_text(encoding="utf-8")
            css_version = {
                "karya-inovasi.html": "20261028-karya-v1",
                "semester2.html": "20261029-semester2-route-v1",
                "sppg.html": "20261028-sppg-summary-v1",
            }.get(page_name, "20261028-gallery-v11")
            self.assertIn(
                f'href="assets/css/site.css?v={css_version}"', html, page_name
            )
            self.assertIn(
                'src="assets/js/site.js?v=20261027-scrollspy-v6"', html, page_name
            )

    def test_detail_pages_reveal_their_main_content(self):
        for page_name in ("sppg.html", "pplm.html", "karya-inovasi.html"):
            html = (ROOT / page_name).read_text(encoding="utf-8")
            self.assertRegex(html, r"<body[^>]*\bdata-reveal-page\b[^>]*>", page_name)

        script = (ROOT / "assets/js/site.js").read_text(encoding="utf-8")
        css = (ROOT / "assets/css/site.css").read_text(encoding="utf-8")
        self.assertIn('document.querySelectorAll("[data-reveal-page]")', script)
        self.assertIn("[data-reveal-page] .detail-hero > *", css)
        self.assertIn(
            "[data-reveal-page] .section .rv.in { opacity: 1; transform: none; }",
            css,
        )
        for selector in (
            ".detail-hero > *",
            ".section-heading",
            ".document-link",
            ".timeline-card",
            ".photo-grid > a",
            ".pending",
            ".portal",
        ):
            self.assertIn(selector, script)

    def test_semester_one_gallery_intro_has_contrast_on_rose_background(self):
        css = (ROOT / "assets/css/site.css").read_text(encoding="utf-8")

        self.assertIn(
            ".semester-one-page .semester-one-gallery .body-muted { color: var(--mid); }",
            css,
        )

    def test_checkpoint_two_explains_deep_learning_across_semester_two_cycles(self):
        html = (ROOT / "semester2.html").read_text(encoding="utf-8")

        self.assertNotIn("Tautan lama dipertahankan", html)
        self.assertIn("Landasan pembelajaran", html)
        self.assertIn("Berkesadaran", html)
        self.assertIn("Bermakna", html)
        self.assertIn("Menggembirakan", html)
        self.assertEqual(html.count('class="cycle-learning-card"'), 4)
        for number in (1, 2, 3, 4):
            self.assertIn(f'href="pplm.html#siklus-{number}"', html)

    def test_checkpoint_two_uses_parallel_sppg_headings_and_rose_transitions(self):
        html = (ROOT / "sppg.html").read_text(encoding="utf-8")
        css = (ROOT / "assets/css/site.css").read_text(encoding="utf-8")

        semester_one = re.search(
            r'<section id="refleksi-smt1".*?</section>', html, re.S
        ).group(0)
        semester_two = re.search(
            r'<section id="refleksi-smt2".*?</section>', html, re.S
        ).group(0)
        self.assertRegex(semester_one, r'<p class="eyebrow">LK 2</p><h2>Refleksi Semester 1</h2>')
        self.assertRegex(semester_two, r'<p class="eyebrow">LK 2</p><h2>Refleksi Semester 2</h2>')
        self.assertIn('href="#refleksi-smt2">Refleksi Semester 2</a>', html)
        self.assertIn("Lima pengalaman belajar", semester_two)
        self.assertIn('class="section rosewash"', semester_two)
        self.assertIn(".section.rosewash", css)

    def test_section_led_pages_expose_a_default_sidebar_location(self):
        for page_name, href in (
            ("sppg.html", "#identifikasi"),
            ("pplm.html", "#orientasi"),
            ("karya-inovasi.html", "#ringkasan"),
        ):
            html = (ROOT / page_name).read_text(encoding="utf-8")
            self.assertIn(
                f'href="{href}" aria-current="location"',
                html,
                page_name,
            )

    def test_checkpoint_two_preserves_semester_two_reflection_targets(self):
        html = (ROOT / "sppg.html").read_text(encoding="utf-8")

        for identifier, target in (
            ("pse", "1VjIk3hzCOBAlyz58nOfejXIGQel2fDGi"),
            ("pmal", "1jiUpLoXD338ndZ6pDn2i62prOyjVqGZt"),
            ("ppl-mandiri", "1TGvVfWYeX6eN0MOtLMDiHeCullJz_Hj0"),
            ("projek-kepemimpinan", "1B8pt7sgV0THkIRorPOjzr-NxaYcghrZW"),
            ("inklusi", "1GOam_AahMpJK4nuvaIMWsvp0EKtSXZGd"),
        ):
            self.assertIn(f'id="{identifier}"', html)
            self.assertIn(target, html)

        for superseded_target in (
            "1Ufi2kcLs_U0s2Rm8SIF9-S5tn0YqFKLt",
            "1qrfayLDS5JafO1GgGjinzMfuVLdsBrMc",
            "1j62oWZ_kjQy7bux1GtAn0mJlCCOVdNsY",
            "1mq7mDek9IiHgnueH1gecuemft9WxijKS",
            "1qJ3AAbJGN8_rmVNhh9zUrXeu74OPJnVp",
        ):
            self.assertNotIn(superseded_target, html)

    def test_sppg_keeps_summaries_in_sections_without_a_separate_guide(self):
        html = (ROOT / "sppg.html").read_text(encoding="utf-8")

        self.assertNotIn('id="alur-seminar"', html)
        self.assertNotIn('href="#alur-seminar"', html)

        for identifier in ("identifikasi", "refleksi-ppg"):
            section = re.search(
                rf'<section id="{identifier}".*?</section>', html, re.S
            ).group(0)
            self.assertIn('class="sppg-artifact-card"', section)
            self.assertIn('class="reflection-summary"', section)

        seminar = re.search(r'<section id="seminar".*?</section>', html, re.S).group(0)
        self.assertIn('class="lead"', seminar)
        self.assertIn("Presentasi merangkum", seminar)

        self.assertNotIn("Peta Penilaian", html)
        self.assertNotIn("Bobot (%)", html)
        self.assertNotIn("rubrik", html.lower())

    def test_sppg_links_completed_reflections_and_supporting_artifacts(self):
        html = (ROOT / "sppg.html").read_text(encoding="utf-8")

        self.assertEqual(html.count('class="sppg-artifact-card"'), 13)
        self.assertEqual(html.count("Artefak yang digunakan"), 11)
        self.assertIn("Filosofi Pendidikan dan Pendidikan Nilai", html)
        self.assertNotIn("Fondasi Pendidikan Nasional", html)
        self.assertEqual(html.count("1DLft_RnDIL0OXLDyHD5oxoGeifH_ETzm"), 5)
        self.assertEqual(html.count("Modul Ajar Siklus 1–4"), 3)

        for target in (
            "1P5lPBB71QMqWn0Avpi3gGsFHBnycfng8",
            "1lPkbKANtwdwGALeo7jGOVUVYqO_LAkFi",
            "153nfHhccRt3c7YrQdc4tsqo1-WKXy0Pe",
            "1eLBS39XXIx8gTSIqAtiXjQ5pEySIujEu",
            "124CXbwCqr5TiWj3m1Pol25-G3JFqLOiM",
            "1zR-1eLTVyTDQw9x6tbBHfbiZB05GvwGd",
            "1gtANq_J3tXLrQp1s2G9EY3AuN0xua2_heeRhaQ1RyIk",
            "11I5_EJY2o_YAaP1y3zqIHtYCad7lKGH4TzU9kTM_ljY",
            "1Jq4-cm_Dmd2ZKtYFx2M4Nbinawb0v3zAl9P9vrUR1qA",
            "1uWmOg2KVMCJGD58NxBo77wGLAoOW2HUpFT2hHTjMuzc",
            "1i0sD1dqre9blhAIw0FUXMD3jGVKqIarA",
            "1_YLcXQ4C9OHdLXgMXgP4vBuISPJLRHPGDVCRUyff7rE",
            "1HFuNlrw2dPbbMfyj1_7IKu-WRTeI4bql",
            "1hu5sMfx2cY7Et9rHn8mxhJXfo6LFbEk6",
            "1vS7YQc1p5jR26ZZe6qn_e5OPXLQhJVof",
        ):
            self.assertIn(target, html)

        self.assertNotIn("1Facm8btXut7Klso_DtTCXyVPbFIqm1k6", html)
        self.assertNotIn("1xzIB1InDOKaaXHvpdVJUnVZRGISTtoRW", html)
        self.assertNotIn("1cNQvcVjKpW3EtvAUVxweSzA2TkAeN0XI", html)
        self.assertNotIn("17WwOLFEvwXeFs9lo12QCuUoq-HzqkXDB", html)

        reflection = re.search(
            r'<section id="refleksi-ppg".*?</section>', html, re.S
        ).group(0)
        self.assertNotIn('class="pending"', reflection)

        for identifier in (
            "pse",
            "pmal",
            "ppl-mandiri",
            "projek-kepemimpinan",
            "inklusi",
        ):
            card = re.search(
                rf'<article id="{identifier}" class="sppg-artifact-card">.*?</article>',
                html,
                re.S,
            ).group(0)
            self.assertIn('class="artifact-links"', card)

    def test_every_sppg_reflection_card_explains_its_learning(self):
        html = (ROOT / "sppg.html").read_text(encoding="utf-8")
        cards = re.findall(
            r'<article(?: id="[^"]+")? class="sppg-artifact-card">(.*?)</article>',
            html,
            re.S,
        )

        self.assertEqual(len(cards), 11)
        for card in cards:
            self.assertEqual(card.count('class="reflection-summary"'), 1)
            self.assertRegex(
                card,
                r'class="document-link".*class="reflection-summary".*class="artifact-links"',
            )
            summary = re.search(
                r'<div class="reflection-summary">.*?<p>(.*?)</p></div>',
                card,
                re.S,
            ).group(1)
            self.assertGreaterEqual(len(summary.split()), 20)
            self.assertGreaterEqual(len(re.findall(r"[.!?](?:\s|$)", summary)), 2)

    def test_sppg_shows_pdf_presentation_and_project_manager_artifact(self):
        html = (ROOT / "sppg.html").read_text(encoding="utf-8")

        seminar = re.search(r'<section id="seminar".*?</section>', html, re.S).group(0)
        self.assertIn("109-2p7FeeohxJGOiy23iZVTSEy10_GrN", seminar)
        self.assertIn("versi PDF", seminar)
        self.assertNotIn("1uDKI19WkS8OtlEP5K3si700kvPih4R8PDn1tqTa3X-o", html)
        self.assertNotIn("Presentasi final belum ada di folder SPPG.", seminar)

        project = re.search(
            r'<article id="projek-kepemimpinan" class="sppg-artifact-card">.*?</article>',
            html,
            re.S,
        ).group(0)
        self.assertIn("1XQWuo1rnstNpx6kubBlU8S1msxY6ORV3", project)
        self.assertIn("LK 1.11", project)

    def test_karya_inovasi_links_pdf_and_lk4_without_exposing_source_docx(self):
        html = (ROOT / "karya-inovasi.html").read_text(encoding="utf-8")

        self.assertIn("Karya &amp; LK 4 tersedia", html)
        self.assertIn("1RlkwLdn3-BVfUWi47J7rimYbdx0QiRt3", html)
        self.assertIn("19weIGNJLxM1vvXeivpg6qkmHiUZ74s6d", html)
        self.assertNotIn("1ZftGlbJ5jWmWx5DLadhMJrzQNIaso2iz", html)
        self.assertNotIn("1qYV6MzmMV-EfN9XWiJ4HqcjCOtFBLHmc", html)
        self.assertIn("Desain Pembelajaran Berbasis Scaffolding Bertahap", html)
        for heading in (
            "Identitas Karya",
            "Gagasan &amp; Riset",
            "Rancangan &amp; Implementasi",
            "Evaluasi Karya",
        ):
            self.assertIn(f"<h2>{heading}</h2>", html)
        for content in (
            "Scaffolding A–B–C",
            "Kebaruan",
            "Kreativitas",
            "Kebermanfaatan",
            "kelas X RPL 2",
            "4 JP",
        ):
            self.assertIn(content, html)
        mobile_nav = re.search(
            r'<details class="mobile-nav">.*?</details>', html, re.S
        ).group(0)
        for fragment in (
            "#identitas",
            "#gagasan-riset",
            "#rancangan",
            "#evaluasi",
            "#dokumen",
        ):
            self.assertIn(f'href="{fragment}"', mobile_nav)
        self.assertEqual(html.count('class="document-link"'), 2)
        self.assertIn("Efektivitas dan keberhasilan", html)
        self.assertIn("belum diterapkan secara utuh", html)
        self.assertNotIn("LK sudah ada dan akan menyusul", html)

    def test_karya_inovasi_uses_readable_presentation_layout(self):
        html = (ROOT / "karya-inovasi.html").read_text(encoding="utf-8")
        css = (ROOT / "assets/css/site.css").read_text(encoding="utf-8")
        evaluation = re.search(r'<section id="evaluasi".*?</section>', html, re.S).group(0)

        self.assertIn('class="karya-inovasi-page"', html)
        self.assertIn('class="evaluation-overview"', evaluation)
        self.assertIn('class="evaluation-criteria-grid"', evaluation)
        self.assertEqual(evaluation.count('class="evaluation-criterion"'), 3)
        self.assertIn('class="pending evaluation-boundary"', evaluation)
        self.assertNotIn('class="stat-grid"', evaluation)
        for selector in (
            ".karya-inovasi-page .section-heading",
            ".karya-inovasi-page #rancangan .timeline-card",
            ".evaluation-overview",
            ".evaluation-criteria-grid",
            ".evaluation-boundary",
        ):
            self.assertIn(selector, css)

    def test_all_pages_use_the_shared_footer_layout(self):
        for page_name in PAGES:
            html = (ROOT / page_name).read_text(encoding="utf-8")
            self.assertIn('class="footer-grid"', html, page_name)
            self.assertIn('class="footer-bottom"', html, page_name)

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

    def test_home_preserves_original_profile_and_contact_copy(self):
        home = re.sub(r"\s+", " ", (ROOT / "index.html").read_text(encoding="utf-8"))

        for expected in (
            "Menyelesaikan tugas sesuai target dan deadline",
            "Mudah beradaptasi dalam lingkungan baru",
            "100% Dedikasi",
            "Punya pertanyaan tentang e-portofolio ini atau ingin berdiskusi tentang "
            "pendidikan vokasi Informatika? Jangan ragu menghubungi saya.",
        ):
            self.assertIn(expected, home)

    def test_semester_one_gallery_preserves_its_original_context(self):
        html = re.sub(
            r"\s+", " ", (ROOT / "semester1.html").read_text(encoding="utf-8")
        )

        self.assertIn(
            "Dokumentasi praktik mengajar, karya murid, artefak media pembelajaran, "
            "dan aktivitas laboratorium komputer selama PPL Terbimbing di SMK Negeri "
            "1 Surabaya.",
            html,
        )

    def test_semester_one_uses_redesigned_shell_and_cleaned_photos(self):
        html = (ROOT / "semester1.html").read_text(encoding="utf-8")
        self.assertIn('class="semester-one-page"', html)
        self.assertIn('href="assets/css/site.css?v=20261028-gallery-v11"', html)
        self.assertIn('src="assets/js/site.js?v=20261027-scrollspy-v6"', html)
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

    def test_semester_one_uses_shared_font_and_compact_vertical_rhythm(self):
        html = (ROOT / "semester1.html").read_text(encoding="utf-8")
        css = (ROOT / "assets/css/site.css").read_text(encoding="utf-8")
        self.assertNotIn("Space+Grotesk", html)
        self.assertIn("family=Outfit", html)
        self.assertIn(".semester-one-page #home { min-height: auto;", css)
        self.assertNotIn(".semester-one-page #home { min-height: 640px;", css)

    def test_teacher_character_content_is_a_full_width_section(self):
        html = (ROOT / "semester1.html").read_text(encoding="utf-8")
        self.assertEqual(html.count('class="teacher-character-card"'), 4)
        self.assertEqual(html.count('class="teacher-character-section"'), 1)
        self.assertGreater(
            html.index('class="teacher-character-section"'),
            html.index('class="ref-split"'),
        )

    def test_teacher_character_cards_preserve_the_original_explanations(self):
        html = re.sub(
            r"\s+", " ", (ROOT / "semester1.html").read_text(encoding="utf-8")
        )

        for explanation in (
            "Mendorong kemandirian dari belakang. Murid diberi ruang untuk mencoba, "
            "salah, dan bangkit karena guru hadir sebagai pendamping, bukan pengawas "
            "yang mengontrol setiap langkah.",
            "Ketika murid buntu, guru masuk sebagai teman berpikir, bukan yang memberi "
            "jawaban, melainkan yang mengajukan pertanyaan yang tepat untuk membuka "
            "jalan pikiran mereka sendiri.",
            "Guru yang mau belajar dan berkembang, menunjukkannya lewat tindakan, "
            "bukan sekadar kata-kata. Ketika murid melihat gurunya masih mau berproses, "
            "mereka pun tidak takut untuk berproses.",
            "Murid hari ini tumbuh dalam ekosistem digital. Guru yang baik tidak melawan "
            "itu, tetapi memanfaatkannya sebagai jembatan menuju pembelajaran yang lebih "
            "bermakna dan kontekstual.",
        ):
            self.assertIn(explanation, html)

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

    def test_pplm_uses_cleaned_thumbnails_for_all_photos(self):
        html = (ROOT / "pplm.html").read_text(encoding="utf-8")
        css = (ROOT / "assets/css/site.css").read_text(encoding="utf-8")
        targets = re.findall(
            r'href="(assets/media/semester2/ppl/[^"]+GPSMapCamera\.webp)"',
            html,
        )
        self.assertEqual(len(targets), 11)
        self.assertEqual(len(set(targets)), 11)
        self.assertEqual(html.count('class="photo-cover"'), 0)
        self.assertNotIn("Pendampingan pembelajaran", html)
        self.assertNotIn("20260908_82945AMByGPSMapCamera.webp", html)
        self.assertIn(
            "<figcaption>Penyampaian materi analisis gim</figcaption>",
            html,
        )
        self.assertIn(
            "Pada 6 Oktober 2026, kegiatan kokurikuler juga dilaksanakan sebagaimana dicatat dalam LK 4.4 Kegiatan Nonmengajar.",
            html,
        )
        self.assertIn(
            "<figcaption>Persiapan kegiatan kokurikuler</figcaption>",
            html,
        )
        self.assertIn(
            "<figcaption>Kegiatan kokurikuler di laboratorium komputer</figcaption>",
            html,
        )
        self.assertNotIn("bukti utama praktik mengajar Siklus 4", html)
        self.assertNotIn("<figcaption>6 Oktober · Struktur Data Dasar</figcaption>", html)
        self.assertNotIn("<figcaption>Pertemuan I Siklus 4</figcaption>", html)
        self.assertIsNone(
            re.search(
                r'src="assets/media/semester2/ppl/[^"]+GPSMapCamera\.webp"',
                html,
            )
        )
        cleaned_photos = {
            "assets/media/semester2/ppl/cleaned/t01-praktik-terbimbing-clean.jpg":
                "assets/media/semester2/ppl/terbimbing/2026-07-28/20260728_71925AMByGPSMapCamera.webp",
            "assets/media/semester2/ppl/cleaned/t02-praktik-terbimbing-clean.jpg":
                "assets/media/semester2/ppl/terbimbing/2026-08-04/20260804_84241AMByGPSMapCamera.webp",
            "assets/media/semester2/ppl/cleaned/s1-01-persiapan-clean.jpg":
                "assets/media/semester2/ppl/siklus-1/2026-08-18/20260818_83034AMByGPSMapCamera.webp",
            "assets/media/semester2/ppl/cleaned/s1-02-dekomposisi-clean.jpg":
                "assets/media/semester2/ppl/siklus-1/2026-08-18/20260818_94931AMByGPSMapCamera.webp",
            "assets/media/semester2/ppl/cleaned/s1-03-pendampingan-murid-clean.jpg":
                "assets/media/semester2/ppl/siklus-1/2026-08-18/20260818_83756AMByGPSMapCamera.webp",
            "assets/media/semester2/ppl/cleaned/s2-01-analisis-gim-clean.jpg":
                "assets/media/semester2/ppl/siklus-2/2026-09-08/20260908_82942AMByGPSMapCamera.webp",
            "assets/media/semester2/ppl/cleaned/s3-01-konsep-gim-clean.jpg":
                "assets/media/semester2/ppl/siklus-3/2026-09-15/20260915_94753AMByGPSMapCamera.webp",
            "assets/media/semester2/ppl/cleaned/s3-02-praktik-mengajar-clean.jpg":
                "assets/media/semester2/ppl/siklus-3/2026-09-22/20260922_72909AMByGPSMapCamera.webp",
            "assets/media/semester2/ppl/cleaned/s3-03-variabel-clean.jpg":
                "assets/media/semester2/ppl/siklus-3/2026-09-29/20260929_73534AMByGPSMapCamera.webp",
            "assets/media/semester2/ppl/cleaned/s4-01-struktur-data-clean.jpg":
                "assets/media/semester2/ppl/siklus-4/2026-10-06/20261006_72208AMByGPSMapCamera.webp",
            "assets/media/semester2/ppl/cleaned/s4-02-pembelajaran-lab-clean.jpg":
                "assets/media/semester2/ppl/siklus-4/2026-10-06/20261006_72230AMByGPSMapCamera.webp",
        }
        for thumbnail, original in cleaned_photos.items():
            self.assertTrue((ROOT / thumbnail).is_file(), thumbnail)
            self.assertIn(
                f'href="{original}" target="_blank" rel="noopener"',
                html,
            )
            self.assertIn(f'src="{thumbnail}"', html)
        for target in targets:
            self.assertIn(
                f'href="{target}" target="_blank" rel="noopener"',
                html,
            )
        self.assertIn(
            ".pplm-page .photo-grid { width: min(100%, 900px); margin-inline: auto !important; }",
            css,
        )
        self.assertIn(
            ".pplm-page .photo-grid img { aspect-ratio: 16/9; }",
            css,
        )
        self.assertIn(
            ".pplm-page #siklus-2 .photo-grid { width: min(100%, 560px); grid-template-columns: 1fr; }",
            css,
        )

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
