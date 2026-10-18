"""Audit tests: plain asserts, run with `uv run python tests/test_audit.py` (no pytest).

Builds tiny synthetic run directories against a deterministic ridge world (no DEM download)
and checks the audit's core physics: exact geometric bearings pass bearing_geometry, random
bearings fail it, and NLOS power indistinguishable from LOS power fails terrain_shadow.
"""
import math
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mirrorworld import audit  # noqa: E402
from mirrorworld.itu import fspl_db  # noqa: E402
from mirrorworld.truth import iso  # noqa: E402

START = datetime(2026, 11, 4, 8, 55, tzinfo=timezone.utc)
F_MHZ, EIRP_DBM = 2437.0, 26.0  # dji_mavic3 video link
SITE_XY, LOS_XY, NLOS_XY = (-4000.0, 0.0), (-2000.0, 600.0), (2000.0, 600.0)


class FakeWorld:
    """150 m plain with a 300 m ridge along y at x=0: same API surface the audit uses."""

    def __init__(self, cfg):
        self.lat0, self.lon0 = cfg.area.lat, cfg.area.lon
        self.cos0 = math.cos(math.radians(self.lat0))

    def to_xy(self, lat, lon):
        lat, lon = np.asarray(lat, float), np.asarray(lon, float)
        return (lon - self.lon0) * 111_195.0 * self.cos0, (lat - self.lat0) * 111_195.0

    def to_ll(self, x, y):
        x, y = np.asarray(x, float), np.asarray(y, float)
        return self.lat0 + y / 111_195.0, self.lon0 + x / (111_195.0 * self.cos0)

    def height(self, x, y):
        return 150.0 + 150.0 * np.exp(-(np.asarray(x, float) / 800.0) ** 2)

    def los(self, a, b):
        a, b = np.broadcast_arrays(np.asarray(a, float), np.asarray(b, float))
        ts = np.linspace(0.0, 1.0, 64)[1:-1]
        xs = a[..., 0, None] + (b[..., 0] - a[..., 0])[..., None] * ts
        ys = a[..., 1, None] + (b[..., 1] - a[..., 1])[..., None] * ts
        zs = a[..., 2, None] + (b[..., 2] - a[..., 2])[..., None] * ts
        clear = (zs > self.height(xs, ys)).all(axis=-1)
        return bool(clear) if a.ndim == 1 else clear


