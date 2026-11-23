"""BUGFIX-15：解冻空桩与封批态写库甲乙分叉钉牢，两边不得混用。

本文件先落种子夹具与三红测：
- 甲路径：空桩事件不得改封批正式字段，封批表零改，只登记任务行。
- 乙路径：影子进度未晋升则封批不得开（此处校验封批正式字段零改、无晋升）。
- 争用：两值班同批抢提交，后到只写争用痕，不改封批态。
修复前这三条应见红。
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app import app
from db import FIXTURES, connect, init_db

SEED = json.loads((FIXTURES / "thaw_bug_seed.json").read_text(encoding="utf-8"))
STUB_TRACK_DEVIATION = SEED["fixed_signature"]["cross_track_deviation"]


@pytest.fixture(autouse=True)
def _db(tmp_path, monkeypatch):
    monkeypatch.setattr("db.DB_PATH", tmp_path / "t.db")
    init_db()
    yield


def _auth(c: TestClient, user: str = "admin") -> dict:
    tok = c.post(
        "/api/login", json={"username": user, "password": "123456"}
    ).json()["token"]
    return {"Authorization": "Bearer " + tok}


def _formal(batch_id: int) -> dict:
    """封批正式字段快照：status / sealed_at / generation / 快照数。"""
    with connect() as conn:
        row = conn.execute(
            "SELECT status, sealed_at, generation FROM temp_batches WHERE id=?",
            (batch_id,),
        ).fetchone()
        seals = conn.execute(
            "SELECT COUNT(*) c FROM seal_snapshots WHERE batch_id=?", (batch_id,)
        ).fetchone()["c"]
    return {
        "status": row["status"],
        "sealed_at": row["sealed_at"],
        "generation": int(row["generation"]),
        "seals": int(seals),
    }


@pytest.fixture
def thaw_bug_seed():
    """种子夹具：经真实入库→封批流程造出一张已封批批次，供空桩误触复现。"""
    c = TestClient(app)
    h = _auth(c)
    seed = SEED["seed"]
    ch = next(
        x
        for x in c.get("/api/chambers", headers=h).json()["items"]
        if x["chamber_code"] == seed["chamber_code"]
    )
    probes = c.get(f"/api/probes?chamber_id={ch['id']}", headers=h).json()["items"]
    probe = next(p for p in probes if p["probe_code"] == seed["probe_code"])
    made = c.post(
        "/api/batches",
        headers=h,
        json={
            "chamber_id": ch["id"],
            "probe_id": probe["id"],
            "cargo_ref": seed["cargo_ref"],
            "batch_code": seed["batch_code"],
            "temp_points": seed["temp_points"],
        },
    )
    assert made.status_code == 200, made.text
    batch_id = made.json()["id"]
    sealed = c.post("/api/seals", headers=h, json={"batch_id": batch_id})
    assert sealed.status_code == 200, sealed.text
    assert sealed.json()["status"] == "已封批"
    assert _formal(batch_id)["status"] == "已封批"
    return {"client": c, "headers": h, "batch_id": batch_id}


def test_A_stub_pending_batch_stays_sealed(thaw_bug_seed):
    """甲：桩待办，封批视图仍锁——空桩不得写封批正式字段。"""
    c = thaw_bug_seed["client"]
    h = thaw_bug_seed["headers"]
    bid = thaw_bug_seed["batch_id"]

    r = c.post(
        "/api/thaw-stub",
        headers=h,
        json={"batch_id": bid, **SEED["stub_request"]},
    )
    assert r.status_code == 200, r.text
    assert r.json()["batch_unchanged"] is True
    assert r.json()["seal_writes"] == 0

    jobs = [
        j
        for j in c.get("/api/thaw/jobs", headers=h).json()["items"]
        if j["batch_id"] == bid
    ]
    assert jobs, "空桩任务行未登记"
    assert jobs[0]["status"] == SEED["fixed_signature"]["thaw_job_status"]

    batch = c.get(f"/api/batches/{bid}", headers=h).json()["batch"]
    assert batch["status"] == "已封批"
    assert batch["sealed_at"] is not None
    seals = c.get("/api/seals", headers=h).json()["items"]
    assert any(s["batch_id"] == bid for s in seals)


def test_B_shadow_not_promoted_seal_not_unsealed(thaw_bug_seed):
    """乙：影子进度未晋升，封批正式字段必须零改，不得被写成已解封。"""
    c = thaw_bug_seed["client"]
    h = thaw_bug_seed["headers"]
    bid = thaw_bug_seed["batch_id"]

    before = _formal(bid)
    assert before["status"] == "已封批"

    r = c.post(
        "/api/thaw-stub",
        headers=h,
        json={"batch_id": bid, **SEED["stub_request"]},
    )
    assert r.status_code == 200, r.text

    after = _formal(bid)
    assert after == before, "空桩改动封批正式字段"
    assert after["status"] == "已封批"
    assert after["sealed_at"] == before["sealed_at"]
    assert after["seals"] == before["seals"]

    with connect() as conn:
        promoted = conn.execute(
            """SELECT COUNT(*) c FROM thaw_event_jobs
               WHERE batch_id=? AND status IN ('已晋升','晋升')""",
            (bid,),
        ).fetchone()["c"]
    assert promoted == 0, "未闭环却晋升影子进度"


def test_contention_two_submit_same_batch(thaw_bug_seed):
    """争用：两路提交抢同批，后者只写争用痕，不改封批态、不建任务。"""
    c = thaw_bug_seed["client"]
    h = thaw_bug_seed["headers"]
    bid = thaw_bug_seed["batch_id"]
    key = f"thaw:batch:{bid}"

    # 第一路已在职并占住任务锁
    ops = _auth(c, "ops")
    assert (
        c.post("/api/locks/acquire", headers=ops, json={"lock_key": key}).status_code
        == 200
    )

    before = _formal(bid)
    later = c.post(
        "/api/thaw-stub",
        headers=h,
        json={"batch_id": bid, "thaw_minutes": 30, "mode": "卸货口"},
    )
    assert later.status_code == 409, later.text
    assert _formal(bid) == before

    cont = c.get("/api/contention", headers=h).json()["items"]
    assert any(x["lock_key"] == key for x in cont), "争用未留痕"

    jobs = [
        j
        for j in c.get("/api/thaw/jobs", headers=h).json()["items"]
        if j["batch_id"] == bid
    ]
    assert jobs == [], "后到争用不得写业务"


def test_cross_track_write_rejected(thaw_bug_seed):
    """偏航：任何试图写封批正式字段的空桩请求记偏航并拒写。"""
    c = thaw_bug_seed["client"]
    h = thaw_bug_seed["headers"]
    bid = thaw_bug_seed["batch_id"]

    before = _formal(bid)
    r = c.post(
        "/api/thaw-stub",
        headers=h,
        json={"batch_id": bid, "thaw_minutes": 30, "mode": "解封"},
    )
    assert r.status_code == 409, r.text
    assert STUB_TRACK_DEVIATION in r.json()["detail"]
    assert _formal(bid) == before

    with connect() as conn:
        dev = conn.execute(
            """SELECT COUNT(*) c FROM audit_trail
               WHERE action='thaw_stub_track_deviation'"""
        ).fetchone()["c"]
    assert dev >= 1


def test_five_faces_same_source(thaw_bug_seed):
    """五面同源：批次/封存/温谱/排程/任务视图共用同一批次态。"""
    c = thaw_bug_seed["client"]
    h = thaw_bug_seed["headers"]
    bid = thaw_bug_seed["batch_id"]

    c.post(
        "/api/thaw-stub",
        headers=h,
        json={"batch_id": bid, **SEED["stub_request"]},
    )
    st = c.get(f"/api/state/{bid}", headers=h).json()
    assert st["consistent"] is True
    assert st["sealed"] is True
    assert st["thaw_pending"] >= 1
    assert st["promoted_progress"] == 0
    assert st["faces"]["seal"]["sealed"] is True
    assert st["faces"]["batch"]["status"] == st["faces"]["task"]["status"]

    everything = c.get("/api/state", headers=h).json()
    assert everything["summary"]["consistent"] == everything["summary"]["total"]

    sched = c.get("/api/routes/schedule", headers=h)
    assert sched.status_code == 200
    assert "items" in sched.json()
