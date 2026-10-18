"""Scenario config: the one contract every module reads. YAML in, validated model out."""
from datetime import datetime
from math import cos, radians
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator

from .catalog import CATALOG

UKRAINE = (44.0, 52.5, 22.0, 40.5)  # ponytail: lat/lon bbox, not the border polygon
M_PER_DEG = 111_195.0  # mean-earth metres per degree; world.py's local frame uses the same
ID = r"^[A-Za-z0-9_-][A-Za-z0-9_.-]{0,63}$"  # safe as a file name, URL segment, CoT uid and HTML text
MODULE = r"^[a-z][a-z0-9_]{0,31}$"  # sensor type = module name under mirrorworld/sensors/


class Spoof(BaseModel):
    """GNSS spoofing: the object's own GNSS fix walks away from the truth."""
    start_s: float
    end_s: float
    drift_mps: float = 6.0
    drift_deg: float = 90.0  # direction the fake position walks, degrees true


class Obj(BaseModel):
    id: str = Field(pattern=ID)
    type: str  # CATALOG key
    side: Literal["hostile", "friendly", "neutral", "unknown"] = "unknown"
    pos: tuple[float, float] | None = None  # static: (lat, lon)
    path: list[tuple[float, float, float]] | None = None  # moving: (lat, lon, alt_agl_m) waypoints
    alt_agl_m: float | None = None  # static objects; default catalog height_m
    speed_mps: float | None = None  # default catalog speed_mps
    start_s: float = 0.0
    end_s: float | None = None  # gone after this (landed, shot down, impact)
    loop: bool = False
    controls: str | None = None  # operator -> id of the drone it flies; it transmits that drone's uplinks
    remote_id: bool | None = None  # override catalog remote_id (e.g. a modded drone that stays silent)
    gnss_spoof: Spoof | None = None

    @model_validator(mode="after")
    def _shape(self):
        if self.type not in CATALOG:
            raise ValueError(f"{self.id}: unknown type {self.type!r}; known: {sorted(CATALOG)}")
        if (self.pos is None) == (self.path is None):
            raise ValueError(f"{self.id}: give exactly one of pos or path")
        if self.path is not None and len(self.path) < 2:
            raise ValueError(f"{self.id}: path needs >= 2 waypoints")
        return self


class Sensor(BaseModel):
    id: str = Field(pattern=ID)
    type: str = Field(pattern=MODULE)  # module name in mirrorworld/sensors/
    pos: tuple[float, float] | None = None  # (lat, lon) ...
    mount: str | None = None  # ... or share another sensor's site (camera on RF1's tower)
    mast_m: float = 10.0  # this sensor's own height above ground
    destroyed_by: str | None = None  # object id; the sensor goes dark when that object's track ends
    params: dict = Field(default_factory=dict)  # type-specific; each module validates its own


class Area(BaseModel):
    lat: float
    lon: float
    size_km: float = Field(16.0, gt=1, le=60)


class Weather(BaseModel):
    wind_from_deg: float = 270.0
    wind_mps: float = 3.0
    temp_c: float = 5.0
    rh_pct: float = 80.0
    visibility_km: float = 10.0
    cloud_pct: float = 60.0


class Scenario(BaseModel):
    name: str = Field(pattern=ID)
    seed: int = 0
    start: datetime  # UTC, e.g. 2026-11-03T13:55:00Z
    duration_s: float = Field(gt=0, lt=86400)
    truth_hz: float = Field(2.0, gt=0, le=20)
    area: Area
    weather: Weather = Weather()
    objects: list[Obj]
    sensors: list[Sensor]

    @model_validator(mode="after")
    def _refs(self):
        lat0, lat1, lon0, lon1 = UKRAINE
        if not (lat0 <= self.area.lat <= lat1 and lon0 <= self.area.lon <= lon1):
            raise ValueError("area centre must be in Ukraine")
        if self.start.utcoffset() is None or self.start.utcoffset().total_seconds() != 0:
            raise ValueError("start must be UTC, e.g. 2026-11-03T13:55:00Z")
        ids = [o.id for o in self.objects] + [s.id for s in self.sensors]
        if dupes := sorted({i for i in ids if ids.count(i) > 1}):
            raise ValueError(f"duplicate ids: {dupes}")
        objs, sens = {o.id for o in self.objects}, {s.id for s in self.sensors}
        for o in self.objects:
            if o.controls and o.controls not in objs:
                raise ValueError(f"{o.id}.controls -> unknown object {o.controls!r}")
            for lat, lon in [o.pos] if o.pos else [(p[0], p[1]) for p in o.path]:
                self._check_inside(o.id, lat, lon)
        for s in self.sensors:
            if (s.pos is None) == (s.mount is None):
                raise ValueError(f"{s.id}: give exactly one of pos or mount")
            if s.mount and s.mount not in sens:
                raise ValueError(f"{s.id}.mount -> unknown sensor {s.mount!r}")
            if s.destroyed_by and s.destroyed_by not in objs:
                raise ValueError(f"{s.id}.destroyed_by -> unknown object {s.destroyed_by!r}")
            if s.pos:
                self._check_inside(s.id, *s.pos)
        return self

    def _check_inside(self, who, lat, lon):
        half = self.area.size_km * 500
        dx = (lon - self.area.lon) * M_PER_DEG * cos(radians(self.area.lat))
        dy = (lat - self.area.lat) * M_PER_DEG
        if abs(dx) > half or abs(dy) > half:
            raise ValueError(f"{who} at ({lat}, {lon}) is outside the {self.area.size_km} km area")


def load(path: str | Path) -> Scenario:
    return Scenario.model_validate(yaml.safe_load(Path(path).read_text()))


def coord_label(lat: float, lon: float) -> str:
    """How a place is shown: coordinates, never names."""
    return f"{abs(lat):.4f}° {'N' if lat >= 0 else 'S'} · {abs(lon):.4f}° {'E' if lon >= 0 else 'W'}"


def coord_slug(lat: float, lon: float) -> str:
    """File/id-safe form of the same, e.g. 49.375N_31.188E."""
    return f"{abs(lat):.3f}{'N' if lat >= 0 else 'S'}_{abs(lon):.3f}{'E' if lon >= 0 else 'W'}"
