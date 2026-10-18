"""Telemetry receiver: our own drones' downlinked flight logs (MAVLink-like, 5 Hz).

The log is what each drone's flight controller believes: positions from its own GNSS fix,
velocity from the smoothed GNSS track. GNSS spoofing therefore shows up as drifting positions,
phantom velocity and a suspiciously clean satellite fix — the sensor never knows it is spoofed.
"""
import numpy as np
import pandas as pd

from .rf_df import LABEL

HZ = 5.0
HALF_WIN_S = 10.0  # velocity from +-10 s central differences: averages fix noise to ~0.2 m/s
CLIP_MPS = 40.0  # receiver clamps implausible track rates (the spoof snap-back step)
ENDURANCE_S = 2700.0  # battery: linear drain over a ~45 min flight
CSV_COLS = ["record_id", "time_utc", "t", "lat_e7", "lon_e7", "alt_mm", "relative_alt_mm",
            "vx_cms", "vy_cms", "vz_cms", "hdg_cdeg", "groundspeed", "satellites_visible",
            "cn0_dbhz", "hdop", "battery_pct", "ekf_vel_innov"]
KEY_COLS = ["record_id", "object_id", "link", "label", "true_lat", "true_lon", "true_alt",
            "gnss_error_m", "spoofed"]


def _track_velocity(t, gx, gy, gz):
    """Velocity from central differences of the GNSS track over +-HALF_WIN_S (see remote_id)."""
    n = t.size
    k = max(int(round(HALF_WIN_S / float(np.median(np.diff(t))))) if n > 1 else 1, 1)
    i0, i1 = np.clip(np.arange(n) - k, 0, n - 1), np.clip(np.arange(n) + k, 0, n - 1)
    dt = np.where(t[i1] > t[i0], t[i1] - t[i0], 1.0)
    v = np.stack([(p[i1] - p[i0]) / dt for p in (gx, gy, gz)], -1)
    return v * np.minimum(1.0, CLIP_MPS / np.maximum(np.linalg.norm(v, axis=1), 1e-9))[:, None]


def _interp(rows, t, col):
    return np.interp(t, rows["t"].to_numpy(), rows[col].to_numpy(), left=np.nan, right=np.nan)


