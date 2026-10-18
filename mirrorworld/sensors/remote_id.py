"""Remote ID receiver: decoded DJI DroneID / ASTM F3411-style broadcasts and why each decoded.

Every airborne object whose `remote_id` resolves true broadcasts one 1 Hz message carrying its
own GNSS view of the world (so GNSS spoofing shows up as a drifting reported position) and the
pilot's GPS — DroneID really leaks the operator. A message is recorded only when the 2.4 GHz
link budget closes: path loss over the real terrain, +2/-2 dB per-burst wobble, 10% packet loss.
"""
import hashlib

import numpy as np
import pandas as pd

from ..catalog import CATALOG
from .rf_df import LABEL, path_loss_db

F_MHZ = 2437.0  # 802.11 channel 6; Remote ID broadcasts ride the 2.4 GHz ISM band
EIRP_DBM = 23.0
RX_GAIN_DBI = 3.0  # the mast antenna RID1 shares with RF1 (same as rf_df's gain_dbi on this tower)
SENSITIVITY_DBM = -92.0
PKT_LOSS = 0.1
JITTER_DB = 2.0  # Rician-ish per-burst power wobble
C_MPS = 299_792_458.0
SERIAL_PREFIX = "1581F6Z"  # DJI-style serial; the remainder is derived, not random per run
ALPHABET = "0123456789ABCDEFGHJKLMNPQRSTUVWXYZ"  # DJI serials skip I and O
MSG_COLS = ["uas_id", "ua_type", "lat", "lon", "alt_geo", "height_agl", "speed_horizontal",
            "track_direction", "operator_lat", "operator_lon", "timestamp"]
CSV_COLS = ["record_id", "t", "time_utc", "timestamp", "uas_id", "ua_type", "lat", "lon",
            "alt_geo", "height_agl", "speed_horizontal", "track_direction", "operator_lat",
            "operator_lon", "rx_power_dbm"]
KEY_COLS = ["record_id", "object_id", "link", "label", "true_lat", "true_lon", "true_alt",
            "position_error_m", "operator_true_lat", "operator_true_lon", "rx_power_dbm"]


def _serial(seed, obj_id):
    """Deterministic DJI-like serial: same drone, same serial, every run."""
    n = int.from_bytes(hashlib.sha256(f"{seed}:{obj_id}".encode()).digest()[:8], "big")
    chars = []
    for _ in range(7):
        chars.append(ALPHABET[n % len(ALPHABET)])
        n //= len(ALPHABET)
    return SERIAL_PREFIX + "".join(chars)


def _track_velocity(t, gx, gy, gz, half_s, clip_mps):
    """Velocity from central differences of the GNSS track over +-half_s.

    The long window is a receiver smoothing its fixes: it averages the per-fix position noise
    down to sub-m/s velocity noise. Clipping bounds the glitch a snap-back step would print.
    """
    n = t.size
    k = max(int(round(half_s / float(np.median(np.diff(t))))) if n > 1 else 1, 1)
    i0, i1 = np.clip(np.arange(n) - k, 0, n - 1), np.clip(np.arange(n) + k, 0, n - 1)
    dt = np.where(t[i1] > t[i0], t[i1] - t[i0], 1.0)
    v = np.stack([(p[i1] - p[i0]) / dt for p in (gx, gy, gz)], -1)
    return v * np.minimum(1.0, clip_mps / np.maximum(np.linalg.norm(v, axis=1), 1e-9))[:, None]


def _interp(rows, t, col):
    return np.interp(t, rows["t"].to_numpy(), rows[col].to_numpy(), left=np.nan, right=np.nan)


def _messages(ctx, obj, operator_of):
    """One object's broadcast stream at 1 Hz: what its own GNSS believes, plus the pilot's GPS."""
    rng = ctx.rng(f"rid:tx:{obj.id}")
    rows = ctx.truth[ctx.truth["object_id"] == obj.id].sort_values("t")
    if rows.empty:
        return None
    t = np.arange(0.0, ctx.cfg.duration_s, 1.0)
    g_lat, g_lon, g_alt = (_interp(rows, t, c) for c in ("gnss_lat", "gnss_lon", "gnss_alt_msl_m"))
    t_lat, t_lon, t_alt = (_interp(rows, t, c) for c in ("lat", "lon", "alt_msl_m"))
    air = np.isfinite(g_lat) & (_interp(rows, t, "alt_agl_m") > 1.0)  # broadcast only while airborne
    if not air.any():
        return None
    i = np.flatnonzero(air)
    g_lat, g_lon, g_alt = g_lat[i], g_lon[i], g_alt[i]
    t_lat, t_lon, t_alt = t_lat[i], t_lon[i], t_alt[i]
    gx, gy = ctx.world.to_xy(g_lat, g_lon)
    v = _track_velocity(t[i], gx, gy, g_alt, 2.0, 60.0)
    x_true, y_true = ctx.world.to_xy(t_lat, t_lon)
    # height_agl is barometric: the vertical channel is honest even when the fix is spoofed
    height_agl = g_alt - ctx.world.height(x_true, y_true) + rng.normal(0.0, 2.0, i.size)

    operator_lat = operator_lon = o_true_lat = o_true_lon = None
    if operator_of.get(obj.id) is not None:
        orows = ctx.truth[ctx.truth["object_id"] == operator_of[obj.id]].sort_values("t")
        o_true_lat, o_true_lon = _interp(orows, t[i], "lat"), _interp(orows, t[i], "lon")
        # a DroneID pilot position is the operator's own GNSS with ~5 m of wobble
        ox, oy = ctx.world.to_xy(_interp(orows, t[i], "gnss_lat"), _interp(orows, t[i], "gnss_lon"))
        ox += rng.normal(0.0, 2.0, i.size)
        oy += rng.normal(0.0, 2.0, i.size)
        operator_lat, operator_lon = ctx.world.to_ll(ox, oy)

    return {
        "t": t[i], "xyz": np.stack([gx, gy, g_alt], -1),
        "uas_id": _serial(ctx.cfg.seed, obj.id),
        "ua_type": "Helicopter or Multirotor",
        "lat": np.round(g_lat, 6), "lon": np.round(g_lon, 6),
        "alt_geo": np.round(g_alt, 1), "height_agl": np.round(height_agl, 1),
        "speed_horizontal": np.round(np.hypot(v[:, 0], v[:, 1]), 2),
        "track_direction": np.round(np.degrees(np.arctan2(v[:, 0], v[:, 1])) % 360, 1),
        "operator_lat": np.round(operator_lat, 6) if operator_lat is not None else None,
        "operator_lon": np.round(operator_lon, 6) if operator_lon is not None else None,
        "timestamp": ctx.iso(t[i]),
        "true_lat": t_lat, "true_lon": t_lon, "true_alt": t_alt,
        "operator_true_lat": o_true_lat if o_true_lat is not None else None,
        "operator_true_lon": o_true_lon if o_true_lon is not None else None,
    }


