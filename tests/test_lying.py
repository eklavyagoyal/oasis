"""Lying-sensor tests: plain asserts, run with `uv run python tests/test_lying.py`.

Synthetic 60 km world: a spoofed Mavic near the receiver, a second Mavic 30 km away behind a
ridge. Exercises remote_id + telemetry end to end on a Context, no DEM download, no pytest.
"""
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mirrorworld.__main__ import Context  # noqa: E402
from mirrorworld.config import Scenario  # noqa: E402
from mirrorworld.sensors import remote_id, telemetry  # noqa: E402
from mirrorworld.truth import simulate  # noqa: E402
from mirrorworld.world import World  # noqa: E402

M_PER_DEG = 111_195.0


def bare_world():
    """World without a DEM download: flat 100 m plain with a 250 m ridge 14.5 km north."""
    w = World.__new__(World)
    w.lat0, w.lon0 = 49.365, 31.228
    w.cos0 = float(np.cos(np.radians(w.lat0)))
    w.spacing = 30.0
    w.n = int(2 * 31000.0 / w.spacing) + 1  # 60 km area + 1 km margin, as world.__init__ builds it
    w.x0 = w.y0 = -w.spacing * (w.n - 1) / 2.0
    w.grid = np.full((w.n, w.n), 100.0, dtype=np.float32)
    ridge = slice(int((14000 - w.y0) / w.spacing), int((15000 - w.y0) / w.spacing) + 1)
    w.grid[ridge, :] = 250.0  # terrain between the receiver and the far drone
    return w


cfg = Scenario.model_validate({
    "name": "test-lying", "seed": 7, "start": "2026-11-03T13:55:00Z",
    "duration_s": 80, "truth_hz": 2, "area": {"lat": 49.365, "lon": 31.228, "size_km": 60},
    "objects": [
        {"id": "drone_1", "type": "dji_mavic3", "side": "friendly", "loop": True,
         "path": [[49.3650, 31.2200, 50], [49.3650, 31.2360, 50]],
         "gnss_spoof": {"start_s": 20, "end_s": 60, "drift_mps": 8, "drift_deg": 60}},
        {"id": "op_1", "type": "operator", "side": "friendly", "pos": [49.3645, 31.2205],
         "controls": "drone_1"},
        {"id": "far_1", "type": "dji_mavic3", "side": "hostile",
         "pos": [49.3650 + 28000 / M_PER_DEG, 31.228], "alt_agl_m": 50},
    ],
    "sensors": [
        {"id": "RID1", "type": "remote_id", "pos": [49.3650 - 2000 / M_PER_DEG, 31.228], "mast_m": 40},
        {"id": "TEL1", "type": "telemetry", "pos": [49.3650 - 2000 / M_PER_DEG, 31.228],
         "params": {"objects": ["drone_1"]}},
    ],
})
w = bare_world()
out = Path(tempfile.mkdtemp())
ctx = Context(cfg, w, None, {o.id: o for o in cfg.objects}, out)
ctx.truth = simulate(cfg, w, ctx.rng("truth"))
remote_id.run([cfg.sensors[0]], ctx)
telemetry.run([cfg.sensors[1]], ctx)

key = pd.read_csv(out / "answer_key" / "RID1.csv")
msg = pd.read_csv(out / "sensors" / "RID1" / "messages.csv")
tel = pd.read_csv(out / "sensors" / "TEL1" / "drone_1.csv")
tel_key = pd.read_csv(out / "answer_key" / "TEL1.csv")
m = msg.merge(key, on="record_id")
d1 = m[m["object_id"] == "drone_1"]

# 1. RID position error grows at the 8 m/s spoof drift, snaps back to < 10 m
innov_in = d1[d1["t"].between(25, 55)]
assert len(innov_in) > 20, f"drone_1 received {len(innov_in)}x in the spoof window"
slope = np.polyfit(innov_in["t"] - 20.0, innov_in["position_error_m"], 1)[0]
assert 7.5 <= slope <= 8.5, f"error growth {slope:.2f} m/s, want ~8"
after = d1[d1["t"] > 61]["position_error_m"]
assert len(after) > 5 and after.max() < 10, f"post-spoof error {after.max():.1f} m, want < 10"

# 2. a drone 30 km away behind the ridge is never received
assert (m["object_id"] == "far_1").sum() == 0, "far_1 must not close the Remote ID link"

# the DroneID pilot leak: reported operator position within ~10 m of the real pilot
op_err = np.hypot((d1["operator_lat"] - d1["operator_true_lat"]) * M_PER_DEG,
                  (d1["operator_lon"] - d1["operator_true_lon"]) * M_PER_DEG * w.cos0)
assert op_err.max() < 10, f"pilot leak error {op_err.max():.1f} m, want < 10"

# 3. satellites_visible flips inside the spoof window
si, so = tel[tel["t"].between(30, 50)], tel[tel["t"].between(2, 18) | tel["t"].between(62, 78)]
assert so["satellites_visible"].between(18, 22).all() and so["satellites_visible"].std() > 0.5
assert si["satellites_visible"].between(24, 26).all() and si["satellites_visible"].std() < 1.0
assert si["cn0_dbhz"].mean() > so["cn0_dbhz"].mean() + 3, "C/N0 must rise with the spoof"

# 4. EKF velocity innovation is > 3x higher inside the window
ratio = si["ekf_vel_innov"].median() / so["ekf_vel_innov"].median()
assert ratio > 3, f"innov ratio {ratio:.1f}x, want > 3x"

# answer key sanity: every telemetry record is mapped, spoofing flagged only in the key
assert set(tel["record_id"]) == set(tel_key["record_id"]), "answer key must cover every record"
in_ids = set(tel.loc[tel["t"].between(30, 50), "record_id"])
out_ids = set(tel.loc[tel["t"].between(2, 18), "record_id"])
assert tel_key.loc[tel_key["record_id"].isin(in_ids), "spoofed"].all()
assert not tel_key.loc[tel_key["record_id"].isin(out_ids), "spoofed"].any()
assert tel_key["gnss_error_m"].max() > 250, "the 8 m/s drift must show in the answer key"

print(f"all lying-sensor tests passed (slope {slope:.2f} m/s, innov {ratio:.1f}x, "
      f"{len(d1)} RID messages)")
