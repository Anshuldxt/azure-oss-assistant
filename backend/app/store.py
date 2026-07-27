"""
In-memory NE index.

This mirrors the client-side prototype's data model but lives on the
server so large CSVs never have to be parsed in the browser. It is a
single process-wide store guarded by a lock -- fine for a single
`uvicorn` worker serving one team's daily report. If you outgrow that
(multiple workers, need persistence across restarts), swap this
module for a Redis-backed or SQLite-backed implementation; the API
layer only calls the methods below, so nothing else needs to change.
"""

import threading
from collections import Counter
from typing import Dict, Optional


def _empty_ne_record() -> dict:
    return {
        "devip": [], "vlan": [], "s1": [],
        "gsm": [], "umts": [], "lte": [], "nr": [],
        "neReport": None,
    }


class Store:
    def __init__(self):
        self._lock = threading.Lock()
        self.reset()

    def reset(self):
        with self._lock:
            self.ne: Dict[str, dict] = {}
            self.alias: Dict[str, str] = {}   # BSC/RNC-side short name -> real NE name
            self.counts = Counter()           # gsm/umts/lte/nr/ip row counts
            self.files_loaded: list = []      # ingestion history for this session

    def ensure_ne(self, name: str) -> dict:
        rec = self.ne.get(name)
        if rec is None:
            rec = _empty_ne_record()
            self.ne[name] = rec
        return rec

    def already_have_cell(self, name: str, bucket: str, cell_key: str) -> bool:
        """True if this exact (NE, cellId) has already been recorded
        for this bucket -- lets us safely ingest overlapping sources
        (e.g. a vendor's consolidated xlsx *and* its raw per-shard
        exports of the same cells) without double-counting. Returns
        False (and records the key) the first time it's seen."""
        if not cell_key:
            return False
        rec = self.ensure_ne(name)
        seen = rec.setdefault("_seenCells", {}).setdefault(bucket, set())
        if cell_key in seen:
            return True
        seen.add(cell_key)
        return False

    def merge_ne_report(self, name: str, new_data: dict):
        """Merge a neReport dict into whatever's already stored for
        this NE, only overwriting a field if the new value is
        non-empty. Lets several source files (e.g. Ericsson's NE
        inventory + audit export) progressively enrich one record
        instead of the later file wiping out the earlier one."""
        rec = self.ensure_ne(name)
        existing = rec.get("neReport") or {}
        merged = dict(existing)
        for k, v in new_data.items():
            if v not in (None, ""):
                merged[k] = v
        rec["neReport"] = merged

    def add_alias(self, alias: str, real_ne: str):
        if alias:
            self.alias[alias] = real_ne

    def bump(self, key: str, n: int = 1):
        self.counts[key] += n

    def get_ne(self, name: str) -> Optional[dict]:
        if name in self.ne:
            return self.ne[name]
        real = self.alias.get(name)
        if real and real in self.ne:
            return self.ne[real]
        return None

    def resolve_name(self, name: str) -> Optional[str]:
        if name in self.ne:
            return name
        return self.alias.get(name)

    def search(self, q: str, limit: int = 12):
        ql = q.lower()
        ne_matches = [n for n in self.ne.keys() if ql in n.lower()][:limit]
        alias_matches = [
            {"alias": a, "ne": real}
            for a, real in self.alias.items()
            if ql in a.lower()
        ][: max(0, 6)]
        return ne_matches, alias_matches

    def stats(self) -> dict:
        ip_count = self.counts.get("devip", 0) + self.counts.get("vlan", 0)
        return {
            "neCount": len(self.ne),
            "gsm": self.counts.get("gsm", 0),
            "umts": self.counts.get("umts", 0),
            "lte": self.counts.get("lte", 0),
            "nr": self.counts.get("nr", 0),
            "ip": ip_count,
            "filesLoaded": self.files_loaded,
        }

    def lock(self):
        return self._lock


# single process-wide instance used by the API routes
store = Store()
