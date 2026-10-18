"""Truth simulation: one clock, one world state. Sensor modules never see this file's data
except through Context.truth, and never write truth columns into sensors/."""
import math
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from .catalog import CATALOG
from .config import Scenario
from .world import World

TRACK_COLUMNS = [
    "t", "time_utc", "object_id", "lat", "lon", "alt_msl_m", "alt_agl_m",
    "x_m", "y_m", "z_m", "vx", "vy", "vz", "speed_mps", "heading_deg",
    "gnss_lat", "gnss_lon", "gnss_alt_msl_m",
]


def iso(start: datetime, t):
    """ISO 8601 with milliseconds and Z, for t seconds after `start`; scalar or array."""
    arr = np.asarray(t, dtype=np.float64)

    def fmt(ti: float) -> str:
        d = start + timedelta(milliseconds=int(round(float(ti) * 1000)))
        return f"{d:%Y-%m-%dT%H:%M:%S}.{d.microsecond // 1000:03d}Z"

    if arr.ndim == 0:
        return fmt(arr)
    return np.array([fmt(v) for v in arr.ravel()]).reshape(arr.shape)


def simulate(cfg: Scenario, world: World, rng) -> pd.DataFrame:
    ticks = np.arange(math.ceil(cfg.duration_s * cfg.truth_hz)) / cfg.truth_hz
    frames = []
    for obj in cfg.objects:
        cat = CATALOG[obj.type]
        if obj.path is not None:
            t, x, y, z, agl = _moving(obj, cat, world, ticks)
        else:
            t, x, y, z, agl = _static(obj, cat, world, ticks)
        if t.size == 0:
            continue
        if t.size == 1:
            vx = vy = vz = np.zeros(1)
        else:
            vx, vy, vz = (np.gradient(c, t) for c in (x, y, z))
        speed = np.hypot(vx, vy)  # ground speed, pairs with heading
        heading = np.degrees(np.arctan2(vx, vy)) % 360.0
        lat, lon = world.to_ll(x, y)

        gx = x + rng.normal(0.0, 1.5, t.size)
        gy = y + rng.normal(0.0, 1.5, t.size)
        gz = z + rng.normal(0.0, 3.0, t.size)
        if obj.gnss_spoof is not None:
            sp = obj.gnss_spoof
            on = (t >= sp.start_s) & (t <= sp.end_s)
            d = np.where(on, sp.drift_mps * (t - sp.start_s), 0.0)  # snaps back after end_s
            rad = math.radians(sp.drift_deg)  # true bearing: 0 = north, 90 = east
            gx += d * math.sin(rad)
            gy += d * math.cos(rad)
        gnss_lat, gnss_lon = world.to_ll(gx, gy)

        frames.append(pd.DataFrame({
            "t": t,
            "time_utc": iso(cfg.start, t),
            "object_id": obj.id,
            "lat": lat,
            "lon": lon,
            "alt_msl_m": z,
            "alt_agl_m": agl,
            "x_m": x,
            "y_m": y,
            "z_m": z,
            "vx": vx,
            "vy": vy,
            "vz": vz,
            "speed_mps": speed,
            "heading_deg": heading,
            "gnss_lat": gnss_lat,
            "gnss_lon": gnss_lon,
            "gnss_alt_msl_m": gz,
        }))
    if not frames:
        return pd.DataFrame(columns=TRACK_COLUMNS)
    return pd.concat(frames, ignore_index=True)[TRACK_COLUMNS]


def _moving(obj, cat, world, ticks):
    """Constant speed along the waypoint polyline; alt_agl interpolated along the path."""
    wps = np.asarray(obj.path, dtype=np.float64)  # (lat, lon, alt_agl)
    wx, wy = world.to_xy(wps[:, 0], wps[:, 1])
    alt = wps[:, 2]
    if obj.loop:  # close the loop back to the first waypoint
        wx = np.append(wx, wx[0])
        wy = np.append(wy, wy[0])
        alt = np.append(alt, alt[0])
    seg = np.hypot(np.diff(wx), np.diff(wy))
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    length = cum[-1]

    speed = obj.speed_mps if obj.speed_mps is not None else cat.get("speed_mps", 0.0)
    t = ticks[ticks >= obj.start_s]
    if obj.end_s is not None:
        t = t[t <= obj.end_s]
    s = speed * (t - obj.start_s)
    if obj.loop:
        s = s % length if length > 0 else np.zeros_like(s)
    else:
        keep = s <= length  # non-looping objects stop existing at the end of the path
        t, s = t[keep], s[keep]

    idx = np.clip(np.searchsorted(cum, s, side="right") - 1, 0, seg.size - 1)
    safe = np.where(seg[idx] > 0, seg[idx], 1.0)
    frac = np.where(seg[idx] > 0, (s - cum[idx]) / safe, 0.0)
    x = wx[idx] + frac * (wx[idx + 1] - wx[idx])
    y = wy[idx] + frac * (wy[idx + 1] - wy[idx])
    agl = np.interp(s, cum, alt)
    return t, x, y, world.height(x, y) + agl, agl


def _static(obj, cat, world, ticks):
    agl = obj.alt_agl_m if obj.alt_agl_m is not None else cat.get("height_m", 0.0)
    end = obj.end_s if obj.end_s is not None else np.inf
    t = ticks[(ticks >= obj.start_s) & (ticks <= end)]
    x, y = world.to_xy(obj.pos[0], obj.pos[1])
    x = np.full(t.shape, x, dtype=np.float64)
    y = np.full(t.shape, y, dtype=np.float64)
    agl_arr = np.full(t.shape, agl, dtype=np.float64)
    return t, x, y, world.height(x, y) + agl_arr, agl_arr
