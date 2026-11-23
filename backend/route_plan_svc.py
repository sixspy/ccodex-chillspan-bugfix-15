"""冷链线路计划。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from auth import AuthHeader, require_user, require_writer
from db import connect, now_iso, write_audit
from models import RouteIn

router = APIRouter(tags=["routes"])


@router.get("/api/routes")
def list_routes(authorization: AuthHeader = None):
    require_user(authorization)
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM route_plans ORDER BY id"
        ).fetchall()
        return {"items": [dict(r) for r in rows]}


@router.get("/api/routes/{route_id}")
def get_route(route_id: int, authorization: AuthHeader = None):
    require_user(authorization)
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM route_plans WHERE id=?", (route_id,)
        ).fetchone()
        if not row:
            raise HTTPException(404, "线路不存在")
        return dict(row)


@router.post("/api/routes")
def create_route(body: RouteIn, authorization: AuthHeader = None):
    user = require_writer(authorization)
    with connect() as conn:
        if conn.execute(
            "SELECT id FROM route_plans WHERE route_code=?", (body.route_code,)
        ).fetchone():
            raise HTTPException(409, "线路编码已存在")
        cur = conn.execute(
            """INSERT INTO route_plans(route_code,origin_region,dest_region,cold_hours,
               vehicle_type,status,created_at) VALUES (?,?,?,?,?,?,?)""",
            (
                body.route_code,
                body.origin_region,
                body.dest_region,
                body.cold_hours,
                body.vehicle_type,
                "启用",
                now_iso(),
            ),
        )
        write_audit(conn, user, "route_create", body.route_code, {"id": cur.lastrowid})
        conn.commit()
        return {"id": cur.lastrowid, "route_code": body.route_code, "status": "启用"}