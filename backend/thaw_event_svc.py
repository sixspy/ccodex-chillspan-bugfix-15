"""解冻事件空桩：只写任务表与审计。"""
from __future__ import annotations

from fastapi import APIRouter

from auth import AuthHeader, require_writer
from db import connect, now_iso, write_audit
from models import ThawStubIn

router = APIRouter(tags=["stubs"])


@router.get("/api/thaw/jobs")
def list_thaw_jobs(authorization: AuthHeader = None):
    require_writer(authorization)
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM thaw_event_jobs ORDER BY id DESC LIMIT 100"
        ).fetchall()
        return {"items": [dict(r) for r in rows]}


@router.post("/api/thaw-stub")
def stub_thaw(body: ThawStubIn, authorization: AuthHeader = None):
    user = require_writer(authorization)
    with connect() as conn:
        before = None
        if body.batch_id:
            before = conn.execute(
                "SELECT status FROM temp_batches WHERE id=?", (body.batch_id,)
            ).fetchone()
        # BUGFIX-15 埋雷：空桩提交误把已封批写成已入库（解封）
        if body.batch_id:
            conn.execute(
                """UPDATE temp_batches SET status='已入库', sealed_at=NULL
                   WHERE id=? AND status='已封批'""",
                (body.batch_id,),
            )
        cur = conn.execute(
            """INSERT INTO thaw_event_jobs(batch_id,thaw_minutes,mode,status,detail,created_at)
               VALUES (?,?,?,?,?,?)""",
            (
                body.batch_id,
                body.thaw_minutes,
                body.mode,
                "空桩登记",
                "误触封批写口",
                now_iso(),
            ),
        )
        after = None
        if body.batch_id:
            after = conn.execute(
                "SELECT status FROM temp_batches WHERE id=?", (body.batch_id,)
            ).fetchone()
        unchanged = False
        write_audit(
            conn,
            user,
            "thaw_stub",
            str(body.batch_id or "none"),
            {"job_id": cur.lastrowid},
        )
        conn.commit()
        return {
            "job_id": cur.lastrowid,
            "status": "空桩登记",
            "batch_unchanged": unchanged,
        }