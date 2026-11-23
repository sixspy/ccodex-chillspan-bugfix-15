import json

import pytest
from fastapi.testclient import TestClient

from app import app
from db import init_db


@pytest.fixture(autouse=True)
def _db(tmp_path, monkeypatch):
    monkeypatch.setattr("db.DB_PATH", tmp_path / "t.db")
    init_db()
    yield


def _auth(c: TestClient, user="admin") -> dict:
    tok = c.post(
        "/api/login", json={"username": user, "password": "123456"}
    ).json()["token"]
    return {"Authorization": "Bearer " + tok}


def test_health_and_seed():
    c = TestClient(app)
    health = c.get("/api/health").json()
    assert health["product"] == "冷链温谱管道"
    assert health["chambers"] >= 4
    assert health["probes"] >= 6
    assert health["batches"] >= 4
    assert "carrier_ingest" in health["meta"]["stubs"]


def test_inbound_excursion_seal_spectrum_flow():
    c = TestClient(app)
    h = _auth(c)
    chambers = c.get("/api/chambers", headers=h).json()["items"]
    ch = next(x for x in chambers if x["chamber_code"] == "CK-HN-03")
    probes = c.get(f"/api/probes?chamber_id={ch['id']}", headers=h).json()["items"]
    probe = probes[0]
    points = [
        {"t": "10:00", "c": 3.0},
        {"t": "11:00", "c": 8.5},
        {"t": "12:00", "c": 4.0},
    ]
    batch = c.post(
        "/api/batches",
        headers=h,
        json={
            "chamber_id": ch["id"],
            "probe_id": probe["id"],
            "cargo_ref": "流程验收货载",
            "temp_points": points,
            "batch_code": "TB-FLOW-001",
        },
    ).json()
    assert batch["status"] == "已入库"
    exc = c.post(
        "/api/excursions/open",
        headers=h,
        json={"batch_id": batch["id"], "threshold": 7.0},
    )
    assert exc.status_code == 200
    assert exc.json()["peak_temp"] >= 7.0
    c.post(
        "/api/excursions/close",
        headers=h,
        json={"cursor_id": exc.json()["id"], "note": "闭环"},
    )
    seal = c.post("/api/seals", headers=h, json={"batch_id": batch["id"]})
    assert seal.status_code == 200
    assert seal.json()["status"] == "已封批"
    sp = c.post("/api/spectrum/export", headers=h, json={"batch_id": batch["id"]})
    assert sp.status_code == 200
    assert sp.json()["point_count"] == 3
    proof = c.get("/api/proof/batch/TB-FLOW-001", headers=h).json()
    assert proof["spectrum_matches_seal"] is True
    assert proof["excursion_closed"] is True


def test_reconcile_chamber():
    c = TestClient(app)
    h = _auth(c)
    recon = c.get("/api/reconcile/CK-HD-01", headers=h).json()
    assert recon["balanced"] is True
    assert recon["quota_batches"] >= recon["active_batches"]


def test_lineage_readable():
    c = TestClient(app)
    h = _auth(c)
    edges = c.get("/api/lineage", headers=h).json()["items"]
    assert len(edges) >= 1


def test_lock_contention():
    c = TestClient(app)
    h1 = _auth(c, "admin")
    h2 = _auth(c, "ops")
    assert (
        c.post(
            "/api/locks/acquire", headers=h1, json={"lock_key": "chamber:99"}
        ).status_code
        == 200
    )
    assert (
        c.post(
            "/api/locks/acquire", headers=h2, json={"lock_key": "chamber:99"}
        ).status_code
        == 409
    )
    cont = c.get("/api/contention", headers=h1).json()["items"]
    assert any(x["lock_key"] == "chamber:99" for x in cont)


def test_viewer_readonly():
    c = TestClient(app)
    h = _auth(c, "viewer")
    assert c.get("/api/chambers", headers=h).status_code == 200
    assert (
        c.post(
            "/api/batches",
            headers=h,
            json={"chamber_id": 1, "probe_id": 1, "cargo_ref": "x", "temp_points": []},
        ).status_code
        == 403
    )


def test_calibration_and_routes():
    c = TestClient(app)
    h = _auth(c)
    cals = c.get("/api/calibrations", headers=h).json()["items"]
    assert len(cals) >= 3
    routes = c.get("/api/routes", headers=h).json()["items"]
    assert len(routes) >= 3


def test_seal_blocks_open_excursion():
    c = TestClient(app)
    h = _auth(c)
    batches = c.get("/api/batches", headers=h).json()["items"]
    sealed = [b for b in batches if b["status"] == "已封批"][0]
    assert (
        c.post(
            "/api/excursions/open",
            headers=h,
            json={"batch_id": sealed["id"]},
        ).status_code
        == 409
    )