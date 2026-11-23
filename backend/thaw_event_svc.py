"""解冻事件空桩：甲轨——只登记任务行与审计，封批正式字段零改。

口径（BUGFIX-15）：
- 甲轨：空桩事件不得改封批正式字段；temp_batches / seal_snapshots 零改，
  只登记 thaw_event_jobs 任务行。
- 同批次提交须串行占任务锁 thaw:batch:<id>，后到者只写争用痕，不改封批态、不建任务。
- 任何试图写封批正式字段（解封/封批/解封口令）的空桩请求记「空桩隔轨偏航」并拒写。
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from auth import AuthHeader, require_writer
from db import connect, now_iso, write_audit
from locks import release, try_acquire
from models import ThawStubIn

router = APIRouter(tags=["stubs"])

THAW_TRACK = "甲"
JOB_PENDING = "空桩待办"
CROSS_TRACK_MARKERS = ("解封", "封批", "unseal", "unlock_seal", "seal")


def _formal(conn, batch_id: int) -> dict | None:
    """封批正式字段快照（空桩只读、不得改写）。"""
    row = conn.execute(
        "SELECT status, sealed_at, generation FROM temp_batches WHERE id=?",
        (batch_id,),
    ).fetchone()
    if not row:
        return None
    return {
        "status": row["status"],
        "sealed_at": row["sealed_at"],
        "generation": int(row["generation"]),
    }


def _is_cross_track(body: ThawStubIn) -> bool:
    hay = f"{body.mode}".lower()
    return any(marker in hay for marker in CROSS_TRACK_MARKERS)


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

    # 隔轨拒写：任何想触封批正式字段的空桩请求，记偏航并立即拒绝。
    if _is_cross_track(body):
        with connect() as conn:
            write_audit(
                conn,
                user,
                "thaw_stub_track_deviation",
                str(body.batch_id or "none"),
                {
                    "track": THAW_TRACK,
                    "mode": body.mode,
                    "reason": "空桩隔轨偏航",
                },
            )
            conn.commit()
        raise HTTPException(
            409,
            f"空桩隔轨偏航：{THAW_TRACK}轨只登记任务行，禁止写封批正式字段",
        )

    lock_key = f"thaw:batch:{body.batch_id}" if body.batch_id else None
    with connect() as conn:
        if lock_key:
            if not try_acquire(conn, lock_key, user):
                # 后到争用：只写争用痕与审计，不改封批态、不建任务。
                write_audit(
                    conn,
                    user,
                    "thaw_stub_contention",
                    str(body.batch_id),
                    {"lock_key": lock_key, "track": THAW_TRACK},
                )
                conn.commit()
                raise HTTPException(409, "争用：后到只记争用，不写业务")
        try:
            before = _formal(conn, body.batch_id) if body.batch_id else None
            if body.batch_id and before is None:
                raise HTTPException(404, "批次不存在")
            cur = conn.execute(
                """INSERT INTO thaw_event_jobs(batch_id,thaw_minutes,mode,status,detail,created_at)
                   VALUES (?,?,?,?,?,?)""",
                (
                    body.batch_id,
                    body.thaw_minutes,
                    body.mode,
                    JOB_PENDING,
                    "甲轨：只登记任务行，封批正式字段零改",
                    now_iso(),
                ),
            )
            after = _formal(conn, body.batch_id) if body.batch_id else None
            batch_unchanged = (before == after) if body.batch_id else True
            write_audit(
                conn,
                user,
                "thaw_stub",
                str(body.batch_id or "none"),
                {
                    "job_id": cur.lastrowid,
                    "track": THAW_TRACK,
                    "seal_writes": 0,
                },
            )
            conn.commit()
            result = {
                "job_id": cur.lastrowid,
                "status": JOB_PENDING,
                "batch_unchanged": batch_unchanged,
                "seal_writes": 0,
                "track": THAW_TRACK,
            }
        finally:
            if lock_key:
                release(conn, lock_key, user)
                conn.commit()
    return result
