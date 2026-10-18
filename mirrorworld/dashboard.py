"""3D replay dashboard: export out/<name>/ to a CesiumJS viewer and serve it.

`python -m mirrorworld dash out/<name> [--serve] [--port 8765]` copies the static app from
mirrorworld/dashboard/ into out/<name>/dashboard/ and writes data.js (`window.MW = {...}`)
holding the whole scenario in compact parallel arrays: terrain DEM, truth tracks, sensor
sites, RF detections + answer key, fused fixes, terrain-shadow maps, key events, media
and the audit. With --serve an http.server is rooted at out/<name>/.
"""
from __future__ import annotations

import argparse
import functools
import http.server
import json
import math
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import config
from .__main__ import Context
from .config import M_PER_DEG
from .truth import iso
from .world import World

STATIC_DIR = Path(__file__).resolve().parent / "dashboard"
NX = NY = 241          # terrain grid over the area (lon x lat)
SX = SY = 121          # terrain-shadow grid per rf sensor
LABELS = ["target", "friendly", "clutter", "false_alarm"]
NLOS_MIN_S = 30.0      # occlusion events need runs at least this long


# ---------------------------------------------------------------- helpers
def _f(v, nd: int) -> float | None:
    """Rounded float, or None for missing/NaN."""
    if v is None:
        return None
    v = float(v)
    return None if math.isnan(v) else round(v, nd)


def _clean(v):
    """Safety net for json.dumps(allow_nan=False): round stray floats, kill NaN/Inf."""
    if isinstance(v, float):
        return None if not math.isfinite(v) else round(v, 6)
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v]
    return v


def _blank_to_none(v):
    return None if v is None or (isinstance(v, float) and math.isnan(v)) or v == "" else v


def _runs(los: np.ndarray):
    """Contiguous runs of equal values: (lo, hi_inclusive, value)."""
    if los.size == 0:
        return
    change = np.flatnonzero(np.diff(los)) + 1
    starts = np.concatenate([[0], change])
    ends = np.concatenate([change - 1, [los.size - 1]])
    for a, b in zip(starts, ends):
        yield int(a), int(b), bool(los[b])


