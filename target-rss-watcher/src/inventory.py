"""
Loads/saves the inventory.json state file that lets each run know what the
previous run already saw.

Shape of inventory.json:
{
  "generated_at": "2026-09-03T10:00:00Z",
  "services": {
    "ecms": {
      "https://.../file1.pdf": {
        "title": "...",
        "date_text": "14 March 2024",
        "annotation": null,
        "sha256": "abc123...",
        "size": 123456
      },
      ...
    },
    ...
  }
}
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from .config import INVENTORY_PATH


def load_inventory(path: str = INVENTORY_PATH) -> dict:
    if not os.path.exists(path):
        return {"generated_at": None, "services": {}}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_inventory(inventory: dict, path: str = INVENTORY_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    inventory["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(inventory, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")
