"""温谱导出。"""
from __future__ import annotations

import hashlib
import json

from fastapi import APIRouter, HTTPException

from auth import AuthHeader, require_user, require_writer
from db import connect, now_iso, write_audit
from models import SpectrumIn

router = APIRouter(tags=["spectrum"])


@router.get("/api/spectrum")
def list_exports(authorization: AuthHeader = None):
    require_user(authorization)
    with connect() as conn:
        rows = conn.execute(
            """SELECT s.*, b.batch_code FROM spectrum_exports s
               JOIN temp_batches b ON b.id=s.batch_id ORDER BY s.id DESC"""
        ).fetchall()
        return {"items": [dict(r) for r in rows]}


@router.post("/api/spectrum/export")
def export_spectrum(body: SpectrumIn, authorization: AuthHeader = None):
    user = require_writer(authorization)
    with connect() as conn:
        batch = conn.execute(
            "SELECT * FROM temp_batches WHERE id=?", (body.batch_id,)
        ).fetchone()
        if not batch:
            raise HTTPException(404, "批次不存在")
        if batch["status"] != "已封批":
            raise HTTPException(409, "须先封批再导出温谱")
        points = json.loads(batch["temp_points"] or "[]")
        payload = json.dumps(
            {
                "batch_code": batch["batch_code"],
                "generation": batch["generation"],
                "points": points,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        checksum = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
        ref = f"SP-{batch['batch_code']}-G{batch['generation']}"
        dup = conn.execute(
            "SELECT id FROM spectrum_exports WHERE export_ref=?", (ref,)
        ).fetchone()
        if dup:
            raise HTTPException(409, "该代温谱已导出")
        cur = conn.execute(
            """INSERT INTO spectrum_exports(batch_id,export_ref,point_count,checksum,
               status,created_at) VALUES (?,?,?,?,?,?)""",
            (
                body.batch_id,
                ref,
                len(points),
                checksum,
                "已导出",
                now_iso(),
            ),
        )
        write_audit(conn, user, "spectrum_export", ref, {"checksum": checksum})
        conn.commit()
        return {
            "id": cur.lastrowid,
            "export_ref": ref,
            "point_count": len(points),
            "checksum": checksum,
            "status": "已导出",
        }


@router.get("/api/spectrum/{export_ref}")
def get_export(export_ref: str, authorization: AuthHeader = None):
    require_user(authorization)
    with connect() as conn:
        row = conn.execute(
            """SELECT s.*, b.temp_points, b.batch_code FROM spectrum_exports s
               JOIN temp_batches b ON b.id=s.batch_id WHERE s.export_ref=?""",
            (export_ref,),
        ).fetchone()
        if not row:
            raise HTTPException(404, "导出不存在")
        data = dict(row)
        data["temp_points"] = json.loads(data["temp_points"] or "[]")
        return data