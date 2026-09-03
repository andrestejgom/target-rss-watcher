"""
Offline test of the extraction -> diff -> feed pipeline using local HTML
fixtures, so it runs without network access or a real browser. Run with:

    python -m pytest tests/ -v

or directly:

    python tests/test_pipeline.py
"""

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.diff import diff_service
from src.feed import update_feed
from src.scraper import extract_document_links

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
BASE_URL = "https://www.ecb.europa.eu/paym/target/target-professional-use-documents-links/ecms/html/index.en.html"


def _docs_to_inventory(docs) -> dict:
    return {
        d.url: {
            "title": d.title,
            "date_text": d.date_text,
            "annotation": d.annotation,
            "sha256": None,  # no network in this test — hash comparison covered separately
            "size": None,
        }
        for d in docs
    }


def test_extraction_finds_expected_links():
    with open(os.path.join(FIXTURES, "rendered_page_v1.html"), encoding="utf-8") as f:
        html = f.read()
    docs = extract_document_links(html, BASE_URL)
    assert len(docs) == 3, f"expected 3 document links, got {len(docs)}"

    titles = {d.title for d in docs}
    assert "ECMS User Detailed Functional Specifications" in titles
    assert "ECMS Release 3.0 schemas" in titles

    cr112 = next(d for d in docs if "Change Request 112" in d.title)
    assert cr112.annotation and "with revisions" in cr112.annotation.lower()
    assert cr112.date_text == "10 January 2026"
    print("OK: test_extraction_finds_expected_links")


def test_diff_detects_new_and_removed_documents():
    with open(os.path.join(FIXTURES, "rendered_page_v1.html"), encoding="utf-8") as f:
        html_v1 = f.read()
    with open(os.path.join(FIXTURES, "rendered_page_v2.html"), encoding="utf-8") as f:
        html_v2 = f.read()

    docs_v1 = extract_document_links(html_v1, BASE_URL)
    docs_v2 = extract_document_links(html_v2, BASE_URL)

    inv_v1 = _docs_to_inventory(docs_v1)
    inv_v2 = _docs_to_inventory(docs_v2)

    changes = diff_service("ecms", "ECMS", inv_v1, inv_v2)
    kinds = {c.kind for c in changes}

    assert "new_document" in kinds, "expected a new_document change (Change Request 130)"
    assert "document_removed" in kinds, "expected a document_removed change (Release 3.0 schemas)"

    new_doc = next(c for c in changes if c.kind == "new_document")
    assert "130" in new_doc.title

    removed_doc = next(c for c in changes if c.kind == "document_removed")
    assert "Release 3.0" in removed_doc.title
    print("OK: test_diff_detects_new_and_removed_documents")


def test_content_replacement_is_detected_via_hash():
    inv_before = {
        "https://example.org/doc.pdf": {
            "title": "Doc", "date_text": "1 Jan 2026", "annotation": None,
            "sha256": "aaa", "size": 100,
        }
    }
    inv_after = {
        "https://example.org/doc.pdf": {
            "title": "Doc", "date_text": "1 Jan 2026", "annotation": None,
            "sha256": "bbb", "size": 101,  # same URL, different content
        }
    }
    changes = diff_service("t2", "T2", inv_before, inv_after)
    assert len(changes) == 1
    assert changes[0].kind == "content_replaced"
    print("OK: test_content_replacement_is_detected_via_hash")


def test_feed_generation_writes_valid_items():
    with open(os.path.join(FIXTURES, "rendered_page_v1.html"), encoding="utf-8") as f:
        html_v1 = f.read()
    with open(os.path.join(FIXTURES, "rendered_page_v2.html"), encoding="utf-8") as f:
        html_v2 = f.read()

    inv_v1 = _docs_to_inventory(extract_document_links(html_v1, BASE_URL))
    inv_v2 = _docs_to_inventory(extract_document_links(html_v2, BASE_URL))
    changes = diff_service("ecms", "ECMS", inv_v1, inv_v2)

    with tempfile.TemporaryDirectory() as tmp:
        feed_path = os.path.join(tmp, "feed.xml")
        count = update_feed(changes, feed_path=feed_path)
        assert count == len(changes)
        assert os.path.exists(feed_path)
        with open(feed_path, encoding="utf-8") as f:
            xml = f.read()
        assert "<rss" in xml and "</rss>" in xml
        assert xml.count("<item>") == len(changes)
        assert "Change Request 130" in xml
    print("OK: test_feed_generation_writes_valid_items")


if __name__ == "__main__":
    test_extraction_finds_expected_links()
    test_diff_detects_new_and_removed_documents()
    test_content_replacement_is_detected_via_hash()
    test_feed_generation_writes_valid_items()
    print("\nAll tests passed.")
