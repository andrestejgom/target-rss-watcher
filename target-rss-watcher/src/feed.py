"""
Builds/updates the RSS 2.0 feed.xml from a list of Change events.

We hand-roll minimal RSS XML rather than pulling in a templating dependency —
the format is small and stable enough that this is easier to audit than a
third-party feed library.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape

from .config import (
    FEED_DESCRIPTION,
    FEED_PATH,
    FEED_SELF_URL,
    FEED_SITE_URL,
    FEED_TITLE,
    MAX_FEED_ITEMS,
)
from .diff import Change

KIND_LABELS = {
    "new_document": "New document",
    "content_replaced": "Document replaced (same link, new content)",
    "revision_marked": "Revision marked",
    "metadata_changed": "Title/date changed",
    "document_removed": "Document removed",
}


def _rfc822_now() -> str:
    return format_datetime(datetime.now(timezone.utc))


def _item_guid(change: Change) -> str:
    # Stable per event: same URL + same kind + same detection timestamp.
    return f"{change.service_key}:{change.kind}:{change.url}:{change.detected_at}"


def change_to_item_xml(change: Change) -> str:
    kind_label = KIND_LABELS.get(change.kind, change.kind)
    title = f"[{change.service_label}] {kind_label}: {escape(change.title)}"
    description_parts = [escape(change.detail)] if change.detail else []
    description_parts.append(f'Source: <a href="{escape(change.url)}">{escape(change.url)}</a>')
    description = "<br/>".join(description_parts)

    pub_date = format_datetime(
        datetime.strptime(change.detected_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    )

    return (
        "<item>"
        f"<title>{escape(title)}</title>"
        f"<link>{escape(change.url)}</link>"
        f"<guid isPermaLink=\"false\">{escape(_item_guid(change))}</guid>"
        f"<pubDate>{pub_date}</pubDate>"
        f"<category>{escape(change.service_label)}</category>"
        f"<description><![CDATA[{description}]]></description>"
        "</item>"
    )


def _read_existing_item_xmls(path: str) -> list[str]:
    """Extract raw <item>...</item> blocks from an existing feed.xml, if any."""
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    items: list[str] = []
    start = 0
    while True:
        i = content.find("<item>", start)
        if i == -1:
            break
        j = content.find("</item>", i)
        if j == -1:
            break
        j += len("</item>")
        items.append(content[i:j])
        start = j
    return items


def update_feed(changes: list[Change], feed_path: str = FEED_PATH) -> int:
    """
    Prepend new items for `changes` to the existing feed (newest first),
    truncate to MAX_FEED_ITEMS, and write feed.xml. Returns the number of
    items written.

    If `changes` is empty, the feed is left untouched.
    """
    if not changes:
        return 0

    os.makedirs(os.path.dirname(feed_path), exist_ok=True)

    new_item_xmls = [change_to_item_xml(c) for c in changes]
    existing_item_xmls = _read_existing_item_xmls(feed_path)

    all_items = new_item_xmls + existing_item_xmls
    all_items = all_items[:MAX_FEED_ITEMS]

    feed_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        "<channel>\n"
        f"<title>{escape(FEED_TITLE)}</title>\n"
        f"<link>{escape(FEED_SITE_URL)}</link>\n"
        f"<description>{escape(FEED_DESCRIPTION)}</description>\n"
        f'<atom:link href="{escape(FEED_SELF_URL)}" rel="self" type="application/rss+xml" />\n'
        "<language>en</language>\n"
        f"<lastBuildDate>{_rfc822_now()}</lastBuildDate>\n"
        f"<generator>target-rss-watcher</generator>\n"
        + "\n".join(all_items)
        + "\n</channel>\n</rss>\n"
    )

    with open(feed_path, "w", encoding="utf-8") as f:
        f.write(feed_xml)

    return len(all_items)
