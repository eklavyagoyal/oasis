"""Small 3D surveillance radar (X-band, electronically scanned): the plots it makes and the tracks it keeps.

Per scan and object: line of sight over the real DEM (radar beams don't bend round hills), the radar
equation scaled from a reference (SNR ~ RCS / R^4), Swerling-1 fluctuation, square-law detection
Pd = Pfa^(1 / (1 + SNR)), Gaussian measurement noise that grows as SNR falls, and a micro-Doppler-style
class guess that confuses birds with small rotary drones (and decoys with the real thing) near the noise.
Low-elevation clutter adds false plots. A nearest-neighbour alpha-beta tracker turns plots into tracks
with gaps: the thing that cues cameras and feeds C2.
"""
import json

import numpy as np
import pandas as pd

from ..catalog import CATALOG
from .rf_df import LABEL

DEFAULTS = dict(scan_s=1.0, ref_range_m=3000.0, ref_rcs_m2=0.1, ref_snr_db=16.0, pfa=1e-6, min_range_m=150.0,
                max_range_m=12000.0, sigma_range_m=5.0, sigma_az_deg=0.6, sigma_el_deg=1.0, sigma_vr_mps=0.3,
                clutter_per_scan=0.3)
CLASS_OF = {"quad": "UAV rotary", "delta": "UAV fixed-wing", "fixed_wing": "UAV fixed-wing", "flock": "bird"}
CLASSES = sorted(set(CLASS_OF.values()))
GATE_M, ALPHA, BETA, COAST_S, CONFIRM = 300.0, 0.5, 0.3, 5.0, 3


