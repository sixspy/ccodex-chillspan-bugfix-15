"""同源态：批次 / 封存 / 曲线 / 排程 / 任务五面同一批次态只读投影。

五处视图一律从本模块 `batch_state()` 取态，禁止各页自行拼封批正式字段，
以免空桩隔轨偏航造成「桩未结、封批已开」的态串写。
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from auth import AuthHeader, require_user
from db import connect

router = APIRouter(tags=["state"])

THAW_PENDING = "空桩待办"
PROMOTED_STATUSES = ("已晋升", "晋升")


def batch_state(conn, batch_id: int) -> dict | None:
    """单一读取口：批次态 + 五面投影 + 一致性判定。"""
    row = conn.execute(
        "SELECT * FROM temp_batches WHERE id=?", (batch_id,)
    ).fetchone()
    if not row:
        return None
    bid = int(row["id"])
    seals = conn.execute(
        "SELECT * FROM seal_snapshots WHERE batch_id=? ORDER BY id DESC", (bid,)
    ).fetchall()
    exports = conn.execute(
        """SELECT COUNT(*) c FROM spectrum_exports
           WHERE batch_id=? AND status='已导出'""",
        (bid,),
    ).fetchone()["c"]
    jobs = conn.execute(
        "SELECT * FROM thaw_event_jobs WHERE batch_id=? ORDER BY id DESC", (bid,)
    ).fetchall()
    thaw_pending = sum(1 for j in jobs if j["status"] == THAW_PENDING)
    promoted = sum(1 for j in jobs if j["status"] in PROMOTED_STATUSES)
    routes = conn.execute("SELECT COUNT(*) c FROM route_plans").fetchone()["c"]

    status = row["status"]
    sealed = status == "已封批"

    batch_face = {
        "face": "batch",
        "batch_id": bid,
        "batch_code": row["batch_code"],
        "status": status,
        "sealed": sealed,
        "generation": int(row["generation"]),
        "sealed_at": row["sealed_at"],
    }
    seal_face = {
        "face": "seal",
        "status": status,
        "sealed": sealed,
        "snapshots": len(seals),
        "latest_generation": seals[0]["batch_generation"] if seals else None,
    }
    spectrum_face = {
        "face": "spectrum",
        "status": status,
        "sealed": sealed,
        "exports": int(exports),
        "exportable": sealed,
    }
    schedule_face = {
        "face": "schedule",
        "status": status,
        "sealed": sealed,
        "routes": int(routes),
    }
    task_face = {
        "face": "task",
        "status": status,
        "sealed": sealed,
        "thaw_pending": int(thaw_pending),
        "promoted_progress": int(promoted),
        "jobs": len(jobs),
    }

    faces = {
        "batch": batch_face,
        "seal": seal_face,
        "spectrum": spectrum_face,
        "schedule": schedule_face,
        "task": task_face,
    }
    statuses = {f["status"] for f in faces.values()}
    sealed_flags = {f["sealed"] for f in faces.values()}
    consistent = len(statuses) == 1 and len(sealed_flags) == 1
    return {
        "batch_id": bid,
        "batch_code": row["batch_code"],
        "status": status,
        "sealed": sealed,
        "generation": int(row["generation"]),
        "sealed_at": row["sealed_at"],
        "thaw_pending": int(thaw_pending),
        "promoted_progress": int(promoted),
        "consistent": bool(consistent),
        "faces": faces,
    }


def all_states(conn) -> list[dict]:
    rows = conn.execute("SELECT id FROM temp_batches ORDER BY id").fetchall()
    return [s for s in (batch_state(conn, r["id"]) for r in rows) if s]


@router.get("/api/state")
def state_all(authorization: AuthHeader = None):
    require_user(authorization)
    with connect() as conn:
        items = all_states(conn)
        consistent = sum(1 for s in items if s["consistent"])
        return {
            "items": items,
            "summary": {
                "total": len(items),
                "consistent": consistent,
                "inconsistent": len(items) - consistent,
            },
        }


@router.get("/api/state/{batch_id}")
def state_one(batch_id: int, authorization: AuthHeader = None):
    require_user(authorization)
    with connect() as conn:
        st = batch_state(conn, batch_id)
        if not st:
            raise HTTPException(404, "批次不存在")
        return st
