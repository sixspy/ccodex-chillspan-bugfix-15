"""SQLite：冷链温谱管道母仓公共库层。"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DB_PATH = DATA / "app.db"
FIXTURES = ROOT / "fixtures"
FRONTEND = ROOT / "frontend"

PRODUCT_META = {
    "product": "冷链温谱管道",
    "skeleton": "探头批次入库 → 超温游标闭环 → 封批升代 → 温谱导出 → 冷链血缘对账",
    "modules": [
        "chambers",
        "probes",
        "batches",
        "excursions",
        "seal",
        "spectrum",
        "lineage",
        "reconcile",
        "locks",
        "calibration",
        "route_plan",
    ],
    "stubs": ["carrier_ingest", "thaw_event"],
}


def connect() -> sqlite3.Connection:
    DATA.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def sha_password(password: str) -> str:
    import hashlib

    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def now_iso() -> str:
    from datetime import datetime

    return datetime.now().isoformat(timespec="seconds")


SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  username TEXT PRIMARY KEY,
  password_sha TEXT NOT NULL,
  role TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS cold_chambers(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  chamber_code TEXT UNIQUE NOT NULL,
  region TEXT NOT NULL,
  name TEXT NOT NULL,
  target_min REAL NOT NULL,
  target_max REAL NOT NULL,
  quota_batches INTEGER NOT NULL DEFAULT 20,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS probes(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  probe_code TEXT UNIQUE NOT NULL,
  chamber_id INTEGER NOT NULL,
  model TEXT NOT NULL,
  online_status TEXT NOT NULL,
  calibration_due TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(chamber_id) REFERENCES cold_chambers(id)
);
CREATE TABLE IF NOT EXISTS temp_batches(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  batch_code TEXT UNIQUE NOT NULL,
  chamber_id INTEGER NOT NULL,
  probe_id INTEGER NOT NULL,
  cargo_ref TEXT NOT NULL,
  temp_points TEXT NOT NULL,
  generation INTEGER NOT NULL DEFAULT 1,
  status TEXT NOT NULL,
  min_observed REAL,
  max_observed REAL,
  created_at TEXT NOT NULL,
  sealed_at TEXT,
  FOREIGN KEY(chamber_id) REFERENCES cold_chambers(id),
  FOREIGN KEY(probe_id) REFERENCES probes(id)
);
CREATE TABLE IF NOT EXISTS excursion_cursors(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  batch_id INTEGER NOT NULL,
  cursor_key TEXT NOT NULL,
  peak_temp REAL NOT NULL,
  threshold REAL NOT NULL,
  status TEXT NOT NULL,
  opened_at TEXT NOT NULL,
  closed_at TEXT,
  note TEXT,
  FOREIGN KEY(batch_id) REFERENCES temp_batches(id)
);
CREATE TABLE IF NOT EXISTS seal_snapshots(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  batch_id INTEGER NOT NULL,
  batch_generation INTEGER NOT NULL,
  manifest TEXT NOT NULL,
  status TEXT NOT NULL,
  sealed_at TEXT NOT NULL,
  FOREIGN KEY(batch_id) REFERENCES temp_batches(id)
);
CREATE TABLE IF NOT EXISTS spectrum_exports(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  batch_id INTEGER NOT NULL,
  export_ref TEXT NOT NULL,
  point_count INTEGER NOT NULL,
  checksum TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(batch_id) REFERENCES temp_batches(id)
);
CREATE TABLE IF NOT EXISTS lineage_edges(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  from_batch_id INTEGER NOT NULL,
  to_batch_id INTEGER,
  edge_type TEXT NOT NULL,
  detail TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(from_batch_id) REFERENCES temp_batches(id)
);
CREATE TABLE IF NOT EXISTS calibration_records(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  probe_id INTEGER NOT NULL,
  calibrated_at TEXT NOT NULL,
  offset_c REAL NOT NULL,
  valid_until TEXT NOT NULL,
  officer TEXT NOT NULL,
  status TEXT NOT NULL,
  FOREIGN KEY(probe_id) REFERENCES probes(id)
);
CREATE TABLE IF NOT EXISTS route_plans(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  route_code TEXT UNIQUE NOT NULL,
  origin_region TEXT NOT NULL,
  dest_region TEXT NOT NULL,
  cold_hours REAL NOT NULL,
  vehicle_type TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chamber_locks(
  lock_key TEXT PRIMARY KEY,
  holder TEXT NOT NULL,
  acquired_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS contention_log(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lock_key TEXT NOT NULL,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  detail TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_trail(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  target TEXT,
  payload TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS carrier_ingest_jobs(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  carrier_name TEXT NOT NULL,
  row_count INTEGER NOT NULL,
  mode TEXT NOT NULL,
  status TEXT NOT NULL,
  detail TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS thaw_event_jobs(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  batch_id INTEGER,
  thaw_minutes INTEGER NOT NULL,
  mode TEXT NOT NULL,
  status TEXT NOT NULL,
  detail TEXT,
  created_at TEXT NOT NULL
);
"""


