import argparse
import hashlib
import json
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


BLOCK_TAGS = {
    "blockquote",
    "dd",
    "dl",
    "dt",
    "figcaption",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "li",
    "ol",
    "p",
    "ul",
}
IGNORED_TEXT_TAGS = {"script", "style"}
TEXT_BOUNDARY_TAGS = BLOCK_TAGS | {
    "article",
    "br",
    "div",
    "footer",
    "header",
    "hr",
    "main",
    "nav",
    "section",
    "td",
    "th",
    "tr",
}
VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}


def normalize_text(value):
    return re.sub(r"\s+", " ", value).strip()


class InventoryParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.identifiers = []
        self.hrefs = []
        self.images = []
        self.content_blocks = []
        self.text_segments = []
        self.block_records = []
        self.link_records = []
        self.image_records = []
        self.rendered_text_parts = []
        self.element_stack = []
        self.active_blocks = []
        self.active_links = []
        self.ignored_depth = 0
        self.preserve_ignored_elements = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if self.preserve_ignored_elements or "data-preserve-ignore" in attributes:
            if tag not in VOID_TAGS:
                self.preserve_ignored_elements.append(tag)
            return
        if tag in IGNORED_TEXT_TAGS:
            self.ignored_depth += 1

        identifier = attributes.get("id")
        if identifier is not None:
            self.identifiers.append(identifier)
        if tag == "a":
            if "name" in attributes:
                self.identifiers.append(attributes["name"])
                identifier = identifier or attributes["name"]

        parent_context = self.element_stack[-1][1] if self.element_stack else None
        context = identifier or parent_context
        if tag not in VOID_TAGS:
            self.element_stack.append((tag, context))

        if not self.ignored_depth and tag in TEXT_BOUNDARY_TAGS:
            self.rendered_text_parts.append(" ")
        if tag in BLOCK_TAGS:
            self.content_blocks.append(tag)
            self.active_blocks.append({"tag": tag, "context": context, "parts": []})
        if tag == "a" and "href" in attributes:
            href = attributes["href"]
            self.hrefs.append(href)
            self.active_links.append({"context": context, "href": href, "parts": []})
        if tag == "img" and "src" in attributes:
            source = attributes["src"]
            self.images.append(source)
            link_href = self.active_links[-1]["href"] if self.active_links else None
            self.image_records.append(
                (context, link_href, source, attributes.get("alt", ""))
            )

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if self.preserve_ignored_elements:
            if tag in self.preserve_ignored_elements:
                index = len(self.preserve_ignored_elements) - 1 - self.preserve_ignored_elements[::-1].index(tag)
                del self.preserve_ignored_elements[index:]
            return
        if tag == "a" and self.active_links:
            link = self.active_links.pop()
            self.link_records.append(
                (link["context"], normalize_text("".join(link["parts"])), link["href"])
            )
        if tag in BLOCK_TAGS:
            for index in range(len(self.active_blocks) - 1, -1, -1):
                if self.active_blocks[index]["tag"] == tag:
                    block = self.active_blocks.pop(index)
                    self.block_records.append(
                        (block["context"], tag, normalize_text("".join(block["parts"])))
                    )
                    break
        if not self.ignored_depth and tag in TEXT_BOUNDARY_TAGS:
            self.rendered_text_parts.append(" ")
        if tag in IGNORED_TEXT_TAGS and self.ignored_depth:
            self.ignored_depth -= 1
        for index in range(len(self.element_stack) - 1, -1, -1):
            if self.element_stack[index][0] == tag:
                del self.element_stack[index:]
                break

    def handle_data(self, data):
        if self.ignored_depth or self.preserve_ignored_elements:
            return
        self.rendered_text_parts.append(data)
        for block in self.active_blocks:
            block["parts"].append(data)
        for link in self.active_links:
            link["parts"].append(data)
        normalized = normalize_text(data)
        if normalized:
            self.text_segments.append(normalized)

    @property
    def rendered_text(self):
        return normalize_text("".join(self.rendered_text_parts))


def inventory(path):
    parser = InventoryParser()
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()
    return parser


def external_hrefs(hrefs):
    return [href for href in hrefs if urlparse(href).scheme.lower() in {"http", "https", "mailto", "tel"}]


def changed_values(label, source_values, target_values):
    missing = list((Counter(source_values) - Counter(target_values)).elements())
    added = list((Counter(target_values) - Counter(source_values)).elements())
    if not missing and not added:
        return None
    return f"{label}: missing={missing!r}, added={added!r}"


