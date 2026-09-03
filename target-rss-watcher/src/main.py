"""
Entry point. For each watched page:
  1. Render it with Playwright and extract document links.
  2. Fingerprint (SHA-256) each linked file.
  3. Compare against the previous inventory.
  4. Collect Change events.
Then: update feed.xml with any new changes, and save the new inventory.

Exit code is always 0 on a "clean" run (including "no changes found").
A non-zero exit code means the run itself failed (e.g. every page errored),
which GitHub Actions will surface as a failed job.
"""

from __future__ import annotations

import logging
import sys

from .config import WATCHED_PAGES
from .diff import Change, diff_service
from .feed import update_feed
from .hasher import fingerprint_url
from .inventory import load_inventory, save_inventory
from .scraper import DocumentLink, scrape_page

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("main")


def _doc_to_record(doc: DocumentLink, previous: dict | None) -> dict:
    """Fingerprint a document, reusing the previous hash if this fetch fails."""
    sha256, size = fingerprint_url(doc.url)
    if sha256 is None and previous is not None:
        # Network hiccup or oversized file this run — don't lose the last known hash.
        sha256 = previous.get("sha256")
        if size is None:
            size = previous.get("size")
    return {
        "title": doc.title,
        "date_text": doc.date_text,
        "annotation": doc.annotation,
        "sha256": sha256,
        "size": size,
    }


def run() -> int:
    inventory = load_inventory()
    previous_services: dict = inventory.get("services", {})
    new_services: dict = {}
    all_changes: list[Change] = []
    failures: list[str] = []

    for page in WATCHED_PAGES:
        logger.info("Scraping %s (%s)", page.label, page.url)
        try:
            docs = scrape_page(page.url)
        except Exception:
            logger.exception("Failed to scrape %s — keeping previous inventory for this page", page.label)
            failures.append(page.key)
            new_services[page.key] = previous_services.get(page.key, {})
            continue

        previous_docs = previous_services.get(page.key, {})
        current_docs: dict = {}
        for doc in docs:
            current_docs[doc.url] = _doc_to_record(doc, previous_docs.get(doc.url))

        new_services[page.key] = current_docs

        changes = diff_service(page.key, page.label, previous_docs, current_docs)
        if changes:
            logger.info("%s: %d change(s) detected", page.label, len(changes))
        all_changes.extend(changes)

    written = update_feed(all_changes)
    save_inventory({"services": new_services})

    logger.info(
        "Run complete: %d total change(s), %d item(s) now in feed.xml, %d page(s) failed",
        len(all_changes),
        written if all_changes else "unchanged",
        len(failures),
    )

    if failures and len(failures) == len(WATCHED_PAGES):
        logger.error("Every watched page failed to scrape — treating this as a failed run")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(run())