def _receive(sensor, ctx, streams):
    """One receiver: which bursts survive the link budget, and why each one is in the log."""
    rx = ctx.sensor_xyz(sensor)
    rng = ctx.rng(f"rid:rx:{sensor.id}")
    recs, keys = [], []
    for obj_id, m in streams.items():
        t_tx = m["t"]
        d = np.hypot(*(m["xyz"] - rx).T)
        t_rx = t_tx + d / C_MPS
        loss = path_loss_db(ctx.world, m["xyz"], rx, F_MHZ)
        prx = EIRP_DBM + RX_GAIN_DBI - loss + rng.uniform(-JITTER_DB, JITTER_DB, t_tx.size)
        got = ctx.alive(sensor, t_rx) & (prx >= SENSITIVITY_DBM) & (rng.random(t_tx.size) >= PKT_LOSS)
        for k in np.flatnonzero(got):
            ex, ey = ctx.world.to_xy(m["true_lat"][k], m["true_lon"][k])
            recs.append(dict(
                t=float(t_rx[k]), uas_id=m["uas_id"], ua_type=m["ua_type"],
                lat=float(m["lat"][k]), lon=float(m["lon"][k]), alt_geo=float(m["alt_geo"][k]),
                height_agl=float(m["height_agl"][k]),
                speed_horizontal=float(m["speed_horizontal"][k]),
                track_direction=float(m["track_direction"][k]),
                operator_lat=float(m["operator_lat"][k]) if m["operator_lat"] is not None else None,
                operator_lon=float(m["operator_lon"][k]) if m["operator_lon"] is not None else None,
                timestamp=str(m["timestamp"][k]), rx_power_dbm=round(float(prx[k]), 1)))
            keys.append(dict(
                object_id=obj_id, link="remote_id", label=LABEL[ctx.objects[obj_id].side],
                true_lat=round(float(m["true_lat"][k]), 6),
                true_lon=round(float(m["true_lon"][k]), 6),
                true_alt=round(float(m["true_alt"][k]), 1),
                position_error_m=round(float(np.hypot(m["xyz"][k, 0] - ex, m["xyz"][k, 1] - ey)), 1),
                operator_true_lat=round(float(m["operator_true_lat"][k]), 6)
                if m["operator_true_lat"] is not None else np.nan,
                operator_true_lon=round(float(m["operator_true_lon"][k]), 6)
                if m["operator_true_lon"] is not None else np.nan,
                rx_power_dbm=round(float(prx[k]), 1)))
    return recs, keys


def run(sensors, ctx):
    (ctx.out / "answer_key").mkdir(parents=True, exist_ok=True)
    operator_of = {o.controls: o.id for o in ctx.objects.values() if o.controls}
    streams = {}
    for obj in ctx.objects.values():
        rid = obj.remote_id if obj.remote_id is not None else CATALOG[obj.type].get("remote_id", False)
        if rid and (m := _messages(ctx, obj, operator_of)) is not None:
            streams[obj.id] = m

    for s in sensors:
        recs, keys = _receive(s, ctx, streams)
        order = np.argsort([r["t"] for r in recs], kind="stable") if recs else np.empty(0, int)
        recs, keys = [recs[i] for i in order], [keys[i] for i in order]
        ids = [f"{s.id}-{k:06d}" for k in range(len(recs))]

        det = pd.DataFrame(recs, columns=["t"] + MSG_COLS + ["rx_power_dbm"])
        det.insert(0, "record_id", ids)
        det.insert(1, "time_utc", ctx.iso(np.array([r["t"] for r in recs])))
        det = det[CSV_COLS]
        key = pd.DataFrame(keys, columns=KEY_COLS[1:])
        key.insert(0, "record_id", ids)
        key = key[KEY_COLS]

        folder = ctx.out / "sensors" / s.id
        folder.mkdir(parents=True, exist_ok=True)
        det.to_csv(folder / "messages.csv", index=False)
        det.to_json(folder / "messages.jsonl", orient="records", lines=True)
        key.to_csv(ctx.out / "answer_key" / f"{s.id}.csv", index=False)