# ---------------------------------------------------------------- build
def build(out: Path | str) -> dict:
    """Build the whole MW payload from an out/<name>/ run directory."""
    out = Path(out)
    cfg = config.load(out / "scenario.yaml")
    world = World(cfg)
    truth = pd.read_csv(out / "truth" / "tracks.csv")
    objs_df = pd.read_csv(out / "truth" / "objects.csv").set_index("id")
    ctx = Context(cfg, world, truth, {o.id: o for o in cfg.objects}, out)

    obj_ids = list(objs_df.index)
    obj_ix = {oid: i for i, oid in enumerate(obj_ids)}

    # ---- scenario ------------------------------------------------------
    w = cfg.weather
    scenario = {
        "name": cfg.name,
        "start": iso(cfg.start, 0.0),
        "duration_s": _f(cfg.duration_s, 3),
        "area": {"lat": cfg.area.lat, "lon": cfg.area.lon, "size_km": cfg.area.size_km},
        "weather": {"wind_from_deg": w.wind_from_deg, "wind_mps": _f(w.wind_mps, 2),
                    "temp_c": w.temp_c, "rh_pct": w.rh_pct,
                    "visibility_km": w.visibility_km, "cloud_pct": w.cloud_pct},
    }

    # ---- terrain (rows south->north, cols west->east) ------------------
    dlat = cfg.area.size_km * 500.0 / M_PER_DEG
    dlon = dlat / math.cos(math.radians(cfg.area.lat))
    west, east = cfg.area.lon - dlon, cfg.area.lon + dlon
    south, north = cfg.area.lat - dlat, cfg.area.lat + dlat
    glats = np.linspace(south, north, NY)
    glons = np.linspace(west, east, NX)
    lon_g, lat_g = np.meshgrid(glons, glats)
    x, y = world.to_xy(lat_g, lon_g)
    h = world.height(x, y)
    terrain = {"west": _f(west, 6), "south": _f(south, 6), "east": _f(east, 6),
               "north": _f(north, 6), "nx": NX, "ny": NY,
               "h": [round(float(v), 1) for v in h.reshape(-1)]}

    # ---- objects: truth tracks downsampled to 1 Hz ---------------------
    static = {o.id for o in cfg.objects if o.pos is not None}
    objects = []
    for oid in obj_ids:
        rows = truth[truth["object_id"] == oid].sort_values("t")
        if rows.empty:
            continue
        ts = rows["t"].to_numpy()
        if oid in static:  # never moves: two samples are plenty
            idx = [0, len(ts) - 1] if len(ts) > 1 else [0]
        else:  # nearest actual tick to each integer second
            targets = np.arange(math.ceil(ts[0] - 1e-9), math.floor(ts[-1] + 1e-9) + 1)
            if targets.size == 0:
                targets = np.array([round(float(ts[len(ts) // 2]))])
            pos = np.searchsorted(ts, targets)
            lo = np.clip(pos - 1, 0, len(ts) - 1)
            hi = np.clip(pos, 0, len(ts) - 1)
            pick = np.where(np.abs(ts[lo] - targets) <= np.abs(ts[hi] - targets), lo, hi)
            idx = sorted(set(int(i) for i in pick))
        sub = rows.iloc[idx]
        objects.append({
            "id": oid,
            "type": str(objs_df.at[oid, "type"]),
            "kind": str(objs_df.at[oid, "kind"]),
            "side": str(objs_df.at[oid, "side"]),
            "controls": _blank_to_none(objs_df.at[oid, "controls"]),
            "t": [_f(t, 3) for t in sub["t"]],
            "lat": [_f(v, 6) for v in sub["lat"]],
            "lon": [_f(v, 6) for v in sub["lon"]],
            "alt": [_f(v, 1) for v in sub["alt_msl_m"]],
        })

    # ---- sensors (Context resolves mount and destroyed_by) -------------
    sensors, dead_t = [], {}
    for s in cfg.sensors:
        xyz = ctx.sensor_xyz(s)
        lat, lon = world.to_ll(xyz[0], xyz[1])
        dead = None
        if s.destroyed_by:
            dead = _f(truth.loc[truth["object_id"] == s.destroyed_by, "t"].max(), 3)
            dead_t[s.id] = dead
        sensors.append({"id": s.id, "type": s.type, "lat": _f(lat, 6), "lon": _f(lon, 6),
                        "ground": _f(xyz[2] - s.mast_m, 1), "alt": _f(xyz[2], 1),
                        "mast_m": s.mast_m, "dead_t": dead})

    # ---- rf: detections joined with the answer key ---------------------
    rf_sensors = [s for s in cfg.sensors if s.type == "rf_df"]
    det_by, key_by, classes, links = {}, {}, set(), set()
    for s in rf_sensors:
        det = pd.read_csv(out / "sensors" / s.id / "detections.csv")
        key = pd.read_csv(out / "answer_key" / f"{s.id}.csv")
        det_by[s.id] = det
        key_by[s.id] = key
        classes.update(str(v) for v in det["sig_class"].dropna().unique())
        links.update(str(v) for v in key["link"].dropna().unique() if v != "")

    fixes_df = pd.read_csv(out / "fused" / "fixes.csv")
    fixes_key = pd.read_csv(out / "answer_key" / "fused.csv")
    classes.update(str(v) for v in fixes_df["sig_class"].dropna().unique())
    classes, links = sorted(classes), sorted(links)
    cls_ix = {c: i for i, c in enumerate(classes)}
    link_ix = {l: i for i, l in enumerate(links)}
    label_ix = {l: i for i, l in enumerate(LABELS)}

    rf = {}
    for s in rf_sensors:
        det, key = det_by[s.id], key_by[s.id]
        m = det.merge(key, on="record_id", how="left", sort=False)

        def _obj(v):
            return -1 if v is None or (isinstance(v, float) and math.isnan(v)) or v == "" \
                else obj_ix.get(str(v), -1)

        def _los(v):
            return 1 if v is True or (isinstance(v, str) and v.strip().lower() == "true") else 0

        rf[s.id] = {
            "t": [_f(v, 3) for v in m["t"]],
            "brg": [_f(v, 2) for v in m["bearing_deg"]],
            "std": [_f(v, 2) for v in m["bearing_std_deg"]],
            "snr": [_f(v, 1) for v in m["snr_db"]],
            "pwr": [_f(v, 1) for v in m["power_dbm"]],
            "cls": [cls_ix.get(str(v), -1) for v in m["sig_class"]],
            "obj": [_obj(v) for v in m["object_id"]],
            "link": [link_ix.get(str(v), -1) if not (isinstance(v, float) and math.isnan(v)) else -1
                     for v in m["link"]],
            "los": [_los(v) for v in m["los"]],
            "label": [label_ix.get(str(v), -1) for v in m["label"]],
        }

    # ---- fixes ---------------------------------------------------------
    fm = fixes_df.merge(fixes_key, on="fix_id", how="left", sort=False)
    fixes = {
        "t": [_f(v, 3) for v in fm["t"]],
        "lat": [_f(v, 6) for v in fm["lat"]],
        "lon": [_f(v, 6) for v in fm["lon"]],
        "smaj": [_f(v, 1) for v in fm["semi_major_m"]],
        "smin": [_f(v, 1) for v in fm["semi_minor_m"]],
        "orient": [_f(v, 1) for v in fm["orient_deg"]],
        "ce": [_f(v, 1) for v in fm["ce_m"]],
        "cep50": [_f(v, 1) for v in fm["cep50_m"]],
        "cls": [cls_ix.get(str(v), -1) for v in fm["sig_class"]],
        "obj": [-1 if (isinstance(v, float) and math.isnan(v)) or v in ("", "mixed")
                else obj_ix.get(str(v), -1) for v in fm["object_id"]],
        "err": [_f(v, 1) for v in fm["error_m"]],
    }

    # ---- terrain-shadow maps ------------------------------------------
    slats = np.linspace(south, north, SY)
    slons = np.linspace(west, east, SX)
    slon_g, slat_g = np.meshgrid(slons, slats)
    sx, sy = world.to_xy(slat_g, slon_g)
    sx, sy = sx.reshape(-1), sy.reshape(-1)
    shadow = {}
    for s in rf_sensors:
        agl = world.min_visible_agl(ctx.sensor_xyz(s), sx, sy)
        agl = np.clip(np.round(agl), 0, 3000).astype(int)
        shadow[s.id] = {"west": _f(west, 6), "south": _f(south, 6), "east": _f(east, 6),
                        "north": _f(north, 6), "nx": SX, "ny": SY,
                        "agl": [int(v) for v in agl]}

    # ---- events --------------------------------------------------------
    events = []

    def add(t, label, kind):
        events.append({"t": _f(t, 3), "label": label, "kind": kind})

    for oid in obj_ids:  # drones: first and last truth tick
        if str(objs_df.at[oid, "kind"]) != "drone":
            continue
        ts = truth.loc[truth["object_id"] == oid, "t"]
        if ts.empty:
            continue
        add(ts.min(), f"{oid} airborne", "airborne")
        add(ts.max(), f"{oid} ends", "ends")

    for s in cfg.sensors:  # dead sensors
        if s.id in dead_t:
            add(dead_t[s.id], f"{s.id} destroyed by {s.destroyed_by}", "destroyed")

    for o in cfg.objects:  # static emitters on/off
        if str(objs_df.at[o.id, "kind"]) != "emitter":
            continue
        add(o.start_s, f"{o.id} on", "on")
        if o.end_s is not None:
            add(o.end_s, f"{o.id} off", "off")

    for s in rf_sensors:  # terrain occlusion intervals
        site = ctx.sensor_xyz(s)
        for oid in obj_ids:
            if str(objs_df.at[oid, "kind"]) != "drone":
                continue
            so = next(x for x in objects if x["id"] == oid)
            ts = np.array(so["t"], dtype=float)
            if ts.size < 2:
                continue
            lats, lons, alts = (np.array(so[k], dtype=float) for k in ("lat", "lon", "alt"))
            px, py = world.to_xy(lats, lons)
            pts = np.stack([px, py, alts], axis=1)
            los = np.empty(ts.size, dtype=bool)
            for a in range(0, ts.size, 2048):
                los[a:a + 2048] = world.los(np.broadcast_to(site, pts[a:a + 2048].shape),
                                            pts[a:a + 2048])
            for lo_, hi_, val in _runs(los):
                if val:  # LOS run, skip
                    continue
                start = ts[lo_]  # NLOS run: drone hidden by terrain
                end = ts[hi_ + 1] if hi_ + 1 < ts.size else None
                span = (end if end is not None else ts[hi_] + 1.0) - start
                if span >= NLOS_MIN_S:
                    add(start, f"{oid} hidden from {s.id} by terrain", "hidden")
                    if end is not None:
                        add(end, f"{oid} visible again to {s.id}", "visible")

    # ---- media ---------------------------------------------------------
    media = []
    start_dt = cfg.start.replace(tzinfo=timezone.utc)
    for s in cfg.sensors:
        folder = out / "sensors" / s.id
        if not folder.is_dir():
            continue
        mc = folder / "media.csv"
        if mc.exists():
            rows = pd.read_csv(mc)
            for _, r in rows.iterrows():
                kind = str(r.get("kind", ""))
                path = str(r.get("path", ""))
                if kind == "event":
                    add(float(r["t"]), path, "media")
                elif kind in ("image", "audio", "iq"):
                    if path.startswith(("/", "~")) or "\\" in path or ".." in Path(path).parts:
                        raise ValueError(f"{mc}: media path {path!r} must be a plain relative path")
                    media.append({"sensor": s.id, "kind": kind, "t": _f(r["t"], 3),
                                  "src": f"../sensors/{s.id}/{path}"})
        for png in sorted(folder.glob("snap_*.png")):  # rf_iq recorder snapshots
            meta = png.with_suffix(".sigmf-meta")
            if not meta.exists():
                continue
            try:
                cap = json.loads(meta.read_text()).get("captures", [{}])[0]
                dt = datetime.fromisoformat(str(cap["core:datetime"]).replace("Z", "+00:00"))
                t = (dt - start_dt).total_seconds()
            except (ValueError, KeyError, IndexError):
                continue
            media.append({"sensor": s.id, "kind": "image", "t": _f(t, 3),
                          "src": f"../sensors/{s.id}/{png.name}"})

    events.sort(key=lambda e: (e["t"], e["label"]))
    media.sort(key=lambda m: (m["t"], m["sensor"]))

    # ---- audit ---------------------------------------------------------
    audit = None
    ap = out / "audit.json"
    if ap.exists():
        audit = json.loads(ap.read_text())

    return _clean({
        "scenario": scenario,
        "terrain": terrain,
        "objects": objects,
        "sensors": sensors,
        "classes": classes,
        "links": links,
        "labels": LABELS,
        "rf": rf,
        "fixes": fixes,
        "shadow": shadow,
        "events": events,
        "media": media,
        "audit": audit,
    })


# ---------------------------------------------------------------- export / serve
def export(out: Path | str) -> Path:
    """Copy the static app and write data.js into out/<name>/dashboard/."""
    out = Path(out)
    dst = out / "dashboard"
    dst.mkdir(parents=True, exist_ok=True)
    for f in sorted(STATIC_DIR.iterdir()):
        if f.is_file() and not f.name.startswith("."):
            shutil.copyfile(f, dst / f.name)
    payload = build(out)
    js = "window.MW = " + json.dumps(payload, separators=(",", ":"), allow_nan=False) + ";\n"
    (dst / "data.js").write_text(js)
    print(f"wrote {dst}/ ({len(js) / 1024:.0f} kB data.js)")
    return dst


class _Static(http.server.SimpleHTTPRequestHandler):
    """Static files only, no directory listings, and only for local or tailnet host names
    (a DNS-rebinding guard; `tailscale serve` forwards the *.ts.net Host header)."""

    def send_head(self):
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0].lower()
        if host not in ("localhost", "127.0.0.1") and not host.endswith(".ts.net"):
            self.send_error(403, "host not allowed")
            return None
        return super().send_head()

    def list_directory(self, path):
        self.send_error(403, "directory listing disabled")
        return None


def serve(out: Path | str, port: int) -> None:
    handler = functools.partial(_Static, directory=str(Path(out).resolve()))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    print(f"serving http://localhost:{port}/dashboard/", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    ap = argparse.ArgumentParser(prog="mirrorworld dash",
                                 description="Export / serve the 3D replay dashboard.")
    ap.add_argument("out", help="run directory, e.g. out/ros-valley")
    ap.add_argument("--serve", action="store_true", help="serve the run directory over http")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args(argv)
    export(args.out)
    if args.serve:
        serve(args.out, args.port)


if __name__ == "__main__":
    main()
