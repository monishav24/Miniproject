"""
Temporal Network State Database — SQLite-backed snapshot store
Behaves like "Git for networks": versioned states, diff, rollback, timeline
"""
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).parent.parent / "data" / "network_states.db"


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   REAL    NOT NULL,
                tick        INTEGER NOT NULL,
                label       TEXT    DEFAULT '',
                fingerprint TEXT    NOT NULL,
                topology    TEXT    NOT NULL,
                metrics     TEXT    NOT NULL,
                surge       INTEGER DEFAULT 0,
                tag         TEXT    DEFAULT 'auto'
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   REAL    NOT NULL,
                name        TEXT,
                config      TEXT,
                results     TEXT
            )
        """)
        con.commit()


# ── Snapshot CRUD ─────────────────────────────────────────────────────────────
def save_snapshot(snapshot: dict, label: str = "", tag: str = "auto") -> int:
    with _conn() as con:
        cur = con.execute("""
            INSERT INTO snapshots (timestamp, tick, label, fingerprint, topology, metrics, surge, tag)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            snapshot["timestamp"],
            snapshot["tick"],
            label,
            snapshot["fingerprint"],
            json.dumps({"nodes": snapshot["nodes"], "edges": snapshot["edges"]}),
            json.dumps(snapshot["metrics"]),
            1 if snapshot.get("surge_active") else 0,
            tag,
        ))
        con.commit()
        return cur.lastrowid


def get_snapshot(snap_id: int) -> Optional[Dict]:
    with _conn() as con:
        row = con.execute("SELECT * FROM snapshots WHERE id=?", (snap_id,)).fetchone()
    return _row_to_dict(row) if row else None


def get_latest_snapshot() -> Optional[Dict]:
    with _conn() as con:
        row = con.execute("SELECT * FROM snapshots ORDER BY id DESC LIMIT 1").fetchone()
    return _row_to_dict(row) if row else None


def list_snapshots(limit: int = 100, offset: int = 0) -> List[Dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT id, timestamp, tick, label, fingerprint, surge, tag FROM snapshots "
            "ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset)
        ).fetchall()
    return [dict(r) for r in rows]


def get_total_snapshots() -> int:
    with _conn() as con:
        return con.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]


def delete_snapshot(snap_id: int):
    with _conn() as con:
        con.execute("DELETE FROM snapshots WHERE id=?", (snap_id,))
        con.commit()


def tag_snapshot(snap_id: int, label: str, tag: str = "manual"):
    with _conn() as con:
        con.execute("UPDATE snapshots SET label=?, tag=? WHERE id=?", (label, tag, snap_id))
        con.commit()


# ── Diff ─────────────────────────────────────────────────────────────────────
def diff_snapshots(id_a: int, id_b: int) -> Dict:
    a = get_snapshot(id_a)
    b = get_snapshot(id_b)
    if not a or not b:
        return {"error": "Snapshot not found"}

    def _metric_diff(ma, mb):
        result = {}
        for k in set(list(ma.keys()) + list(mb.keys())):
            va = ma.get(k, 0)
            vb = mb.get(k, 0)
            if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                result[k] = {"a": va, "b": vb, "delta": round(vb - va, 4)}
        return result

    top_a = a["topology"]
    top_b = b["topology"]

    # Node load diffs
    nodes_a = {n["id"]: n["load"] for n in top_a.get("nodes", [])}
    nodes_b = {n["id"]: n["load"] for n in top_b.get("nodes", [])}
    node_diffs = {
        nid: {"a": nodes_a.get(nid, 0), "b": nodes_b.get(nid, 0),
              "delta": round(nodes_b.get(nid, 0) - nodes_a.get(nid, 0), 4)}
        for nid in set(list(nodes_a.keys()) + list(nodes_b.keys()))
    }

    return {
        "snapshot_a": {"id": id_a, "tick": a["tick"], "fingerprint": a["fingerprint"]},
        "snapshot_b": {"id": id_b, "tick": b["tick"], "fingerprint": b["fingerprint"]},
        "fingerprint_match": a["fingerprint"] == b["fingerprint"],
        "tick_delta": b["tick"] - a["tick"],
        "metric_diff": _metric_diff(a["metrics"], b["metrics"]),
        "node_load_diff": node_diffs,
    }


# ── Timeline ─────────────────────────────────────────────────────────────────
def get_timeline(limit: int = 200) -> List[Dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT id, timestamp, tick, label, fingerprint, surge, tag "
            "FROM snapshots ORDER BY tick ASC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


# ── Experiments ───────────────────────────────────────────────────────────────
def save_experiment(name: str, config: dict, results: list) -> int:
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO experiments (timestamp, name, config, results) VALUES (?,?,?,?)",
            (time.time(), name, json.dumps(config), json.dumps(results))
        )
        con.commit()
        return cur.lastrowid


def list_experiments(limit: int = 50) -> List[Dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT id, timestamp, name, config, results FROM experiments ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["config"]  = json.loads(d["config"])
        d["results"] = json.loads(d["results"])
        out.append(d)
    return out


# ── Internal ─────────────────────────────────────────────────────────────────
def _row_to_dict(row) -> Dict[str, Any]:
    d = dict(row)
    d["topology"] = json.loads(d["topology"])
    d["metrics"]  = json.loads(d["metrics"])
    return d