def write_audit(conn: sqlite3.Connection, actor: str, action: str, target: str, payload: dict) -> None:
    conn.execute(
        """INSERT INTO audit_trail(actor,action,target,payload,created_at)
           VALUES (?,?,?,?,?)""",
        (actor, action, target, json.dumps(payload, ensure_ascii=False), now_iso()),
    )


def _load_json(name: str):
    path = FIXTURES / name
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def seed_users(conn: sqlite3.Connection) -> None:
    for u, role in (("admin", "admin"), ("ops", "clerk"), ("viewer", "viewer")):
        conn.execute(
            "INSERT OR IGNORE INTO users(username,password_sha,role) VALUES (?,?,?)",
            (u, sha_password("123456"), role),
        )


def _chamber_id(conn, code: str) -> int | None:
    row = conn.execute(
        "SELECT id FROM cold_chambers WHERE chamber_code=?", (code,)
    ).fetchone()
    return int(row["id"]) if row else None


def seed_chambers(conn: sqlite3.Connection) -> None:
    for row in _load_json("chambers.json"):
        if conn.execute(
            "SELECT id FROM cold_chambers WHERE chamber_code=?",
            (row["chamber_code"],),
        ).fetchone():
            continue
        conn.execute(
            """INSERT INTO cold_chambers(chamber_code,region,name,target_min,target_max,
               quota_batches,status,created_at) VALUES (?,?,?,?,?,?,?,?)""",
            (
                row["chamber_code"],
                row["region"],
                row["name"],
                float(row["target_min"]),
                float(row["target_max"]),
                int(row.get("quota_batches", 20)),
                row.get("status", "运行"),
                row.get("created_at", now_iso()),
            ),
        )


def seed_probes(conn: sqlite3.Connection) -> None:
    for row in _load_json("probes.json"):
        if conn.execute(
            "SELECT id FROM probes WHERE probe_code=?", (row["probe_code"],),
        ).fetchone():
            continue
        ch = _chamber_id(conn, row["chamber_code"])
        if not ch:
            continue
        conn.execute(
            """INSERT INTO probes(probe_code,chamber_id,model,online_status,
               calibration_due,created_at) VALUES (?,?,?,?,?,?)""",
            (
                row["probe_code"],
                ch,
                row.get("model", "T-100"),
                row.get("online_status", "在线"),
                row["calibration_due"],
                row.get("created_at", now_iso()),
            ),
        )


