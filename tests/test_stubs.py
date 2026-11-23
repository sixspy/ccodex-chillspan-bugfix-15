import pytest
from fastapi.testclient import TestClient

from app import app
from db import connect, init_db


@pytest.fixture(autouse=True)
def _db(tmp_path, monkeypatch):
    monkeypatch.setattr("db.DB_PATH", tmp_path / "t.db")
    init_db()
    yield


def _auth(c: TestClient) -> dict:
    tok = c.post(
        "/api/login", json={"username": "admin", "password": "123456"}
    ).json()["token"]
    return {"Authorization": "Bearer " + tok}


def test_carrier_ingest_stub_no_batch_change():
    c = TestClient(app)
    h = _auth(c)
    with connect() as conn:
        before = conn.execute("SELECT COUNT(*) c FROM temp_batches").fetchone()["c"]
    r = c.post(
        "/api/carrier-ingest-stub",
        headers=h,
        json={"carrier_name": "顺 Cold 物流", "row_count": 120, "mode": "CSV"},
    )
    assert r.status_code == 200
    assert r.json()["batches_unchanged"] is True
    with connect() as conn:
        after = conn.execute("SELECT COUNT(*) c FROM temp_batches").fetchone()["c"]
    assert after == before
    jobs = c.get("/api/carrier-ingest/jobs", headers=h).json()["items"]
    assert any(j["status"] == "空桩登记" for j in jobs)


def test_thaw_stub_no_status_change():
    c = TestClient(app)
    h = _auth(c)
    batch = c.get("/api/batches", headers=h).json()["items"][0]
    before_status = batch["status"]
    r = c.post(
        "/api/thaw-stub",
        headers=h,
        json={"batch_id": batch["id"], "thaw_minutes": 30, "mode": "卸货口"},
    )
    assert r.status_code == 200
    assert r.json()["batch_unchanged"] is True
    after = c.get(f"/api/batches/{batch['id']}", headers=h).json()["batch"]
    assert after["status"] == before_status