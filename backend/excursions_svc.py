"""超温游标开闭。"""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from auth import AuthHeader, require_user, require_writer
from db import connect, now_iso, write_audit
from locks import release, require_lock
from models import ExcursionCloseIn, ExcursionOpenIn
from validators import detect_excursion

router = APIRouter(tags=["excursions"])


@router.get("/api/excursions")
def list_excursions(authorization: AuthHeader = None, status: str | None = None):
    require_user(authorization)
    with connect() as conn:
        q = """SELECT e.*, b.batch_code FROM excursion_cursors e
               JOIN temp_batches b ON b.id=e.batch_id"""
        if status:
            rows = conn.execute(
                q + " WHERE e.status=? ORDER BY e.id DESC", (status,)
            ).fetchall()
        else:
            rows = conn.execute(q + " ORDER BY e.id DESC").fetchall()
        return {"items": [dict(r) for r in rows]}


@router.post("/api/excursions/open")
def open_excursion(body: ExcursionOpenIn, authorization: AuthHeader = None):
    user = require_writer(authorization)
    lock_key = f"batch:{body.batch_id}"
    with connect() as conn:
        require_lock(conn, lock_key, user)
        try:
            batch = conn.execute(
                "SELECT * FROM temp_batches WHERE id=?", (body.batch_id,)
            ).fetchone()
            if not batch:
                raise HTTPException(404, "批次不存在")
            if batch["status"] == "已封批":
                raise HTTPException(409, "已封批禁止开游标")
            open_n = conn.execute(
                """SELECT COUNT(*) c FROM excursion_cursors
                   WHERE batch_id=? AND status='开放'""",
                (body.batch_id,),
            ).fetchone()["c"]
            if open_n:
                raise HTTPException(409, "已有开放游标")
            ch = conn.execute(
                "SELECT target_max FROM cold_chambers WHERE id=?",
                (batch["chamber_id"],),
            ).fetchone()
            threshold = float(body.threshold if body.threshold is not None else ch["target_max"] + 2)
            points = json.loads(batch["temp_points"] or "[]")
            peak = detect_excursion(points, threshold)
            if peak is None:
                raise HTTPException(422, "温度点未超阈，无需开游标")
            key = f"EX-{batch['batch_code']}-{open_n + 1}"
            now = now_iso()
            cur = conn.execute(
                """INSERT INTO excursion_cursors(batch_id,cursor_key,peak_temp,threshold,
                   status,opened_at,note) VALUES (?,?,?,?,?,?,?)""",
                (body.batch_id, key, peak, threshold, "开放", now, body.note),
            )
            conn.execute(
                "UPDATE temp_batches SET status='超温处理中' WHERE id=?",
                (body.batch_id,),
            )
            write_audit(
                conn,
                user,
                "excursion_open",
                key,
                {"batch_id": body.batch_id, "peak": peak},
            )
            conn.commit()
            return {"id": cur.lastrowid, "cursor_key": key, "peak_temp": peak, "status": "开放"}
        finally:
            release(conn, lock_key, user)


@router.post("/api/excursions/close")
def close_excursion(body: ExcursionCloseIn, authorization: AuthHeader = None):
    user = require_writer(authorization)
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM excursion_cursors WHERE id=?", (body.cursor_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "游标不存在")
        if row["status"] != "开放":
            raise HTTPException(409, "游标已关闭")
        now = now_iso()
        conn.execute(
            """UPDATE excursion_cursors SET status='已闭', closed_at=?, note=?
               WHERE id=?""",
            (now, body.note or row["note"], body.cursor_id),
        )
        open_left = conn.execute(
            """SELECT COUNT(*) c FROM excursion_cursors
               WHERE batch_id=? AND status='开放'""",
            (row["batch_id"],),
        ).fetchone()["c"]
        if open_left == 0:
            conn.execute(
                "UPDATE temp_batches SET status='已入库' WHERE id=? AND status='超温处理中'",
                (row["batch_id"],),
            )
        write_audit(conn, user, "excursion_close", row["cursor_key"], {})
        conn.commit()
        return {"id": body.cursor_id, "status": "已闭", "closed_at": now}