def _log(ctx, obj, rng):
    """One drone's 5 Hz log rows and the answer-key rows behind them."""
    rows = ctx.truth[ctx.truth["object_id"] == obj.id].sort_values("t")
    if rows.empty:
        return [], []
    t = np.arange(float(rows["t"].iloc[0]), float(rows["t"].iloc[-1]) + 1e-9, 1.0 / HZ)
    g_lat, g_lon, g_alt = (_interp(rows, t, c) for c in ("gnss_lat", "gnss_lon", "gnss_alt_msl_m"))
    t_lat, t_lon, t_alt = (_interp(rows, t, c) for c in ("lat", "lon", "alt_msl_m"))
    gx, gy = ctx.world.to_xy(g_lat, g_lon)
    x_true, y_true = ctx.world.to_xy(t_lat, t_lon)
    v = _track_velocity(t, gx, gy, g_alt)
    st = ctx.state(obj.id, t)
    innov = np.hypot(*(v - np.stack([st["vx"], st["vy"], st["vz"]], -1)).T)

    spoof = np.zeros(t.size, bool)
    if obj.gnss_spoof is not None:
        # the declared window, plus the snap-back transition: the truth table drops the drift
        # between ticks, so fine samples right after end_s still carry displaced fixes
        err = np.hypot(gx - x_true, gy - y_true)
        spoof = ((t >= obj.gnss_spoof.start_s) & (t <= obj.gnss_spoof.end_s)) | (err > 25.0)
    n = t.size
    # a spoofer broadcasts many strong, clean signals: more sats, higher C/N0, unrealistically
    # good DOP — suspiciously stable where an honest sky jitters
    sats = np.where(spoof, 25 + rng.choice([-1, 0, 0, 0, 1], n),
                    np.clip(20 + np.rint(rng.normal(0, 1.2, n)), 18, 22)).astype(int)
    cn0 = np.where(spoof, 46.0 + rng.normal(0, 0.3, n),
                   np.clip(41.5 + rng.normal(0, 1.5, n), 38, 45))
    hdop = np.where(spoof, np.clip(0.50 + rng.normal(0, 0.02, n), 0.45, 0.60),
                    rng.uniform(0.6, 0.9, n))

    recs = pd.DataFrame({
        "t": t,
        "time_utc": ctx.iso(t),
        "lat_e7": np.rint(g_lat * 1e7).astype(np.int64),
        "lon_e7": np.rint(g_lon * 1e7).astype(np.int64),
        "alt_mm": np.rint(g_alt * 1000).astype(np.int64),
        "relative_alt_mm": np.rint((g_alt - g_alt[0]) * 1000).astype(np.int64),
        "vx_cms": np.rint(v[:, 0] * 100).astype(np.int64),
        "vy_cms": np.rint(v[:, 1] * 100).astype(np.int64),
        "vz_cms": np.rint(v[:, 2] * 100).astype(np.int64),
        "hdg_cdeg": np.rint((np.degrees(np.arctan2(v[:, 0], v[:, 1])) % 360) * 100).astype(np.int64),
        "groundspeed": np.round(np.hypot(v[:, 0], v[:, 1]), 2),
        "satellites_visible": sats,
        "cn0_dbhz": np.round(cn0, 1),
        "hdop": np.round(hdop, 2),
        "battery_pct": np.round(np.clip(100 * (1 - (t - t[0]) / ENDURANCE_S), 0, 100), 1),
        "ekf_vel_innov": np.round(innov, 2),
    })
    key = pd.DataFrame({
        "object_id": obj.id, "link": "telemetry", "label": LABEL[obj.side],
        "true_lat": np.round(t_lat, 6), "true_lon": np.round(t_lon, 6),
        "true_alt": np.round(t_alt, 1),
        "gnss_error_m": np.round(np.hypot(gx - x_true, gy - y_true), 2),
        "spoofed": spoof,
    })
    return recs.to_dict("records"), key.to_dict("records")


def run(sensors, ctx):
    (ctx.out / "answer_key").mkdir(parents=True, exist_ok=True)
    for s in sensors:
        ids = s.params.get("objects")
        if not ids:
            raise ValueError(f"{s.id}: params.objects must list the object ids whose telemetry "
                             f"this receiver logs")
        if unknown := [i for i in ids if i not in ctx.objects]:
            raise ValueError(f"{s.id}: params.objects names unknown object(s) {unknown}; "
                             f"known: {sorted(ctx.objects)}")
        rng = ctx.rng(f"telemetry:{s.id}")
        recs, keys = [], []
        for oid in ids:
            r, k = _log(ctx, ctx.objects[oid], rng)
            recs += r
            keys += k
        order = sorted(range(len(recs)), key=lambda i: recs[i]["t"])
        recs, keys = [recs[i] for i in order], [keys[i] for i in order]
        ids_out = [f"{s.id}-{k:06d}" for k in range(len(recs))]

        all_rows = pd.DataFrame(recs, columns=["t", "time_utc"] + CSV_COLS[3:])
        all_rows.insert(0, "record_id", ids_out)
        all_rows = all_rows[CSV_COLS]
        all_keys = pd.DataFrame(keys, columns=KEY_COLS[1:])
        all_keys.insert(0, "record_id", ids_out)
        all_keys = all_keys[KEY_COLS]

        folder = ctx.out / "sensors" / s.id
        folder.mkdir(parents=True, exist_ok=True)
        obj_of = np.array([k["object_id"] for k in keys], dtype=object)
        for oid in ids:
            all_rows[obj_of == oid].to_csv(folder / f"{oid}.csv", index=False)
        all_keys.to_csv(ctx.out / "answer_key" / f"{s.id}.csv", index=False)