def missing_values(label, source_values, target_values):
    missing = list((Counter(source_values) - Counter(target_values)).elements())
    if not missing:
        return None
    return f"{label}: missing={missing!r}"


def git_blob_sha(path):
    content = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha1(b"blob " + str(len(content)).encode("ascii") + b"\0" + content).hexdigest()


def baseline_error(source, baseline):
    data = json.loads(baseline.read_text(encoding="utf-8"))
    entry = next((page for page in data.get("pages", []) if page.get("name") == source.name), None)
    if entry is None:
        return f"baseline has no entry for {source.name}"
    actual = git_blob_sha(source)
    if actual != entry.get("sha"):
        return f"source SHA does not match baseline: expected={entry.get('sha')}, actual={actual}"
    return None


def load_migrations(path):
    if path is None:
        return {}
    migrations = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(migrations, dict) or not all(
        isinstance(old, str) and isinstance(new, str) for old, new in migrations.items()
    ):
        raise ValueError("migrations must be a JSON object mapping old values to new values")
    return migrations


def compare(
    source_path,
    target_path,
    migrations=None,
    baseline=None,
    allow_additions=False,
    text_migrations=None,
):
    source = inventory(source_path)
    target = inventory(target_path)
    migrations = migrations or {}
    text_migrations = text_migrations or {}
    errors = []

    duplicates = sorted(value for value, count in Counter(target.identifiers).items() if count > 1)
    if duplicates:
        errors.append(f"duplicate anchor/id: {duplicates!r}")

    migrated_text = [text_migrations.get(value, value) for value in source.text_segments]
    migrated_blocks = [
        (context, tag, text_migrations.get(value, value))
        for context, tag, value in source.block_records
    ]

    if allow_additions or text_migrations:
        comparison = missing_values if allow_additions else changed_values
        error = comparison("missing content", migrated_text, target.text_segments)
        if error:
            errors.append(error)
    elif source.rendered_text != target.rendered_text:
        errors.append("missing content: rendered text differs")

    checks = (
        ("content structure changed", source.content_blocks, target.content_blocks),
        ("anchor/id changed", source.identifiers, target.identifiers),
        ("image source changed", source.images, target.images),
        ("anchored content changed", migrated_blocks, target.block_records),
    )
    for label, source_values, target_values in checks:
        comparison = missing_values if allow_additions else changed_values
        error = comparison(label, source_values, target_values)
        if error:
            errors.append(error)

    migrated_hrefs = [migrations.get(href, href) for href in source.hrefs]
    comparison = missing_values if allow_additions else changed_values
    href_error = comparison("link href changed", migrated_hrefs, target.hrefs)
    if href_error:
        errors.append(href_error)

    migrated_links = [
        (context, label, migrations.get(href, href))
        for context, label, href in source.link_records
    ]
    link_context_error = comparison(
        "link context changed", migrated_links, target.link_records
    )
    if link_context_error:
        errors.append(link_context_error)

    migrated_images = [
        (context, migrations.get(href, href) if href is not None else None, source_value, alt)
        for context, href, source_value, alt in source.image_records
    ]
    image_context_error = comparison(
        "image context changed", migrated_images, target.image_records
    )
    if image_context_error:
        errors.append(image_context_error)

    migrated_external = external_hrefs(migrated_hrefs)
    external_error = comparison(
        "external href changed", migrated_external, external_hrefs(target.hrefs)
    )
    if external_error:
        errors.append(external_error)

    if baseline is not None:
        error = baseline_error(source_path, baseline)
        if error:
            errors.append(error)

    return {
        "ok": not errors,
        "errors": errors,
        "preserved": {
            "anchor_ids": len(target.identifiers),
            "content_blocks": len(target.content_blocks),
            "external_hrefs": len(external_hrefs(target.hrefs)),
            "images": len(target.images),
            "links": len(target.hrefs),
            "text_segments": len(target.text_segments),
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Check preservation between two HTML documents.")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--migrations", type=Path)
    parser.add_argument("--text-migrations", type=Path)
    parser.add_argument(
        "--allow-additions",
        action="store_true",
        help="Allow new shell/content while requiring every source item to remain unchanged.",
    )
    args = parser.parse_args()

    try:
        report = compare(
            args.source,
            args.target,
            load_migrations(args.migrations),
            args.baseline,
            args.allow_additions,
            load_migrations(args.text_migrations),
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        report = {"ok": False, "errors": [str(error)], "preserved": {}}

    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