def seed_batches(conn: sqlite3.Connection) -> None:
    for row in _load_json("batches.json"):
        if conn.execute(
            "SELECT id FROM temp_batches WHERE batch_code=?", (row["batch_code"],),
        ).fetchone():
            continue
        ch = _chamber_id(conn, row["chamber_code"])
        probe = conn.execute(
            "SELECT id FROM probes WHERE probe_code=?", (row["probe_code"],),
        ).fetchone()
        if not ch or not probe:
            continue
        points = row.get("temp_points", [])
        conn.execute(
            """INSERT INTO temp_batches(batch_code,chamber_id,probe_id,cargo_ref,
               temp_points,generation,status,min_observed,max_observed,created_at,sealed_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                row["batch_code"],
                ch,
                probe["id"],
                row.get("cargo_ref", "未命名货载"),
                json.dumps(points, ensure_ascii=False),
                int(row.get("generation", 1)),
                row.get("status", "草稿"),
                row.get("min_observed"),
                row.get("max_observed"),
                row.get("created_at", now_iso()),
                row.get("sealed_at"),
            ),
        )


def seed_excursions(conn: sqlite3.Connection) -> None:
    for row in _load_json("excursions.json"):
        batch = conn.execute(
            "SELECT id FROM temp_batches WHERE batch_code=?", (row["batch_code"],),
        ).fetchone()
        if not batch:
            continue
        exists = conn.execute(
            "SELECT id FROM excursion_cursors WHERE cursor_key=?",
            (row["cursor_key"],),
        ).fetchone()
        if exists:
            continue
        conn.execute(
            """INSERT INTO excursion_cursors(batch_id,cursor_key,peak_temp,threshold,
               status,opened_at,closed_at,note) VALUES (?,?,?,?,?,?,?,?)""",
            (
                batch["id"],
                row["cursor_key"],
                float(row["peak_temp"]),
                float(row["threshold"]),
                row.get("status", "开放"),
                row["opened_at"],
                row.get("closed_at"),
                row.get("note", ""),
            ),
        )


def seed_calibrations(conn: sqlite3.Connection) -> None:
    for row in _load_json("calibrations.json"):
        probe = conn.execute(
            "SELECT id FROM probes WHERE probe_code=?", (row["probe_code"],),
        ).fetchone()
        if not probe:
            continue
        conn.execute(
            """INSERT INTO calibration_records(probe_id,calibrated_at,offset_c,
               valid_until,officer,status) VALUES (?,?,?,?,?,?)""",
            (
                probe["id"],
                row["calibrated_at"],
                float(row["offset_c"]),
                row["valid_until"],
                row.get("officer", "质检员"),
                row.get("status", "有效"),
            ),
        )


def seed_routes(conn: sqlite3.Connection) -> None:
    for row in _load_json("routes.json"):
        if conn.execute(
            "SELECT id FROM route_plans WHERE route_code=?", (row["route_code"],),
        ).fetchone():
            continue
        conn.execute(
            """INSERT INTO route_plans(route_code,origin_region,dest_region,cold_hours,
               vehicle_type,status,created_at) VALUES (?,?,?,?,?,?,?)""",
            (
                row["route_code"],
                row["origin_region"],
                row["dest_region"],
                float(row["cold_hours"]),
                row.get("vehicle_type", "冷藏车"),
                row.get("status", "启用"),
                row.get("created_at", now_iso()),
            ),
        )


def seed_lineage_samples(conn: sqlite3.Connection) -> None:
    batches = conn.execute(
        "SELECT id, batch_code FROM temp_batches ORDER BY id LIMIT 3"
    ).fetchall()
    if len(batches) < 2:
        return
    n = conn.execute("SELECT COUNT(*) c FROM lineage_edges").fetchone()["c"]
    if n:
        return
    conn.execute(
        """INSERT INTO lineage_edges(from_batch_id,to_batch_id,edge_type,detail,created_at)
           VALUES (?,?,?,?,?)""",
        (
            batches[0]["id"],
            batches[1]["id"],
            "分装衍生",
            f"{batches[0]['batch_code']} 抽样转至 {batches[1]['batch_code']}",
            now_iso(),
        ),
    )


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)
        seed_users(conn)
        seed_chambers(conn)
        seed_probes(conn)
        seed_batches(conn)
        seed_excursions(conn)
        seed_calibrations(conn)
        seed_routes(conn)
        seed_lineage_samples(conn)
        conn.commit()


def dashboard_stats(conn: sqlite3.Connection) -> dict:
    chambers = conn.execute("SELECT COUNT(*) c FROM cold_chambers").fetchone()["c"]
    probes = conn.execute("SELECT COUNT(*) c FROM probes").fetchone()["c"]
    batches = conn.execute("SELECT COUNT(*) c FROM temp_batches").fetchone()["c"]
    open_exc = conn.execute(
        "SELECT COUNT(*) c FROM excursion_cursors WHERE status='开放'"
    ).fetchone()["c"]
    sealed = conn.execute(
        "SELECT COUNT(*) c FROM temp_batches WHERE status='已封批'"
    ).fetchone()["c"]
    exports = conn.execute(
        "SELECT COUNT(*) c FROM spectrum_exports WHERE status='已导出'"
    ).fetchone()["c"]
    stubs = {
        "carrier_ingest_jobs": conn.execute(
            "SELECT COUNT(*) c FROM carrier_ingest_jobs"
        ).fetchone()["c"],
        "thaw_event_jobs": conn.execute(
            "SELECT COUNT(*) c FROM thaw_event_jobs"
        ).fetchone()["c"],
    }
    overdue = conn.execute(
        """SELECT COUNT(*) c FROM probes
           WHERE calibration_due < date('now') AND online_status!='停用'"""
    ).fetchone()["c"]
    return {
        "chambers": chambers,
        "probes": probes,
        "batches": batches,
        "open_excursions": open_exc,
        "sealed_batches": sealed,
        "spectrum_exports": exports,
        "calibration_overdue": overdue,
        "stubs": stubs,
        "meta": PRODUCT_META,
    }