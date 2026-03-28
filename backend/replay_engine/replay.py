"""
Network Replay Engine — rewind / fast-forward snapshots, compare states
"""
from typing import Dict, List, Optional
from backend.database.db import (
    get_snapshot, list_snapshots, get_timeline, diff_snapshots, get_total_snapshots
)


class ReplayEngine:
    """
    Cursor-based replay controller.
    Clients advance/rewind through the snapshot timeline.
    """
    def __init__(self):
        self._cursor_id: Optional[int] = None

    # ── Cursor control ─────────────────────────────────────────────────────
    def go_to_snapshot(self, snap_id: int) -> Optional[Dict]:
        snap = get_snapshot(snap_id)
        if snap:
            self._cursor_id = snap_id
        return snap

    def rewind(self, steps: int = 1) -> Optional[Dict]:
        timeline = get_timeline(limit=500)
        ids = [s["id"] for s in timeline]
        if not ids:
            return None
        if self._cursor_id is None:
            self._cursor_id = ids[-1]
        try:
            idx = ids.index(self._cursor_id)
        except ValueError:
            idx = len(ids) - 1
        idx = max(0, idx - steps)
        self._cursor_id = ids[idx]
        return get_snapshot(self._cursor_id)

    def fast_forward(self, steps: int = 1) -> Optional[Dict]:
        timeline = get_timeline(limit=500)
        ids = [s["id"] for s in timeline]
        if not ids:
            return None
        if self._cursor_id is None:
            self._cursor_id = ids[0]
        try:
            idx = ids.index(self._cursor_id)
        except ValueError:
            idx = 0
        idx = min(len(ids) - 1, idx + steps)
        self._cursor_id = ids[idx]
        return get_snapshot(self._cursor_id)

    def go_to_start(self) -> Optional[Dict]:
        timeline = get_timeline(limit=500)
        if not timeline:
            return None
        self._cursor_id = timeline[0]["id"]
        return get_snapshot(self._cursor_id)

    def go_to_end(self) -> Optional[Dict]:
        rows = list_snapshots(limit=1)
        if not rows:
            return None
        self._cursor_id = rows[0]["id"]
        return get_snapshot(self._cursor_id)

    @property
    def cursor_position(self) -> Optional[int]:
        return self._cursor_id

    # ── Timeline metadata ───────────────────────────────────────────────────
    def get_timeline(self) -> List[Dict]:
        return get_timeline(limit=500)

    def get_total(self) -> int:
        return get_total_snapshots()

    # ── Comparison ─────────────────────────────────────────────────────────
    def compare(self, id_a: int, id_b: int) -> Dict:
        return diff_snapshots(id_a, id_b)

    def compare_adjacent(self) -> Optional[Dict]:
        """Compare current cursor with previous snapshot."""
        timeline = get_timeline(limit=500)
        ids = [s["id"] for s in timeline]
        if len(ids) < 2 or self._cursor_id is None:
            return None
        try:
            idx = ids.index(self._cursor_id)
        except ValueError:
            return None
        if idx == 0:
            return None
        return diff_snapshots(ids[idx - 1], ids[idx])


# Module-level singleton
replay_engine = ReplayEngine()