def _plots(sensor, ctx, p, site, rng):
    t = np.arange(0.0, ctx.cfg.duration_s, p["scan_s"])
    alive = ctx.alive(sensor, t)
    rows, keys = [], []
    for oid, o in ctx.objects.items():
        cat = CATALOG[o.type]
        if "rcs_m2" not in cat:
            continue
        st = ctx.state(oid, t)
        xyz = np.stack([st["x"], st["y"], st["z"]], -1)
        d = xyz - site
        rng_m = np.linalg.norm(d, axis=1)
        use = alive & np.isfinite(rng_m) & (rng_m >= p["min_range_m"]) & (rng_m <= p["max_range_m"])
        i = np.flatnonzero(use)
        if not i.size:
            continue
        los = ctx.world.los(np.broadcast_to(site, (i.size, 3)), xyz[i])
        rcs_eff = cat["rcs_m2"] * rng.exponential(1.0, i.size)  # Swerling 1: new draw every scan
        snr_db = p["ref_snr_db"] + 10 * np.log10(rcs_eff / p["ref_rcs_m2"]) - 40 * np.log10(rng_m[i] / p["ref_range_m"])
        snr = 10 ** (snr_db / 10)
        hit = los & (rng.random(i.size) < p["pfa"] ** (1.0 / (1.0 + snr)))
        j, s = i[hit], snr[hit]
        if not j.size:
            continue
        az = np.degrees(np.arctan2(d[j, 0], d[j, 1])) % 360
        el = np.degrees(np.arctan2(d[j, 2], np.hypot(d[j, 0], d[j, 1])))
        v = np.stack([st["vx"][j], st["vy"][j], st["vz"][j]], -1)
        vr = (v * d[j]).sum(1) / rng_m[j]
        k = np.sqrt(np.clip(20.0 / s, 0.25, 16.0))  # noise grows below ~13 dB
        true_cls = CLASS_OF[cat["shape"]]
        p_wrong = np.clip((15.0 - 10 * np.log10(s)) / 20.0, 0.0, 0.4)
        wrong = rng.random(j.size) < p_wrong
        others = [c for c in CLASSES if c != true_cls]
        rows.append(pd.DataFrame({
            "t": t[j], "range_m": (rng_m[j] + rng.normal(0, p["sigma_range_m"], j.size)).round(1),
            "az_deg": ((az + rng.normal(0, 1, j.size) * p["sigma_az_deg"] * k) % 360).round(2),
            "el_deg": (el + rng.normal(0, 1, j.size) * p["sigma_el_deg"] * k).round(2),
            "vr_mps": (vr + rng.normal(0, p["sigma_vr_mps"], j.size)).round(2),
            "snr_db": (10 * np.log10(s) + rng.normal(0, 1, j.size)).round(1),
            "class": np.where(wrong, rng.choice(others, j.size), true_cls),
            "conf": np.clip(1 - p_wrong + rng.normal(0, 0.05, j.size), 0.05, 0.99).round(2)}))
        keys.append(pd.DataFrame({"object_id": oid, "label": LABEL[o.side], "true_range_m": rng_m[j].round(1),
                                  "true_az_deg": az.round(2), "true_el_deg": el.round(2), "los": True,
                                  "rcs_eff_m2": rcs_eff[hit].round(4)}))
    n = rng.poisson(p["clutter_per_scan"] * t.size)  # ground clutter / anomalous returns near the horizon
    tc = np.sort(rng.choice(t, n)) if n else np.array([])
    tc = tc[ctx.alive(sensor, tc)] if n else tc
    m = tc.size
    rows.append(pd.DataFrame({"t": tc, "range_m": rng.uniform(p["min_range_m"], 0.6 * p["max_range_m"], m).round(1),
                              "az_deg": rng.uniform(0, 360, m).round(2), "el_deg": rng.uniform(0, 2, m).round(2),
                              "vr_mps": rng.normal(0, 0.3, m).round(2), "snr_db": (13 + rng.exponential(1.5, m)).round(1),
                              "class": rng.choice(["bird", "UAV rotary"], m), "conf": rng.uniform(0.2, 0.5, m).round(2)}))
    keys.append(pd.DataFrame({"object_id": [""] * m, "label": "false_alarm"}))
    plots, key = pd.concat(rows, ignore_index=True), pd.concat(keys, ignore_index=True)
    order = np.argsort(plots["t"].to_numpy(), kind="stable")
    plots, key = plots.iloc[order].reset_index(drop=True), key.iloc[order].reset_index(drop=True)
    ids = [f"{sensor.id}-{n:06d}" for n in range(len(plots))]
    plots.insert(0, "record_id", ids)
    plots.insert(1, "time_utc", ctx.iso(plots["t"].to_numpy()))
    key.insert(0, "record_id", ids)
    return plots, key


