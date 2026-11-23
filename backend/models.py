"""请求体模型（冷链温谱管道）。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ChamberIn(BaseModel):
    chamber_code: str = Field(min_length=2, max_length=32)
    region: str
    name: str
    target_min: float
    target_max: float
    quota_batches: int = Field(ge=1, le=500)


class ProbeIn(BaseModel):
    probe_code: str = Field(min_length=2, max_length=32)
    chamber_id: int
    model: str = "T-100"
    calibration_due: str


class BatchIn(BaseModel):
    batch_code: str | None = None
    chamber_id: int
    probe_id: int
    cargo_ref: str
    temp_points: list[dict] = Field(default_factory=list)


class ExcursionOpenIn(BaseModel):
    batch_id: int
    threshold: float | None = None
    note: str = ""


class ExcursionCloseIn(BaseModel):
    cursor_id: int
    note: str = ""


class SealIn(BaseModel):
    batch_id: int
    manifest: str = ""


class SpectrumIn(BaseModel):
    batch_id: int


class LineageIn(BaseModel):
    from_batch_id: int
    to_batch_id: int | None = None
    edge_type: str
    detail: str


class CalibrationIn(BaseModel):
    probe_id: int
    offset_c: float
    valid_until: str
    officer: str = "质检员"


class RouteIn(BaseModel):
    route_code: str
    origin_region: str
    dest_region: str
    cold_hours: float = Field(gt=0)
    vehicle_type: str = "冷藏车"


class CarrierStubIn(BaseModel):
    carrier_name: str
    row_count: int = Field(ge=1)
    mode: str = "批量导入"


class ThawStubIn(BaseModel):
    batch_id: int | None = None
    thaw_minutes: int = Field(ge=1)
    mode: str = "解冻登记"


class LockBody(BaseModel):
    lock_key: str