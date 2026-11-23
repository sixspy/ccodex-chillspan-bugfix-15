"""承运商批量导入空桩：只写任务表与审计，不改主业务表。"""
from __future__ import annotations

from fastapi import APIRouter

from auth import AuthHeader, require_writer
from db import connect, now_iso, write_audit
from models import CarrierStubIn

router = APIRouter(tags=["stubs"])


@router.get("/api/carrier-ingest/jobs")
def list_jobs(authorization: AuthHeader = None):
    require_writer(authorization)
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM carrier_ingest_jobs ORDER BY id DESC LIMIT 100"
        ).fetchall()
        return {"items": [dict(r) for r in rows]}


@router.post("/api/carrier-ingest-stub")
def stub_ingest(body: CarrierStubIn, authorization: AuthHeader = None):
    user = require_writer(authorization)
    with connect() as conn:
        before_batches = conn.execute(
            "SELECT COUNT(*) c FROM temp_batches"
        ).fetchone()["c"]
        cur = conn.execute(
            """INSERT INTO carrier_ingest_jobs(carrier_name,row_count,mode,status,detail,created_at)
               VALUES (?,?,?,?,?,?)""",
            (
                body.carrier_name,
                body.row_count,
                body.mode,
                "空桩登记",
                "未写入批次主表",
                now_iso(),
            ),
        )
        after_batches = conn.execute(
            "SELECT COUNT(*) c FROM temp_batches"
        ).fetchone()["c"]
        write_audit(
            conn,
            user,
            "carrier_ingest_stub",
            body.carrier_name,
            {"job_id": cur.lastrowid, "row_count": body.row_count},
        )
        conn.commit()
        return {
            "job_id": cur.lastrowid,
            "status": "空桩登记",
            "batches_unchanged": before_batches == after_batches,
        }