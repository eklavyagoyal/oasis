"""Deterministic scenario builder: a handful of knobs plus a seed -> a full, validated Scenario YAML.

Everything geometric is computed here from the real DEM (World), never guessed: sensor sites are
greedy coverage picks on DEM maxima, drone corridors run from an edge entry point to the protected
SITE-01, and interceptor rendezvous points lie exactly on the hostile's flown path at the time it
is there. One numpy Generator seeded from (seed, sector) drives every draw in a fixed order, so the
same knobs always give byte-identical YAML.

Run: uv run python -m mirrorworld.builder --sector ros-valley --seed 1 -o scenarios/ros-valley-s1.yaml
     uv run python -m mirrorworld.builder --knobs-json '{"seed": 4, "template": "intercepted"}' --run

Templates (knob `template`):
  incoming      hostile drones enter from `entry_side` and head for SITE-01: one-way types end
                there, reconnaissance types loiter 1-2 km out and then exit. No interceptors.
  intercepted   incoming + friendly INT-01.. (one per two one-way hostiles, max 3) launched from
                ADT-01, each arriving exactly when its assigned hostile passes a chosen point
                before SITE-01; both end there.
  lost-contact  one dji_mavic3 routed through an RF-02 terrain shadow (hidden from RF-02 but
                visible from RF-01 at 30-40 m AGL) + one radio-silent fpv_fiber + a short 2.4 GHz
                jammer window. The `drones`/`mix` knobs do not apply; the composition is fixed.
`defence: true` adds the intercepted-template interceptors to any template.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import yaml
from pydantic import BaseModel, Field, field_validator

from .catalog import CATALOG
from .config import Area, Scenario, coord_slug
from .world import World

SECTORS = {
    # centre (lat, lon) of the 10 km square + the sector town used for clutter/reports
    "ros-valley": {"center": (49.3754, 31.1882), "town": (49.4180, 31.2557)},  # Korsun-Shevchenkivskyi
    "kupiansk-oskil": {"center": (49.7106, 37.6156), "town": (49.7106, 37.6156)},  # Kupiansk
    "vovchansk-border": {"center": (50.2906, 36.9416), "town": (50.2906, 36.9416)},  # Vovchansk
}
AREA_KM = 10.0
HALF_M = AREA_KM * 500.0
MARGIN_M = 300.0  # everything stays >= 300 m inside the area edge
BOX_M = HALF_M - MARGIN_M
RF_MAST_M = 25.0
COVERAGE_AGL_M = 40.0  # site selection scores visibility of 40 m AGL targets
MIN_SITE_SEP_M = 3500.0

ONE_WAY = {"shahed136", "gerbera", "fpv_analog", "fpv_fiber"}  # paths end at SITE-01
RECON = {"orlan10", "zala", "supercam", "dji_mavic3"}  # loiter 1-2 km out, then exit
TERMINAL_AGL_M = 5.0  # one-way drones dive into SITE-01 from here
ALT_AGL = {  # cruise altitude band per type
    "shahed136": (300.0, 1500.0), "gerbera": (300.0, 1500.0),
    "fpv_analog": (10.0, 40.0), "fpv_fiber": (10.0, 40.0),
    "orlan10": (150.0, 500.0), "zala": (150.0, 500.0), "supercam": (150.0, 500.0),
    "dji_mavic3": (60.0, 150.0),
}
ID_STEM = {"shahed136": "shahed", "gerbera": "gerbera", "orlan10": "orlan", "zala": "zala",
           "supercam": "supercam", "dji_mavic3": "mavic", "fpv_analog": "fpv", "fpv_fiber": "fiber"}
SIDES = "NESW"
OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}
INTERCEPTOR_SPEED_MPS = 60.0  # catalog speed, exact


class Knobs(BaseModel):
    """The whole builder input; an LLM fills these from a text prompt."""

    seed: int = 0
    sector: str = "ros-valley"  # or "random"
    drones: int = Field(6, ge=1, le=50)  # incoming/intercepted only
    mix: dict[str, float] = {"shahed136": 3, "gerbera": 2, "orlan10": 1, "dji_mavic3": 1}
    entry_side: str = "random"  # "random" = per drone
    heading_spread_deg: float = Field(25.0, ge=0, le=90)
    time_of_day: str = "dusk"  # dusk | dawn | morning | noon | night | HH:MM (UTC)
    date: str = "2026-11-04"
    duration_min: int = Field(20, ge=1, le=360)
    sensor_preset: str = "standard"  # minimal | standard | full
    template: str = "incoming"  # incoming | intercepted | lost-contact
    defence: bool = False
    birds: bool = True
    wifi: bool = True

    @field_validator("sector")
    @classmethod
    def _sector(cls, v):
        if v not in SECTORS and v != "random":
            raise ValueError(f"unknown sector {v!r}; known: {sorted(SECTORS)} or 'random'")
        return v

    @field_validator("mix")
    @classmethod
    def _mix(cls, m):
        if not m:
            raise ValueError("mix must not be empty")
        for k, w in m.items():
            if k not in CATALOG or CATALOG[k]["kind"] != "drone":
                raise ValueError(f"mix: {k!r} is not a drone type in the catalog")
            if w <= 0:
                raise ValueError(f"mix: weight for {k} must be > 0")
        return m

    @field_validator("entry_side")
    @classmethod
    def _side(cls, v):
        if v not in ("random",) + tuple(SIDES):
            raise ValueError(f"entry_side must be random, N, E, S or W, not {v!r}")
        return v

    @field_validator("time_of_day")
    @classmethod
    def _tod(cls, v):
        if v in ("dusk", "dawn", "morning", "noon", "night"):
            return v
        if not re.fullmatch(r"\d{2}:\d{2}", v):
            raise ValueError(f"time_of_day must be dusk|dawn|morning|noon|night or HH:MM, not {v!r}")
        hh, mm = map(int, v.split(":"))
        if hh > 23 or mm > 59:
            raise ValueError(f"time_of_day {v!r} is not a valid UTC time")
        return v

    @field_validator("date")
    @classmethod
    def _date(cls, v):
        datetime.strptime(v, "%Y-%m-%d")
        return v

    @field_validator("sensor_preset")
    @classmethod
    def _preset(cls, v):
        if v not in ("minimal", "standard", "full"):
            raise ValueError(f"sensor_preset must be minimal, standard or full, not {v!r}")
        return v

    @field_validator("template")
    @classmethod
    def _template(cls, v):
        if v not in ("incoming", "intercepted", "lost-contact"):
            raise ValueError(f"template must be incoming, intercepted or lost-contact, not {v!r}")
        return v


# --- solar -----------------------------------------------------------------
def solar_times(lat: float, lon: float, day) -> tuple[datetime, datetime, datetime]:
    """(sunrise, solar noon, sunset) UTC at (lat, lon) on `day`; NOAA fractional-year algorithm."""
    gamma = 2.0 * math.pi / 365.0 * (day.timetuple().tm_yday - 1)  # fractional year at local noon
    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(gamma) - 0.032077 * math.sin(gamma)
                       - 0.014615 * math.cos(2 * gamma) - 0.040849 * math.sin(2 * gamma))  # minutes
    decl = (0.006918 - 0.399912 * math.cos(gamma) + 0.070257 * math.sin(gamma)
            - 0.006758 * math.cos(2 * gamma) + 0.000907 * math.sin(2 * gamma)
            - 0.002697 * math.cos(3 * gamma) + 0.00148 * math.sin(3 * gamma))  # radians
    cos_h = ((math.cos(math.radians(90.833)) - math.sin(math.radians(lat)) * math.sin(decl))
             / (math.cos(math.radians(lat)) * math.cos(decl)))
    ha = math.degrees(math.acos(max(-1.0, min(1.0, cos_h))))  # hour angle at sunrise/sunset
    noon_min = 720.0 - 4.0 * lon - eqtime  # solar noon, minutes UTC
    midnight = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    to_dt = lambda minutes: midnight + timedelta(minutes=minutes)
    return to_dt(noon_min - 4.0 * ha), to_dt(noon_min), to_dt(noon_min + 4.0 * ha)


def _start_time(k: Knobs, day, sunrise, noon, sunset) -> datetime:
    tod = k.time_of_day
    if tod == "dawn":
        start = sunrise - timedelta(minutes=15)
    elif tod == "morning":
        start = sunrise + timedelta(hours=2.5)
    elif tod == "noon":
        start = noon
    elif tod == "dusk":
        start = sunset - timedelta(minutes=30)
    elif tod == "night":
        start = sunset + timedelta(hours=2)
    else:
        hh, mm = map(int, tod.split(":"))
        start = datetime(day.year, day.month, day.day, hh, mm, tzinfo=timezone.utc)
    return (start + timedelta(seconds=30)).replace(second=0, microsecond=0)  # nearest minute


# --- local geometry --------------------------------------------------------
def _clamp(x: float, y: float) -> tuple[float, float]:
    return float(np.clip(x, -BOX_M, BOX_M)), float(np.clip(y, -BOX_M, BOX_M))


def _point_near(rng, base, rmin: float, rmax: float) -> tuple[float, float]:
    """Seeded point rmin..rmax from base, kept >= rmin away despite edge clamping."""
    th, d = float(rng.uniform(0.0, 2.0 * math.pi)), float(rng.uniform(rmin, rmax))
    for a in (th, th + math.pi, th + math.pi / 2.0):  # mirror/turn inward if the clamp ate the distance
        p = _clamp(base[0] + d * math.cos(a), base[1] + d * math.sin(a))
        if math.hypot(p[0] - base[0], p[1] - base[1]) >= rmin:
            return p
    return _clamp(base[0] + d * math.cos(th), base[1] + d * math.sin(th))


def _edge_point(rng, side: str) -> tuple[float, float]:
    """Entry point on `side`, 300 m inside the area edge."""
    c = float(rng.uniform(-BOX_M, BOX_M))
    return {"N": (c, BOX_M), "S": (c, -BOX_M), "E": (BOX_M, c), "W": (-BOX_M, c)}[side]


def _edge_point_at(side: str, along: float) -> tuple[float, float]:
    c = float(np.clip(along, -BOX_M, BOX_M))
    return {"N": (c, BOX_M), "S": (c, -BOX_M), "E": (BOX_M, c), "W": (-BOX_M, c)}[side]


def _operator_point(rng, side: str, entry_xy) -> tuple[float, float]:
    """0.5-1.5 km inside the area behind the entry point (uprange side of the entry)."""
    depth = float(rng.uniform(500.0, 1500.0))
    v = HALF_M - depth
    along = (entry_xy[0] if side in "NS" else entry_xy[1]) + float(rng.uniform(-600.0, 600.0))
    c = float(np.clip(along, -BOX_M, BOX_M))
    return {"N": (c, v), "S": (c, -v), "E": (v, c), "W": (-v, c)}[side]


def _corridor(rng, entry_xy, target_xy, spread_deg: float):
    """2-3 waypoints on the entry->target line, lateral heading deviation within +-spread."""
    dx, dy = target_xy[0] - entry_xy[0], target_xy[1] - entry_xy[1]
    dist = math.hypot(dx, dy) or 1.0
    ux, uy = dx / dist, dy / dist
    n = int(rng.integers(2, 4))  # 2-3 waypoints
    fr = np.sort(rng.uniform(0.15, 0.85, n))
    lat = rng.uniform(-1.0, 1.0, n) * math.tan(math.radians(spread_deg))
    out = []
    for f, l in zip(fr, lat):
        off = l * f * dist  # perpendicular offset keeping the heading inside +-spread
        out.append(_clamp(entry_xy[0] + ux * f * dist - uy * off,
                          entry_xy[1] + uy * f * dist + ux * off))
    return out


def _loiter_points(rng, site_xy):
    """Two points on a 1-2 km arc around SITE-01: the recon drone loiters here before exiting."""
    th = float(rng.uniform(0.0, 2.0 * math.pi))
    r = float(rng.uniform(1000.0, 2000.0))
    pts = []
    for a in (th, th + math.pi / 3.0):
        pts.append(_clamp(site_xy[0] + r * math.cos(a), site_xy[1] + r * math.sin(a)))
    return pts


def _flight_s(world, path_ll, speed_mps: float) -> float:
    """Ground track length / speed: the same polyline arithmetic truth.py flies."""
    wps = np.asarray(path_ll, dtype=float)
    wx, wy = world.to_xy(wps[:, 0], wps[:, 1])
    return float(np.hypot(np.diff(wx), np.diff(wy)).sum() / speed_mps)


def _at_arclength(cum, pts, s):
    i = int(np.clip(np.searchsorted(cum, s, side="right") - 1, 0, len(pts) - 2))
    fr = (s - cum[i]) / (cum[i + 1] - cum[i])
    return pts[i] + fr * (pts[i + 1] - pts[i])


# --- terrain siting --------------------------------------------------------
def _candidates(world) -> np.ndarray:
    """Local DEM maxima on a 300 m grid over the area, best ~40 by height. Shape (n, 2) x, y."""
    g = np.arange(-BOX_M, BOX_M + 1.0, 300.0)
    x, y = np.meshgrid(g, g)
    h = world.height(x, y)
    mx = np.zeros(h.shape, bool)  # local maxima vs the 8 grid neighbours
    core = h[1:-1, 1:-1]
    ok = np.ones(core.shape, bool)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            if di or dj:
                ok &= core > h[1 + di:h.shape[0] - 1 + di, 1 + dj:h.shape[1] - 1 + dj]
    mx[1:-1, 1:-1] = ok
    hi = h.ravel()
    order = np.concatenate([np.flatnonzero(mx.ravel())[np.argsort(-hi[mx.ravel()], kind="stable")],
                            np.flatnonzero(~mx.ravel())[np.argsort(-hi[~mx.ravel()], kind="stable")]])
    keep = order[:40]
    return np.stack([x.ravel()[keep], y.ravel()[keep]], 1)


def _coverage(world, cand_xy) -> np.ndarray:
    """Per candidate: which of a 250 m grid over the area sees a 40 m AGL target. (n, ngrid) bool."""
    g = np.arange(-4750.0, 4751.0, 250.0)
    x, y = np.meshgrid(g, g)
    cov = np.empty((len(cand_xy), x.size), bool)
    for i, (cx, cy) in enumerate(cand_xy):
        z = float(world.height(cx, cy)) + RF_MAST_M
        cov[i] = (world.min_visible_agl((cx, cy, z), x, y) <= COVERAGE_AGL_M).ravel()
    return cov


def _pick_rf_sites(cand_xy, cov, k: int) -> list[int]:
    """Greedy max union coverage, sites >= 3.5 km apart."""
    chosen: list[int] = []
    union = np.zeros(cov.shape[1], bool)
    for _ in range(k):
        best, best_gain = -1, -1
        for i in range(len(cand_xy)):
            if any(np.hypot(*(cand_xy[i] - cand_xy[j])) < MIN_SITE_SEP_M for j in chosen):
                continue
            gain = int((cov[i] & ~union).sum())
            if gain > best_gain:
                best, best_gain = i, gain
        if best < 0:
            raise ValueError(f"cannot site {k} RF receivers >= {MIN_SITE_SEP_M:.0f} m apart "
                             f"on the {len(cand_xy)} DEM maxima; fewer drones or a larger sector")
        chosen.append(best)
        union |= cov[best]
    return chosen


# --- emission helpers -----------------------------------------------------
def _obj(oid: str, otype: str, side: str, *, pos=None, path=None, **extra) -> dict:
    d: dict = {"id": oid, "type": otype, "side": side}
    if pos is not None:
        d["pos"] = [round(float(pos[0]), 6), round(float(pos[1]), 6)]
    if path is not None:
        d["path"] = [[round(float(a), 6), round(float(b), 6), round(float(c), 1)]
                     for a, b, c in path]
    for key, val in extra.items():
        if val is None:
            continue
        if key in ("start_s", "end_s", "alt_agl_m"):
            d[key] = round(float(val), 1)
        elif key == "speed_mps":
            d[key] = round(float(val), 2)
        else:
            d[key] = val
    return d


def _sensor(sid: str, stype: str, *, pos=None, mount=None, mast_m=None, params=None) -> dict:
    d: dict = {"id": sid, "type": stype}
    if pos is not None:
        d["pos"] = [round(float(pos[0]), 6), round(float(pos[1]), 6)]
    if mount is not None:
        d["mount"] = mount
    if mast_m is not None:
        d["mast_m"] = float(mast_m)
    if params:
        d["params"] = params
    return d


def _ll(world, xy) -> tuple[float, float]:
    lat, lon = world.to_ll(xy[0], xy[1])
    return float(lat), float(lon)


# --- the build ------------------------------------------------------------
def build(knobs: Knobs) -> tuple[str, Scenario]:
    """Returns (yaml_text, validated Scenario). Deterministic from (knobs, seed)."""
    k = knobs
    sector = k.sector
    if sector == "random":
        pick = np.random.default_rng([k.seed, zlib.crc32(b"sector")])
        sector = str(pick.choice(sorted(SECTORS)))
    rng = np.random.default_rng([k.seed, zlib.crc32(sector.encode())])
    info = SECTORS[sector]

    day = datetime.strptime(k.date, "%Y-%m-%d").replace(tzinfo=timezone.utc).date()
    cx, clon = info["center"]
    start = _start_time(k, day, *solar_times(cx, clon, day))
    duration_s = float(k.duration_min * 60)

    weather = {
        "wind_from_deg": round(float(rng.uniform(0.0, 360.0)), 1),
        "wind_mps": round(float(rng.uniform(1.0, 6.0)), 1),
        "temp_c": round(float(rng.uniform(2.0, 8.0)), 1),
        "rh_pct": round(float(rng.uniform(75.0, 90.0)), 1),
        "visibility_km": round(float(rng.uniform(8.0, 20.0)), 1),
    }

    # world from the sector area alone; the emitted scenario uses the same area
    world = World(Scenario(name="_area", seed=k.seed, start=start, duration_s=60,
                           area=Area(lat=cx, lon=clon, size_km=AREA_KM), objects=[], sensors=[]))

    # ground assets: SITE-01 1.5-3 km from the town, ADT-01/ADB-01 1-2 km from SITE-01
    town_xy = _clamp(*[float(v) for v in world.to_xy(*info["town"])])
    site_xy = _point_near(rng, town_xy, 1500.0, 3000.0)
    adt_xy = _point_near(rng, site_xy, 1000.0, 2000.0)
    adb_xy = _point_near(rng, site_xy, 1000.0, 2000.0)

    # terrain-sited receivers
    cand_xy = _candidates(world)
    cov = _coverage(world, cand_xy)
    n_rf = {"minimal": 2, "standard": 3, "full": 4}[k.sensor_preset]
    rf_sites = _pick_rf_sites(cand_xy, cov, n_rf)
    radar_i = int(np.argmax([cov[i].sum() if i not in rf_sites else -1
                             for i in range(len(cand_xy))]))  # best remaining high point
    rf_xyz = [(float(x), float(y), float(world.height(x, y)) + RF_MAST_M) for x, y in cand_xy[rf_sites]]
    bias = [round(float(rng.uniform(-1.0, 1.0)), 2) for _ in rf_sites]

    objs: list[dict] = [
        _obj("SITE-01", "site", "friendly", pos=_ll(world, site_xy)),
        _obj("ADT-01", "ad_team", "friendly", pos=_ll(world, adt_xy)),
        _obj("ADB-01", "ad_battery", "friendly", pos=_ll(world, adb_xy)),
    ]

    # ---- the air picture --------------------------------------------------
    drones: list[dict] = []  # {id, path, speed, start, end}
    oneway: list[dict] = []
    n_int = 0

    def add_drone(typ: str, path_xy, alts, start_s: float, force_end=None):
        counts[typ] = counts.get(typ, 0) + 1
        did = f"{ID_STEM[typ]}_{counts[typ]}"
        speed = CATALOG[typ]["speed_mps"] * float(rng.uniform(0.9, 1.1))
        path = [(x, y, a) for (x, y), a in zip(path_xy, alts)]
        path_ll = [_ll(world, (x, y)) + (a,) for x, y, a in path]
        end_s = start_s + _flight_s(world, path_ll, speed)
        objs.append(_obj(did, typ, "hostile", path=path_ll, speed_mps=speed,
                         start_s=start_s, end_s=force_end))
        if any(L["tx"] == "operator" for L in CATALOG[typ]["links"]):
            op_xy = _operator_point(rng, entry_side, path_xy[0])
            objs.append(_obj(f"op_{did}", "operator", "hostile", pos=_ll(world, op_xy),
                             start_s=start_s, end_s=(force_end if force_end is not None else end_s),
                             controls=did))
        rec = {"id": did, "type": typ, "path_ll": path_ll, "speed": speed,
               "start": start_s, "end": end_s}
        drones.append(rec)
        if typ in ONE_WAY:
            oneway.append(rec)
        return rec

    counts: dict[str, int] = {}
    if k.template == "lost-contact":
        # one hostile recon Mavic with the hero's RF-02 dead-zone leg + one radio-silent fiber FPV
        entry_side = k.entry_side if k.entry_side != "random" else SIDES[int(rng.integers(4))]
        entry_xy = _edge_point(rng, entry_side)
        alt = float(rng.uniform(*ALT_AGL["dji_mavic3"]))
        start_s = float(rng.uniform(0.0, 0.6 * duration_s))
        leg_a, leg_b, leg_alt = _hidden_leg(world, rf_xyz[0], rf_xyz[1], rng)
        mids = _corridor(rng, entry_xy, leg_a, k.heading_spread_deg)
        lo1, lo2 = _loiter_points(rng, site_xy)
        exit_xy = _edge_point_at(OPPOSITE[entry_side], lo2[0] if OPPOSITE[entry_side] in "NS" else lo2[1])
        add_drone("dji_mavic3",
                  [entry_xy] + mids + [tuple(leg_a), tuple(leg_b), lo1, lo2, exit_xy],
                  [alt] * (len(mids) + 1) + [leg_alt, leg_alt] + [alt] * 3, start_s)
        entry_side = k.entry_side if k.entry_side != "random" else SIDES[int(rng.integers(4))]
        entry_xy = _edge_point(rng, entry_side)
        alt = float(rng.uniform(*ALT_AGL["fpv_fiber"]))
        start_s = float(rng.uniform(0.0, 0.6 * duration_s))
        mids = _corridor(rng, entry_xy, site_xy, k.heading_spread_deg)
        add_drone("fpv_fiber", [entry_xy] + mids + [site_xy],
                  [alt] * (len(mids) + 1) + [TERMINAL_AGL_M], start_s)
    else:
        types = rng.choice(sorted(k.mix), size=k.drones,
                           p=np.array([k.mix[t] for t in sorted(k.mix)], float)
                           / sum(k.mix.values()))
        for typ in types:
            typ = str(typ)
            entry_side = k.entry_side if k.entry_side != "random" else SIDES[int(rng.integers(4))]
            entry_xy = _edge_point(rng, entry_side)
            alt = float(rng.uniform(*ALT_AGL[typ]))
            start_s = float(rng.uniform(0.0, 0.6 * duration_s))
            mids = _corridor(rng, entry_xy, site_xy, k.heading_spread_deg)
            if typ in ONE_WAY:
                add_drone(typ, [entry_xy] + mids + [site_xy],
                          [alt] * (len(mids) + 1) + [TERMINAL_AGL_M], start_s)
            else:
                lo1, lo2 = _loiter_points(rng, site_xy)
                exit_xy = _edge_point_at(OPPOSITE[entry_side],
                                         lo2[0] if OPPOSITE[entry_side] in "NS" else lo2[1])
                add_drone(typ, [entry_xy] + mids + [lo1, lo2, exit_xy],
                          [alt] * (len(mids) + 4), start_s)

    # ---- interceptors (intercepted template, or defence=true anywhere) -----
    n_int = min(3, len(oneway) // 2) if (k.template == "intercepted" or k.defence) else 0
    for i in range(n_int):
        hostile = oneway[2 * i]  # one interceptor per two one-way hostiles
        hlat = np.asarray([p[0] for p in hostile["path_ll"]], float)
        hlon = np.asarray([p[1] for p in hostile["path_ll"]], float)
        hxy = np.stack(world.to_xy(hlat, hlon), 1)  # (n, 2) local metres
        seg = np.hypot(np.diff(hxy[:, 0]), np.diff(hxy[:, 1]))
        cum = np.concatenate([[0.0], np.cumsum(seg)])
        halts = np.asarray([p[2] for p in hostile["path_ll"]], float)
        launch_xy = _clamp(adt_xy[0] + float(rng.uniform(-300.0, 300.0)),
                           adt_xy[1] + float(rng.uniform(-300.0, 300.0)))
        for _ in range(12):  # seeded rendezvous candidates; first feasible wins
            frac = float(rng.uniform(0.5, 0.9))
            s = frac * cum[-1]
            p = _at_arclength(cum, hxy, s)
            alt_p = float(np.interp(s, cum, halts))
            t = hostile["start"] + s / hostile["speed"]
            if t > duration_s:  # the rendezvous must fall inside the scenario window
                continue
            if t - math.hypot(p[0] - launch_xy[0], p[1] - launch_xy[1]) / INTERCEPTOR_SPEED_MPS >= 0:
                break
        else:
            raise ValueError(f"no feasible rendezvous inside the {duration_s:.0f} s window for "
                             f"{hostile['id']} from ADT-01; lengthen --duration or drop --defence")
        iid = f"INT-{i + 1:02d}"
        launch = t - math.hypot(p[0] - launch_xy[0], p[1] - launch_xy[1]) / INTERCEPTOR_SPEED_MPS
        path_ll = [_ll(world, launch_xy) + (15.0,), _ll(world, (p[0], p[1])) + (alt_p,)]
        objs.append(_obj(iid, "interceptor", "friendly", path=path_ll,
                         speed_mps=INTERCEPTOR_SPEED_MPS, start_s=launch, end_s=t))
        objs.append(_obj(f"op_{iid}", "operator", "friendly", pos=_ll(world, launch_xy),
                         start_s=launch, end_s=t, controls=iid))
        for o in objs:  # the assigned hostile (and its operator) end at the rendezvous too
            if o["id"] == hostile["id"] or o.get("controls") == hostile["id"]:
                o["end_s"] = round(float(t), 1)

    # ---- clutter + the lost-contact jammer --------------------------------
    if k.wifi:
        objs.append(_obj("wifi_1", "wifi_ap", "neutral", pos=_ll(world, town_xy), alt_agl_m=20.0))
    if k.birds:
        th = float(rng.uniform(0.0, 2.0 * math.pi))
        reach = BOX_M / max(abs(math.cos(th)), abs(math.sin(th)))
        geese_alt = float(rng.uniform(200.0, 300.0))
        objs.append(_obj("geese_1", "geese", "neutral",
                         path=[_ll(world, (-reach * math.cos(th), -reach * math.sin(th))) + (geese_alt,),
                               _ll(world, (reach * math.cos(th), reach * math.sin(th))) + (geese_alt,)],
                         start_s=float(rng.uniform(0.0, 0.6 * duration_s))))
    if k.template == "lost-contact":
        w = min(float(rng.uniform(120.0, 240.0)), 0.5 * duration_s)  # 2-4 min window
        t0 = float(rng.uniform(0.0, duration_s - w))
        objs.append(_obj("jammer_1", "jammer", "friendly", pos=_ll(world, cand_xy[rf_sites[1]]),
                         alt_agl_m=15.0, start_s=t0, end_s=t0 + w))

    # ---- sensors ---------------------------------------------------------
    sens: list[dict] = []
    for i, (bx, b) in enumerate(zip(rf_sites, bias)):
        sens.append(_sensor(f"RF-{i + 1:02d}", "rf_df", pos=_ll(world, cand_xy[bx]),
                            mast_m=RF_MAST_M, params={"calib_bias_deg": b}))
    sens.append(_sensor("RADAR-01", "radar", pos=_ll(world, cand_xy[radar_i]), mast_m=15.0))
    sens.append(_sensor("CAM-01", "camera", mount="RF-01", mast_m=22.0,
                        params={"fov_deg": 3.0, "width": 1280, "height": 720, "fps": 1, "cue": "rf"}))
    if k.sensor_preset != "minimal":
        for i in range(2):
            mic = _clamp(float(rng.uniform(-1200.0, 1200.0)), float(rng.uniform(-1200.0, 1200.0)))
            sens.append(_sensor(f"ACOUSTIC-{i + 1:02d}", "microphone", pos=_ll(world, mic), mast_m=3.0))
        sens.append(_sensor("RID-01", "remote_id", mount="RF-01", mast_m=RF_MAST_M))
    if k.sensor_preset == "full":
        act = [d["start"] for d in drones] + [d["end"] for d in drones]
        lo, hi = (min(act), max(act)) if act else (0.0, duration_s)
        times = sorted(round(float(t), 1) for t in rng.uniform(lo, min(hi, duration_s), 4))
        sens.append(_sensor("IQ-01", "rf_iq", mount="RF-01", mast_m=RF_MAST_M,
                            params={"center_mhz": 2440, "times_s": times}))
        sens.append(_sensor("SAT-01", "satellite", pos=(cx, clon),
                            params={"platform": "SENTINEL-2A"}))
        sens.append(_sensor("REPORTS-01", "reports", pos=_ll(world, town_xy),
                            params={"eppo_civilians": 25}))
        sens.append(_sensor("TEL-01", "telemetry", pos=_ll(world, adt_xy),
                            params={"objects": [o["id"] for o in objs if o["type"] == "interceptor"]}))
    sens.append(_sensor("C2-01", "c2", pos=_ll(world, adt_xy)))  # last: it reads the other sensors

    scen_dict = {
        "name": f"{coord_slug(*SECTORS[sector]['center'])}-{k.template}-s{k.seed}",
        "seed": k.seed,
        "start": start.isoformat().replace("+00:00", "Z"),
        "duration_s": duration_s,
        "truth_hz": 2,
        "area": {"lat": cx, "lon": clon, "size_km": AREA_KM},
        "weather": weather,
        "objects": objs,
        "sensors": sens,
    }
    scenario = Scenario.model_validate(scen_dict)  # raises with context on anything invalid
    kj = json.dumps(k.model_dump(), sort_keys=True)
    text = (f"# mirrorworld.builder: knobs + seed -> validated scenario; geometry from the real DEM.\n"
            f"# Reproduce: uv run python -m mirrorworld.builder --knobs-json '{kj}'\n"
            + yaml.safe_dump(scen_dict, sort_keys=False, default_flow_style=False, width=100))
    return text, scenario


def _hidden_leg(world, rf1_xyz, rf2_xyz, rng):
    """(leg_start, leg_end, alt_agl): a 1.2-2 km leg hidden from RF-02, visible from RF-01 at 30-40 m."""
    g = np.arange(-4625.0, 4626.0, 250.0)
    x, y = np.meshgrid(g, g)
    pts = np.stack([x.ravel(), y.ravel()], 1)
    mva1 = world.min_visible_agl(rf1_xyz, x, y).ravel()
    mva2 = world.min_visible_agl(rf2_xyz, x, y).ravel()
    for alt in (35.0, 32.0, 38.0, 30.0, 40.0):
        hid = np.flatnonzero((mva2 > alt) & (mva1 <= alt))
        if hid.size == 0:
            continue
        sub = pts[hid]
        dist = np.hypot(sub[:, 0, None] - sub[None, :, 0], sub[:, 1, None] - sub[None, :, 1])
        i, j = np.where((dist >= 1200.0) & (dist <= 2000.0))
        if i.size:
            k = int(rng.integers(i.size))
            a, b = sub[i[k]], sub[j[k]]
            if a[0] > b[0] or (a[0] == b[0] and a[1] > b[1]):
                a, b = b, a
            return a, b, alt
    raise ValueError("lost-contact: no 1.2-2 km leg hidden from RF-02 but visible from RF-01 "
                     "at 30-40 m AGL in this sector; try another seed or sector")


# --- CLI ------------------------------------------------------------------
def _onoff(s: str) -> bool:
    if s.lower() in ("on", "true", "1", "yes"):
        return True
    if s.lower() in ("off", "false", "0", "no"):
        return False
    raise argparse.ArgumentTypeError(f"expected on/off, got {s!r}")


def _parse_mix(s: str) -> dict[str, float]:
    out = {}
    for part in s.split(","):
        name, _, w = part.partition(":")
        out[name.strip()] = float(w)
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="mirrorworld.builder",
                                 description="Build a validated scenario YAML from knobs + a seed.")
    ap.add_argument("--knobs-json", default=None, help="JSON knobs (LLM output); CLI flags override")
    ap.add_argument("--sector", default=None, help=f"{', '.join(sorted(SECTORS))} or random")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--drones", type=int, default=None)
    ap.add_argument("--mix", default=None, help='e.g. "dji_mavic3:3,fpv_analog:2,fpv_fiber:1,shahed136:1"')
    ap.add_argument("--entry", dest="entry_side", default=None, help="N, E, S, W or random")
    ap.add_argument("--spread", dest="heading_spread_deg", type=float, default=None)
    ap.add_argument("--tod", dest="time_of_day", default=None, help="dusk|dawn|morning|noon|night|HH:MM")
    ap.add_argument("--date", default=None)
    ap.add_argument("--duration", dest="duration_min", type=int, default=None)
    ap.add_argument("--preset", dest="sensor_preset", default=None)
    ap.add_argument("--template", default=None)
    ap.add_argument("--defence", type=_onoff, default=None)
    ap.add_argument("--birds", type=_onoff, default=None)
    ap.add_argument("--wifi", type=_onoff, default=None)
    ap.add_argument("-o", "--out", default=None, help="output YAML (default scenarios/<name>.yaml)")
    ap.add_argument("--run", action="store_true", help="then run it with --skip-missing")
    args = ap.parse_args(argv)

    knobs_dict = json.loads(args.knobs_json) if args.knobs_json else {}
    for name in ("sector", "seed", "drones", "mix", "entry_side", "heading_spread_deg",
                 "time_of_day", "date", "duration_min", "sensor_preset", "template",
                 "defence", "birds", "wifi"):
        val = getattr(args, name)
        if val is not None:
            knobs_dict[name] = _parse_mix(val) if name == "mix" else val
    knobs = Knobs(**knobs_dict)

    text, scen = build(knobs)
    out = Path(args.out) if args.out else Path("scenarios") / f"{scen.name}.yaml"
    out.write_text(text)
    print(f"wrote {out}")
    if args.run:
        cmd = [sys.executable, "-m", "mirrorworld", "run", str(out), "--skip-missing"]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"run failed: {' '.join(cmd)}\n{r.stdout}{r.stderr}")
        print(r.stdout.strip())
        print(f"out dir: out/{scen.name}")


if __name__ == "__main__":
    main()