def build(root, name, bearings, nlos_excess_db):
    """One synthetic run dir: static drone behind or beside the ridge, RF1 watching it."""
    w = FakeWorld(SimpleNamespace(area=SimpleNamespace(lat=49.37, lon=31.20)))
    rng = np.random.default_rng(7)
    site = np.array([SITE_XY[0], SITE_XY[1], float(w.height(*SITE_XY)) + 30.0])
    blocks = [(0.0, 40.0, LOS_XY, 2.0), (80.0, 120.0, NLOS_XY, nlos_excess_db)]

    out = Path(root) / name
    (out / "truth").mkdir(parents=True)
    (out / "sensors" / "RF1").mkdir(parents=True)
    (out / "answer_key").mkdir()

    rows, det, key = [], [], []
    n = 0
    for t0, t1, xy, excess in blocks:
        z = float(w.height(*xy)) + 40.0
        tgt = np.array([xy[0], xy[1], z])
        brg_geom = math.degrees(math.atan2(tgt[0] - site[0], tgt[1] - site[1])) % 360.0
        rng_m = float(np.linalg.norm(tgt - site))
        power = EIRP_DBM - fspl_db(rng_m / 1000.0, F_MHZ / 1000.0) - excess
        lat, lon = w.to_ll(xy[0], xy[1])
        lat, lon, z = round(float(lat), 6), round(float(lon), 6), round(z, 3)
        for t in np.arange(t0, t1 + 0.5, 0.5):  # truth at 2 Hz
            rows.append((t, iso(START, t), "drone_1", lat, lon, z, 40.0,
                         xy[0], xy[1], z, 0.0, 0.0, 0.0, 0.0, 0.0, lat, lon, z))
        for t in np.arange(t0, t1 + 0.5, 1.0):  # detector reports at 1 Hz
            b = brg_geom if bearings == "exact" else float(rng.uniform(0, 360))
            det.append((f"RF1-{n:06d}", iso(START, t), t, "RF1", F_MHZ, 20.0, round(power, 1),
                        20.0, round(b, 1), 2.0, "OcuSync video", 0.9, ""))
            key.append((f"RF1-{n:06d}", "drone_1", "drone_1:video", "clutter"))
            n += 1

    pd.DataFrame(rows, columns="t,time_utc,object_id,lat,lon,alt_msl_m,alt_agl_m,x_m,y_m,z_m,"
                 "vx,vy,vz,speed_mps,heading_deg,gnss_lat,gnss_lon,gnss_alt_msl_m".split(",")).to_csv(
        out / "truth" / "tracks.csv", index=False)
    pd.DataFrame([{"id": "drone_1", "type": "dji_mavic3", "kind": "drone", "side": "neutral", "controls": ""}]).to_csv(
        out / "truth" / "objects.csv", index=False)
    pd.DataFrame(det, columns="record_id,time_utc,t,sensor_id,freq_mhz,bw_mhz,power_dbm,snr_db,"
                 "bearing_deg,bearing_std_deg,sig_class,class_conf,emitter_id".split(",")).to_csv(
        out / "sensors" / "RF1" / "detections.csv", index=False)
    pd.DataFrame(key, columns=["record_id", "object_id", "link", "label"]).to_csv(
        out / "answer_key" / "RF1.csv", index=False)
    site_ll = w.to_ll(site[0], site[1])
    (out / "sensors" / "RF1" / "site.json").write_text(
        '{"sensor_id": "RF1", "lat": %f, "lon": %f, "alt_msl_m": %.1f, "mast_m": 30.0}'
        % (float(site_ll[0]), float(site_ll[1]), site[2]))
    (out / "scenario.yaml").write_text(f"""\
name: {name}
seed: 7
start: 2026-11-04T08:55:00Z
duration_s: 200
truth_hz: 2
area: {{lat: 49.37, lon: 31.20, size_km: 16}}
weather: {{wind_from_deg: 270, wind_mps: 3.5, temp_c: 4, rh_pct: 85, visibility_km: 12, cloud_pct: 40}}
objects:
  - {{id: drone_1, type: dji_mavic3, side: neutral, pos: [{lat}, {lon}]}}
sensors:
  - {{id: RF1, type: rf_df, pos: [{float(site_ll[0]):.6f}, {float(site_ll[1]):.6f}], mast_m: 30}}
""")
    return out


def checks(out):
    return {c["id"]: c for c in audit.audit_dir(out)["checks"]}


def main():
    audit.World = FakeWorld  # deterministic terrain here; the hero run exercises the real DEM
    tmp = Path(tempfile.mkdtemp(prefix="mw-audit-test-"))
    try:
        a = checks(build(tmp, "fixture-a", "exact", 25.0))
        assert a["clock"]["status"] == "PASS", a["clock"]            # fixture itself is sound
        assert a["provenance"]["status"] == "PASS", a["provenance"]
        assert a["bearing_geometry"]["status"] == "PASS", a["bearing_geometry"]
        assert a["bearing_geometry"]["value"] == 1.0, a["bearing_geometry"]
        assert a["terrain_shadow"]["status"] == "PASS", a["terrain_shadow"]
        assert abs(a["terrain_shadow"]["value"] - 23.0) < 1.0, a["terrain_shadow"]  # 25 dB NLOS excess - 2 dB LOS

        b = checks(build(tmp, "fixture-b", "random", 25.0))
        assert b["bearing_geometry"]["status"] == "FAIL", b["bearing_geometry"]
        assert b["bearing_geometry"]["value"] < 0.2, b["bearing_geometry"]

        c = checks(build(tmp, "fixture-c", "exact", 2.0))
        assert c["bearing_geometry"]["status"] == "PASS", c["bearing_geometry"]
        assert c["terrain_shadow"]["status"] == "FAIL", c["terrain_shadow"]
        print("test_audit: OK")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
