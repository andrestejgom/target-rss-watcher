"""
Compares the freshly-scraped inventory against the inventory saved from the
previous run and produces a list of human-readable Change events.

Change kinds
------------
new_document        A URL that was not in the previous inventory.
content_replaced    Same URL, but the file's SHA-256 hash changed
                     (a "silent" replacement — same address, different bytes).
revision_marked      Same URL, hash unchanged (or unknown), but the page now
                     shows a "with revisions" / "updated" / "version N"
                     annotation that wasn't there before.
metadata_changed     Same URL, but the title or the date text next to it changed.
document_removed     A URL that was in the previous inventory but is gone now.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

ChangeKind = Literal[
    "new_document",
    "content_replaced",
    "revision_marked",
    "metadata_changed",
    "document_removed",
]


@dataclass
class Change:
    kind: ChangeKind
    service_key: str
    service_label: str
    url: str
    title: str
    detected_at: str  # ISO 8601 UTC
    detail: str = ""  # short human-readable extra info, e.g. "date: 12 Mar 2026 -> 20 Mar 2026"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def diff_service(
    service_key: str,
    service_label: str,
    previous_docs: dict[str, dict],
    current_docs: dict[str, dict],
) -> list[Change]:
    """
    previous_docs / current_docs: {url: {"title", "date_text", "annotation", "sha256", "size"}}
    """
    changes: list[Change] = []
    now = _now_iso()

    previous_urls = set(previous_docs)
    current_urls = set(current_docs)

    # New documents
    for url in sorted(current_urls - previous_urls):
        doc = current_docs[url]
        changes.append(
            Change(
                kind="new_document",
                service_key=service_key,
                service_label=service_label,
                url=url,
                title=doc.get("title", url),
                detected_at=now,
                detail=f"date: {doc.get('date_text') or 'n/a'}",
            )
        )

    # Removed documents
    for url in sorted(previous_urls - current_urls):
        doc = previous_docs[url]
        changes.append(
            Change(
                kind="document_removed",
                service_key=service_key,
                service_label=service_label,
                url=url,
                title=doc.get("title", url),
                detected_at=now,
                detail="no longer listed on the ECB page",
            )
        )

    # Documents present in both — check for changes
    for url in sorted(current_urls & previous_urls):
        old = previous_docs[url]
        new = current_docs[url]

        old_hash, new_hash = old.get("sha256"), new.get("sha256")
        if old_hash and new_hash and old_hash != new_hash:
            changes.append(
                Change(
                    kind="content_replaced",
                    service_key=service_key,
                    service_label=service_label,
                    url=url,
                    title=new.get("title", url),
                    detected_at=now,
                    detail="file content changed while the URL stayed the same",
                )
            )
            continue  # a content replacement supersedes lesser metadata diffs

        old_annotation, new_annotation = old.get("annotation"), new.get("annotation")
        if new_annotation and new_annotation != old_annotation:
            changes.append(
                Change(
                    kind="revision_marked",
                    service_key=service_key,
                    service_label=service_label,
                    url=url,
                    title=new.get("title", url),
                    detected_at=now,
                    detail=f"marked as: {new_annotation}",
                )
            )
            continue

        old_title, new_title = old.get("title"), new.get("title")
        old_date, new_date = old.get("date_text"), new.get("date_text")
        if old_title != new_title or old_date != new_date:
            bits = []
            if old_title != new_title:
                bits.append(f"title: '{old_title}' -> '{new_title}'")
            if old_date != new_date:
                bits.append(f"date: '{old_date}' -> '{new_date}'")
            changes.append(
                Change(
                    kind="metadata_changed",
                    service_key=service_key,
                    service_label=service_label,
                    url=url,
                    title=new.get("title", url),
                    detected_at=now,
                    detail="; ".join(bits),
                )
            )

    return changes
