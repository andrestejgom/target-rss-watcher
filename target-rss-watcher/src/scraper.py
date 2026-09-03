"""
Scraper for the ECB TARGET Professional Use pages.

Design note
-----------
These ECB pages render their "Documents and links" section client-side
(the static HTML only contains an empty heading). A plain requests/BeautifulSoup
fetch will NOT see the document list — a real browser engine is required to
execute the page's JavaScript first. We use Playwright (headless Chromium) for
that, then parse the fully-rendered DOM with BeautifulSoup.

Extraction strategy
--------------------
Rather than depending on brittle CSS classes that ECB may change at any time,
we take a robust, generic approach: after the page has rendered, we scan the
main content area for every <a> tag that links to a file with a "document"
extension (PDF, ZIP, XSD, XLSX, ...). For each such link we capture:
  - the absolute URL
  - the link text (used as title)
  - the nearest preceding date-like text, if any (best effort)
  - the raw surrounding text of the containing block (used to detect
    "with revisions" / "updated" type annotations)

This is intentionally tolerant of markup changes: as long as ECB keeps
publishing documents as downloadable file links somewhere in the main
content area, this keeps working. If ECB radically redesigns the page
(e.g. documents become JS-only downloads with no <a href>), this will need
a fresh look — run `python -m src.scraper --dump <url>` to save the
rendered HTML for inspection.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from .config import DOCUMENT_EXTENSIONS, REQUEST_TIMEOUT_SECONDS, USER_AGENT

DATE_PATTERN = re.compile(
    r"\b\d{1,2}\s+(January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+\d{4}\b",
    re.IGNORECASE,
)

REVISION_PATTERN = re.compile(
    r"\b(with revisions|updated|revised|new|version\s+\d+(\.\d+)*)\b",
    re.IGNORECASE,
)


@dataclass
class DocumentLink:
    url: str
    title: str
    date_text: str | None = None
    annotation: str | None = None  # e.g. "with revisions", if detected nearby
    context: str = field(default="", repr=False)  # raw nearby text, for debugging

    @property
    def looks_like_document(self) -> bool:
        path = self.url.split("?")[0].split("#")[0].lower()
        return path.endswith(DOCUMENT_EXTENSIONS)


def render_page_html(url: str, wait_ms: int = 4000) -> str:
    """Load `url` in headless Chromium and return the fully-rendered HTML."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=USER_AGENT)
        page.set_default_timeout(REQUEST_TIMEOUT_SECONDS * 1000)
        page.goto(url, wait_until="networkidle")
        # Belt-and-braces: some ECB widgets finish rendering slightly after
        # the network goes idle (e.g. a client-side sort/filter pass).
        page.wait_for_timeout(wait_ms)
        html = page.content()
        browser.close()
        return html


def _nearest_date(node) -> str | None:
    """Look at the node's own text and a couple of nearby siblings/parents for a date."""
    candidates = []
    if node.parent is not None:
        candidates.append(node.parent.get_text(" ", strip=True))
    prev = node.find_previous(string=DATE_PATTERN)
    if prev:
        candidates.append(str(prev))
    for text in candidates:
        m = DATE_PATTERN.search(text)
        if m:
            return m.group(0)
    return None


def _nearest_annotation(node) -> str | None:
    text = node.parent.get_text(" ", strip=True) if node.parent else ""
    m = REVISION_PATTERN.search(text)
    return m.group(0) if m else None


def extract_document_links(html: str, base_url: str) -> list[DocumentLink]:
    """Parse rendered HTML and return every document-like link in the main content."""
    soup = BeautifulSoup(html, "html.parser")

    main = soup.find(id="main-content") or soup.find("main") or soup

    results: list[DocumentLink] = []
    seen_urls: set[str] = set()

    for a in main.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("javascript:", "mailto:", "#")):
            continue
        absolute = urljoin(base_url, href)
        path = absolute.split("?")[0].split("#")[0].lower()
        if not path.endswith(DOCUMENT_EXTENSIONS):
            continue
        if absolute in seen_urls:
            continue
        seen_urls.add(absolute)

        title = a.get_text(" ", strip=True) or a.get("title") or absolute.rsplit("/", 1)[-1]
        context_node = a.parent if a.parent is not None else a
        context_text = context_node.get_text(" ", strip=True)

        results.append(
            DocumentLink(
                url=absolute,
                title=title,
                date_text=_nearest_date(a),
                annotation=_nearest_annotation(a),
                context=context_text,
            )
        )

    return results


def scrape_page(url: str) -> list[DocumentLink]:
    html = render_page_html(url)
    return extract_document_links(html, url)


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="ECB page URL to scrape")
    parser.add_argument(
        "--dump",
        metavar="PATH",
        help="Save the fully-rendered HTML to PATH for manual inspection "
        "(useful if extraction finds zero documents and you need to see "
        "what the real DOM looks like)",
    )
    args = parser.parse_args()

    html = render_page_html(args.url)
    if args.dump:
        with open(args.dump, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Saved rendered HTML to {args.dump}", file=sys.stderr)

    docs = extract_document_links(html, args.url)
    print(f"Found {len(docs)} document link(s):", file=sys.stderr)
    for d in docs:
        print(f"  - [{d.date_text or '?'}] {d.title} -> {d.url}", file=sys.stderr)
        if d.annotation:
            print(f"      annotation: {d.annotation}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
