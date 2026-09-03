"""
Configuration for the TARGET Professional Use RSS watcher.

Edit WATCHED_PAGES to add or remove ECB pages. Each entry needs:
  - key:   short internal identifier (used in the inventory file and feed)
  - label: human-readable name shown in feed entries
  - url:   the English ("index.en.html") ECB page to watch
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class WatchedPage:
    key: str
    label: str
    url: str


WATCHED_PAGES: list[WatchedPage] = [
    WatchedPage(
        key="coco",
        label="Common components",
        url="https://www.ecb.europa.eu/paym/target/target-professional-use-documents-links/coco/html/index.en.html",
    ),
    WatchedPage(
        key="t2",
        label="T2",
        url="https://www.ecb.europa.eu/paym/target/target-professional-use-documents-links/t2/html/index.en.html",
    ),
    WatchedPage(
        key="t2s",
        label="T2S",
        url="https://www.ecb.europa.eu/paym/target/target-professional-use-documents-links/t2s/html/index.en.html",
    ),
    WatchedPage(
        key="tips",
        label="TIPS",
        url="https://www.ecb.europa.eu/paym/target/target-professional-use-documents-links/tips/html/index.en.html",
    ),
    WatchedPage(
        key="ecms",
        label="ECMS",
        url="https://www.ecb.europa.eu/paym/target/target-professional-use-documents-links/ecms/html/index.en.html",
    ),
    WatchedPage(
        key="pontes",
        label="Pontes",
        url="https://www.ecb.europa.eu/paym/target/target-professional-use-documents-links/pontes-documents-links/html/index.en.html",
    ),
]

# File extensions that count as "documents" worth tracking.
DOCUMENT_EXTENSIONS = (
    ".pdf", ".zip", ".xsd", ".xml", ".xlsx", ".xls",
    ".docx", ".doc", ".csv", ".pptx", ".txt", ".json",
)

# Skip hashing (but still track title/date/link changes for) files above this size,
# to keep hourly runs fast and avoid downloading huge archives repeatedly.
MAX_HASH_BYTES = 25 * 1024 * 1024  # 25 MB

# Network behaviour
REQUEST_TIMEOUT_SECONDS = 30
DELAY_BETWEEN_REQUESTS_SECONDS = 1.5
USER_AGENT = (
    "TARGET-ProfUse-RSS-Watcher/1.0 "
    "(+https://github.com/; personal monitoring tool, low frequency, respects robots.txt)"
)

# Paths
DATA_DIR = "data"
INVENTORY_PATH = f"{DATA_DIR}/inventory.json"
DOCS_DIR = "docs"
FEED_PATH = f"{DOCS_DIR}/feed.xml"
MAX_FEED_ITEMS = 300

# Feed metadata — customise once you know your GitHub Pages URL
FEED_TITLE = "TARGET Professional Use – Document Updates"
FEED_DESCRIPTION = (
    "Unofficial synthetic RSS feed watching the ECB's TARGET Professional Use "
    "documentation pages (Common components, T2, T2S, TIPS, ECMS, Pontes) for "
    "new, revised, replaced or removed documents. This feed is not affiliated "
    "with or endorsed by the European Central Bank; the ECB remains the "
    "authoritative source at all times."
)

FEED_SELF_URL = "https://andrestejgom.github.io/target-rss-watcher/feed.xml"
FEED_SITE_URL = "https://www.ecb.europa.eu/paym/target/target-professional-use-documents-links/html/index.en.html"
