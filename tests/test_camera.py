"""Camera tests: plain asserts, run with `uv run python tests/test_camera.py`."""
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mirrorworld.sensors.camera import (  # noqa: E402
    focal_px, frame_objects, horizon_profile, paint_objects, solar_position)
from mirrorworld.world import World  # noqa: E402


def bare_world(grid, spacing):
    """World without a DEM download: local frame on a synthetic grid."""
    w = World.__new__(World)
    w.lat0, w.lon0 = 49.37, 31.20
    w.cos0 = math.cos(math.radians(w.lat0))
    w.grid = np.asarray(grid, dtype=np.float32)
    w.spacing = spacing
    w.n = w.grid.shape[0]
    w.x0 = w.y0 = -spacing * (w.n - 1) / 2.0
    return w


W, H, FOV = 1280, 720, 3.0
f_px = focal_px(W, FOV)

# --- 1. projection: pixels_on_object = span / range * f_px within 5% ----
cam = np.array([0.0, 0.0, 100.0])
obj_xyz = cam + np.array([150.0, 200.0, 30.0])
true_range = float(np.linalg.norm(obj_xyz - cam))
az0 = math.degrees(math.atan2(150.0, 200.0)) % 360.0
el0 = math.degrees(math.atan2(30.0, 250.0))
objs = [{"id": "t1", "shape": "quad", "span_m": 0.5, "xyz": obj_xyz, "xyz_prev": obj_xyz}]
rows = frame_objects(bare_world(np.zeros((121, 121)), 30.0), cam, objs, az0, el0, f_px, W, H)
assert len(rows) == 1
r = rows[0]
assert abs(r["range_m"] - true_range) / true_range < 0.05, r["range_m"]
want_px = 0.5 / true_range * f_px
assert abs(r["pixels_on_object"] - want_px) / want_px < 0.05, (r["pixels_on_object"], want_px)
assert abs(r["col"] - W / 2) < 0.5 and abs(r["row"] - H / 2) < 0.5, (r["col"], r["row"])
assert r["in_frame"] and not r["occluded"]

# --- 2. object behind a ridge is occluded and not drawn ----------------
grid = np.zeros((121, 121))
grid[76:85, :] = 150.0  # ridge plateau at y = 480..720 m
ridge = bare_world(grid, 30.0)
behind = cam + np.array([0.0, 1200.0, 10.0])
objs = [{"id": "t2", "shape": "quad", "span_m": 0.5, "xyz": behind, "xyz_prev": behind}]
rows = frame_objects(ridge, cam, objs, 0.0, math.degrees(math.atan2(10.0, 1200.0)), f_px, W, H)
assert len(rows) == 1 and rows[0]["occluded"] and rows[0]["in_frame"]
img = np.zeros((H, W, 3))
paint_objects(img, rows, f_px, {}, 12.0)
assert not img.any(), "occluded object must not be drawn"
front = cam + np.array([0.0, 300.0, 50.0])
objs = [{"id": "t3", "shape": "quad", "span_m": 0.5, "xyz": front, "xyz_prev": front}]
rows = frame_objects(ridge, cam, objs, 0.0, math.degrees(math.atan2(50.0, 300.0)), f_px, W, H)
assert not rows[0]["occluded"] and rows[0]["in_frame"]
paint_objects(img, rows, f_px, {}, 12.0)
assert img.any(), "visible object must be drawn"

# --- 3. horizon elevation of a 100 m wall at 1 km ----------------------
grid = np.zeros((161, 161))
grid[:, 120:132] = 100.0  # wall from x = 1000 to 1275 m
_, hel, _ = horizon_profile(bare_world(grid, 25.0), np.array([0.0, 0.0, 0.0]))
i90, i270 = int(round(90 / 0.02)), int(round(270 / 0.02))
want = math.degrees(math.atan(100.0 / 1000.0))
assert abs(hel[i90] - want) < 0.05, (hel[i90], want)
assert hel[i270] < 0.2, hel[i270]

# --- 4. sun: elevation cross-checked against skyfield/DE421 to ~0.01 deg
# (the scenario's "~14:29" sunset note is approximate; the real 0 deg crossing is 14:23:20Z)
el, az = solar_position(datetime(2026, 11, 4, 14, 23, 20, tzinfo=timezone.utc), 49.37, 31.20)
assert abs(el) < 0.15, el
el, az = solar_position(datetime(2026, 11, 4, 14, 29, 0, tzinfo=timezone.utc), 49.37, 31.20)
assert -1.1 < el < -0.6 and 245 < az < 248, (el, az)
el, az = solar_position(datetime(2026, 6, 21, 10, 0, 0, tzinfo=timezone.utc), 49.37, 31.20)
assert el > 45.0 and 150 < az < 250, (el, az)

print("test_camera: ok")
