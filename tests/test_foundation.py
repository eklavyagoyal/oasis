"""Foundation tests: plain asserts, run with `uv run python tests/test_foundation.py`."""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mirrorworld import config  # noqa: E402
from mirrorworld.truth import simulate  # noqa: E402
from mirrorworld.world import World  # noqa: E402


def bare_world(grid=None):
    """World without a DEM download: local frame, optionally a monkeypatched grid."""
    w = World.__new__(World)
    w.lat0, w.lon0 = 49.365, 31.228
    w.cos0 = math.cos(math.radians(w.lat0))
    if grid is not None:
        w.grid = np.asarray(grid, dtype=np.float32)
        w.spacing = 30.0
        w.n = w.grid.shape[0]
        w.x0 = w.y0 = -w.spacing * (w.n - 1) / 2.0
    return w


def scenario(objects):
    return config.Scenario.model_validate({
        "name": "test", "seed": 7, "start": "2026-11-03T13:55:00Z",
        "duration_s": 35, "truth_hz": 2, "area": {"lat": 49.365, "lon": 31.228, "size_km": 4},
        "objects": objects, "sensors": [],
    })


# --- to_xy / to_ll round trip -------------------------------------------
w = bare_world()
lat, lon = np.array([49.35, 49.365, 49.38]), np.array([31.20, 31.228, 31.25])
x, y = w.to_xy(lat, lon)
lat2, lon2 = w.to_ll(x, y)
assert np.allclose(lat2, lat) and np.allclose(lon2, lon), "to_xy/to_ll round trip"
xs, ys = w.to_xy(49.365, 31.228)
assert float(xs) == 0.0 and float(ys) == 0.0, "area centre maps to origin"

# --- LOS over a synthetic ridge -----------------------------------------
n = 101
ridge = np.zeros((n, n), dtype=np.float32)
ridge[:, n // 2 - 1:n // 2 + 2] = 200.0  # 200 m ridge across the middle
w = bare_world(ridge)
a_low = np.array([-1000.0, 0.0, 50.0])
b_low = np.array([1000.0, 0.0, 50.0])
assert not w.los(a_low, b_low), "ray below the ridge top must be blocked"
a_high = np.array([-1000.0, 0.0, 350.0])
b_high = np.array([1000.0, 0.0, 350.0])
assert w.los(a_high, b_high), "ray well above the ridge top must clear"
assert w.los(a_low + [0, 0, 300], b_low + [0, 0, 300]), "batch/list form"

# --- truth: 2-waypoint path at known speed -------------------------------
w = bare_world(np.zeros((101, 101), dtype=np.float32))
dlon = 300.0 / (config.M_PER_DEG * w.cos0)  # 300 m due east of the origin
cfg = scenario([{"id": "p", "type": "dji_mavic3", "speed_mps": 10.0,
                 "path": [[49.365, 31.228, 50], [49.365, 31.228 + dlon, 50]]}])
tr = simulate(cfg, w, np.random.default_rng(0))
row = tr[(tr["object_id"] == "p") & np.isclose(tr["t"], 20.0)]
assert len(row) == 1, "exactly one truth row at t=20"
assert abs(row["x_m"].iloc[0] - 200.0) < 1e-6, f"x at t=20: {row['x_m'].iloc[0]}"
assert abs(row["y_m"].iloc[0]) < 1e-6 and abs(row["z_m"].iloc[0] - 50.0) < 1e-6
assert row["speed_mps"].iloc[0] > 9.9, f"ground speed {row['speed_mps'].iloc[0]}"
assert row["time_utc"].iloc[0] == "2026-11-03T13:55:20.000Z"
assert 29.5 <= tr["t"].max() <= 30.0, "track stops at path end (30 s)"

# --- gnss spoof drift ----------------------------------------------------
cfg = scenario([{"id": "s", "type": "operator", "pos": [49.365, 31.228],
                 "gnss_spoof": {"start_s": 10, "end_s": 20, "drift_mps": 8, "drift_deg": 90}}])
tr = simulate(cfg, w, np.random.default_rng(1234))
rows = tr.set_index("t")
for t, want in [(5.0, 0.0), (15.0, 40.0), (20.0, 80.0), (25.0, 0.0)]:
    r = rows.loc[t]
    dx = (r["gnss_lon"] - r["lon"]) * config.M_PER_DEG * w.cos0
    dy = (r["gnss_lat"] - r["lat"]) * config.M_PER_DEG
    assert abs(dx - want) < 8.0, f"gnss east offset at t={t}: {dx:.2f}, want {want}"
    assert abs(dy) < 8.0, f"gnss north offset at t={t}: {dy:.2f}, want 0"
assert abs(rows.loc[20.0]["gnss_alt_msl_m"] - rows.loc[20.0]["z_m"]) < 15.0

print("all foundation tests passed")