def _track(plots, ctx, site, scan_s):
    """Nearest-neighbour alpha-beta tracker over the plots (sensor data only)."""
    r, az, el = (np.radians(plots[c].to_numpy()) if c != "range_m" else plots[c].to_numpy()
                 for c in ("range_m", "az_deg", "el_deg"))
    pos = site + np.stack([r * np.cos(el) * np.sin(az), r * np.cos(el) * np.cos(az), r * np.sin(el)], -1)
    tracks, rows, n_tr = [], [], 0
    for t, g in plots.groupby("t", sort=True):
        live = []
        for tr in tracks:  # predict; coast or drop
            tr["x"] = tr["x"] + tr["v"] * (t - tr["t"])
            tr["t"] = t
            if t - tr["last_hit"] <= (COAST_S if tr["confirmed"] else 2 * scan_s):
                live.append(tr)
        tracks, used = live, set()
        for i in g.index:  # greedy nearest-neighbour association
            z = pos[i]
            best = min((tr for tr in tracks if id(tr) not in used), key=lambda tr: np.linalg.norm(z - tr["x"]), default=None)
            if best is not None and np.linalg.norm(z - best["x"]) <= GATE_M:
                res = z - best["x"]
                dt = max(t - best["prev_hit"], scan_s)
                best["x"], best["v"] = best["x"] + ALPHA * res, best["v"] + BETA * res / dt
                best["hits"].append(t)
                best["last_hit"] = best["prev_hit"] = t
                best["cls"].append(plots.at[i, "class"])
                best["plot"], best["plots"] = plots.at[i, "record_id"], best["plots"] + [plots.at[i, "record_id"]]
                used.add(id(best))
            else:
                n_tr += 1
                tracks.append(dict(id=f"T-{n_tr:04d}", x=z.copy(), v=np.zeros(3), t=t, last_hit=t, prev_hit=t,
                                   hits=[t], cls=[plots.at[i, "class"]], plot=plots.at[i, "record_id"],
                                   plots=[plots.at[i, "record_id"]], confirmed=False))
        for tr in tracks:
            recent = [h for h in tr["hits"] if h > t - 5 * scan_s]
            tr["confirmed"] = tr["confirmed"] or len(recent) >= CONFIRM
            if not tr["confirmed"]:
                continue
            hit_now = tr["last_hit"] == t
            lat, lon = ctx.world.to_ll(tr["x"][0], tr["x"][1])
            rows.append(dict(track_id=tr["id"], t=t, lat=round(float(lat), 6), lon=round(float(lon), 6),
                             alt_msl_m=round(float(tr["x"][2]), 1), speed_mps=round(float(np.linalg.norm(tr["v"][:2])), 1),
                             heading_deg=round(float(np.degrees(np.arctan2(tr["v"][0], tr["v"][1])) % 360), 1),
                             **{"class": max(set(tr["cls"]), key=tr["cls"].count)},
                             quality=round(len(recent) / 5.0, 2), state="CONFIRMED" if hit_now else "COASTING",
                             plot_record_id=tr["plot"] if hit_now else ""))
    out = pd.DataFrame(rows, columns=["track_id", "t", "lat", "lon", "alt_msl_m", "speed_mps", "heading_deg",
                                      "class", "quality", "state", "plot_record_id"])
    out.insert(1, "time_utc", ctx.iso(out["t"].to_numpy()) if len(out) else [])
    return out


def run(sensors, ctx):
    (ctx.out / "answer_key").mkdir(parents=True, exist_ok=True)
    for s in sensors:
        p = {**DEFAULTS, **s.params}
        unknown = set(p) - set(DEFAULTS)
        if unknown:
            raise ValueError(f"radar {s.id}: unknown params {sorted(unknown)}")
        rng = ctx.rng(f"radar:{s.id}")
        site = ctx.sensor_xyz(s)
        plots, key = _plots(s, ctx, p, site, rng)
        tracks = _track(plots, ctx, site, p["scan_s"])
        folder = ctx.out / "sensors" / s.id
        folder.mkdir(parents=True, exist_ok=True)
        plots.to_csv(folder / "plots.csv", index=False)
        tracks.to_csv(folder / "tracks.csv", index=False)
        key.to_csv(ctx.out / "answer_key" / f"{s.id}.csv", index=False)
        lat, lon = ctx.world.to_ll(site[0], site[1])
        (folder / "site.json").write_text(json.dumps({"sensor_id": s.id, "lat": round(float(lat), 6),
                                                     "lon": round(float(lon), 6), "alt_msl_m": round(float(site[2]), 1),
                                                     "mast_m": s.mast_m}, indent=1))
        # track answer key: which object each track mostly followed (a track can be "mixed")
        obj_of = dict(zip(key["record_id"], key["object_id"]))
        ak = []
        for tid, g in tracks[tracks["plot_record_id"] != ""].groupby("track_id"):
            objs = [obj_of.get(r, "") for r in g["plot_record_id"]]
            top = max(set(objs), key=objs.count)
            ak.append(dict(track_id=tid, object_id=top if objs.count(top) >= 0.8 * len(objs) else "mixed",
                           n_plots=len(objs), life_s=round(float(g["t"].max() - g["t"].min()), 1)))
        pd.DataFrame(ak, columns=["track_id", "object_id", "n_plots", "life_s"]).to_csv(
            ctx.out / "answer_key" / f"{s.id}_tracks.csv", index=False)
