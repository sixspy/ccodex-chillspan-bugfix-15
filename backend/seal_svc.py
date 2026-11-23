"""封批升代 + 快照清单。"""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from auth import AuthHeader, require_user, require_writer
from db import connect, now_iso, write_audit
from locks import release, require_lock
from models import SealIn
from validators import require_calibration_fresh, validate_batch_sealable

router = APIRouter(tags=["seal"])


@router.get("/api/seals")
def list_seals(authorization: AuthHeader = None):
    require_user(authorization)
    with connect() as conn:
        rows = conn.execute(
            """SELECT s.*, b.batch_code FROM seal_snapshots s
               JOIN temp_batches b ON b.id=s.batch_id ORDER BY s.id DESC"""
        ).fetchall()
        return {"items": [dict(r) for r in rows]}


@router.post("/api/seals")
def seal_batch(body: SealIn, authorization: AuthHeader = None):
    user = require_writer(authorization)
    lock_key = f"batch:{body.batch_id}"
    with connect() as conn:
        require_lock(conn, lock_key, user)
        try:
            batch = conn.execute(
                """SELECT b.*, p.calibration_due, p.probe_code
                   FROM temp_batches b JOIN probes p ON p.id=b.probe_id
                   WHERE b.id=?""",
                (body.batch_id,),
            ).fetchone()
            if not batch:
                raise HTTPException(404, "批次不存在")
            open_exc = conn.execute(
                """SELECT COUNT(*) c FROM excursion_cursors
                   WHERE batch_id=? AND status='开放'""",
                (body.batch_id,),
            ).fetchone()["c"]
            bdict = dict(batch)
            bdict["temp_points"] = batch["temp_points"]
            validate_batch_sealable(bdict, open_exc)
            require_calibration_fresh(batch)
            gen = int(batch["generation"])
            manifest = body.manifest or json.dumps(
                {
                    "batch_code": batch["batch_code"],
                    "generation": gen + 1,
                    "point_count": len(json.loads(batch["temp_points"] or "[]")),
                    "min": batch["min_observed"],
                    "max": batch["max_observed"],
                },
                ensure_ascii=False,
            )
            now = now_iso()
            cur = conn.execute(
                """INSERT INTO seal_snapshots(batch_id,batch_generation,manifest,status,sealed_at)
                   VALUES (?,?,?,?,?)""",
                (body.batch_id, gen + 1, manifest, "已封批", now),
            )
            conn.execute(
                """UPDATE temp_batches SET status='已封批', generation=generation+1,
                   sealed_at=? WHERE id=?""",
                (now, body.batch_id),
            )
            write_audit(
                conn,
                user,
                "batch_seal",
                batch["batch_code"],
                {"seal_id": cur.lastrowid, "generation": gen + 1},
            )
            conn.commit()
            return {
                "seal_id": cur.lastrowid,
                "batch_code": batch["batch_code"],
                "generation": gen + 1,
                "status": "已封批",
            }
        finally:
            release(conn, lock_key, user)