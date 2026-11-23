"""探头登记与在线态。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from auth import AuthHeader, require_user, require_writer
from db import connect, now_iso, write_audit
from models import ProbeIn

router = APIRouter(tags=["probes"])


@router.get("/api/probes")
def list_probes(authorization: AuthHeader = None, chamber_id: int | None = None):
    require_user(authorization)
    with connect() as conn:
        if chamber_id:
            rows = conn.execute(
                """SELECT p.*, c.chamber_code, c.region FROM probes p
                   JOIN cold_chambers c ON c.id=p.chamber_id
                   WHERE p.chamber_id=? ORDER BY p.id""",
                (chamber_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT p.*, c.chamber_code, c.region FROM probes p
                   JOIN cold_chambers c ON c.id=p.chamber_id ORDER BY p.id"""
            ).fetchall()
        return {"items": [dict(r) for r in rows]}


@router.get("/api/probes/{probe_id}")
def get_probe(probe_id: int, authorization: AuthHeader = None):
    require_user(authorization)
    with connect() as conn:
        row = conn.execute(
            """SELECT p.*, c.name chamber_name, c.target_min, c.target_max
               FROM probes p JOIN cold_chambers c ON c.id=p.chamber_id
               WHERE p.id=?""",
            (probe_id,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "探头不存在")
        cals = conn.execute(
            "SELECT * FROM calibration_records WHERE probe_id=? ORDER BY id DESC",
            (probe_id,),
        ).fetchall()
        return {"probe": dict(row), "calibrations": [dict(x) for x in cals]}


@router.post("/api/probes")
def register_probe(body: ProbeIn, authorization: AuthHeader = None):
    user = require_writer(authorization)
    with connect() as conn:
        ch = conn.execute(
            "SELECT id FROM cold_chambers WHERE id=?", (body.chamber_id,)
        ).fetchone()
        if not ch:
            raise HTTPException(404, "仓间不存在")
        if conn.execute(
            "SELECT id FROM probes WHERE probe_code=?", (body.probe_code,)
        ).fetchone():
            raise HTTPException(409, "探头编码已存在")
        cur = conn.execute(
            """INSERT INTO probes(probe_code,chamber_id,model,online_status,
               calibration_due,created_at) VALUES (?,?,?,?,?,?)""",
            (
                body.probe_code,
                body.chamber_id,
                body.model,
                "在线",
                body.calibration_due,
                now_iso(),
            ),
        )
        write_audit(conn, user, "probe_register", body.probe_code, {"id": cur.lastrowid})
        conn.commit()
        return {"id": cur.lastrowid, "probe_code": body.probe_code, "online_status": "在线"}


@router.post("/api/probes/{probe_id}/offline")
def set_offline(probe_id: int, authorization: AuthHeader = None):
    user = require_writer(authorization)
    with connect() as conn:
        row = conn.execute("SELECT * FROM probes WHERE id=?", (probe_id,)).fetchone()
        if not row:
            raise HTTPException(404, "探头不存在")
        conn.execute(
            "UPDATE probes SET online_status='离线' WHERE id=?", (probe_id,)
        )
        write_audit(conn, user, "probe_offline", row["probe_code"], {})
        conn.commit()
        return {"id": probe_id, "online_status": "离线"}