"""
Downloads each linked document (streaming, without loading it fully into
memory) and computes a SHA-256 fingerprint. This is what lets the watcher
detect a *silent replacement* — a PDF, ZIP or XSD that keeps the exact same
URL but whose content actually changed.

Files above config.MAX_HASH_BYTES are skipped (only metadata is tracked for
them) to keep hourly runs fast and bandwidth-friendly.
"""

from __future__ import annotations

import hashlib
import logging
import time

import requests

from .config import (
    DELAY_BETWEEN_REQUESTS_SECONDS,
    MAX_HASH_BYTES,
    REQUEST_TIMEOUT_SECONDS,
    USER_AGENT,
)

logger = logging.getLogger(__name__)

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT})


def fingerprint_url(url: str) -> tuple[str | None, int | None]:
    """
    Return (sha256_hex, content_length) for the file at `url`.

    Returns (None, size) if the file was too large to hash, and
    (None, None) if the download failed (network hiccups shouldn't
    crash the whole run — a failed fingerprint is treated as "unknown,
    keep previous value" by the diff step).
    """
    try:
        with _session.get(url, stream=True, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            resp.raise_for_status()

            declared_length = resp.headers.get("Content-Length")
            if declared_length and int(declared_length) > MAX_HASH_BYTES:
                logger.info("Skipping hash for %s (declared size %s bytes > cap)", url, declared_length)
                return None, int(declared_length)

            digest = hashlib.sha256()
            total = 0
            for chunk in resp.iter_content(chunk_size=65536):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_HASH_BYTES:
                    logger.info("Skipping hash for %s (exceeded cap while streaming)", url)
                    return None, total
                digest.update(chunk)

            return digest.hexdigest(), total

    except requests.RequestException as exc:
        logger.warning("Failed to fetch %s for hashing: %s", url, exc)
        return None, None
    finally:
        time.sleep(DELAY_BETWEEN_REQUESTS_SECONDS)
