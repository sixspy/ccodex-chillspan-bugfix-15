"""冷链温谱管道 — FastAPI 入口。"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from audit_svc import router as audit_router
from auth import router as auth_router
from batches_svc import router as batches_router
from calibration_svc import router as calibration_router
from carrier_ingest_svc import router as carrier_router
from chambers_svc import router as chambers_router
from db import FRONTEND, PRODUCT_META, init_db
from excursions_svc import router as excursions_router
from lineage_svc import router as lineage_router
from locks import router as locks_router
from probes_svc import router as probes_router
from reconcile_svc import router as reconcile_router
from route_plan_svc import router as routes_router
from seal_svc import router as seal_router
from spectrum_svc import router as spectrum_router
from state_svc import router as state_router
from thaw_event_svc import router as thaw_router

PRODUCT = "冷链温谱管道"
SKELETON = PRODUCT_META["skeleton"]

app = FastAPI(title=PRODUCT, description=SKELETON)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (
    auth_router,
    chambers_router,
    probes_router,
    batches_router,
    excursions_router,
    seal_router,
    spectrum_router,
    lineage_router,
    reconcile_router,
    locks_router,
    audit_router,
    calibration_router,
    routes_router,
    carrier_router,
    thaw_router,
    state_router,
):
    app.include_router(r)


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/api/health")
def health():
    from db import DB_PATH, connect

    with connect() as conn:
        chambers = conn.execute(
            "SELECT COUNT(*) c FROM cold_chambers"
        ).fetchone()["c"]
        probes = conn.execute("SELECT COUNT(*) c FROM probes").fetchone()["c"]
        batches = conn.execute(
            "SELECT COUNT(*) c FROM temp_batches"
        ).fetchone()["c"]
        tables = conn.execute(
            "SELECT COUNT(*) c FROM sqlite_master WHERE type='table'"
        ).fetchone()["c"]
    return {
        "ok": True,
        "product": PRODUCT,
        "skeleton": SKELETON,
        "chambers": chambers,
        "probes": probes,
        "batches": batches,
        "tables": tables,
        "db": str(DB_PATH),
        "meta": PRODUCT_META,
    }


@app.get("/")
def index():
    return FileResponse(FRONTEND / "index.html")


app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")