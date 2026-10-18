"""Radar self-check on synthetic terrain: farther = fewer plots, hills hide, a straight flight becomes one track."""
import math
import sys
import types
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mirrorworld.sensors import radar  # noqa: E402
from mirrorworld.world import World  # noqa: E402


def flat_world(ridge_m=0.0):
    w = World.__new__(World)
    w.lat0, w.lon0 = 49.365, 31.228
    w.cos0 = math.cos(math.radians(w.lat0))
    g = np.zeros((601, 601), np.float32)
    g[:, 330:333] = ridge_m  # a wall north-south, ~900 m east of the centre
    w.grid, w.spacing, w.n = g, 30.0, 601
    w.x0 = w.y0 = -w.spacing * 300
    return w


class Ctx:
    def __init__(self, world, x0, vx=0.0, alt=300.0, dur=300.0):
        self.world, self.out = world, None
        self.cfg = types.SimpleNamespace(duration_s=dur, seed=1)
        self.objects = {"d1": types.SimpleNamespace(type="shahed136", side="hostile")}
        self.x0, self.vx, self.alt = x0, vx, alt

    def rng(self, name):
        return np.random.default_rng(7)

    def iso(self, t):
        return np.asarray(t).astype(str)

    def alive(self, s, t):
        return np.ones(np.shape(t), bool)

    def state(self, oid, t):
        t = np.asarray(t, float)
        z = np.zeros_like(t)
        return {"x": self.x0 + self.vx * t, "y": z, "z": z + self.alt, "vx": z + self.vx, "vy": z, "vz": z}


SENSOR = types.SimpleNamespace(id="R", params={}, mast_m=10.0)
P = dict(radar.DEFAULTS, clutter_per_scan=0.0)
SITE = np.array([0.0, 0.0, 10.0])

near = radar._plots(SENSOR, Ctx(flat_world(), 3000.0), P, SITE, np.random.default_rng(1))[0]
far = radar._plots(SENSOR, Ctx(flat_world(), 9000.0), P, SITE, np.random.default_rng(1))[0]
assert len(near) > 2 * len(far) > 0, (len(near), len(far))  # SNR ~ 1/R^4

hidden = radar._plots(SENSOR, Ctx(flat_world(ridge_m=800.0), 3000.0), P, SITE, np.random.default_rng(1))[0]
assert len(hidden) == 0, "a target behind a ridge must never be plotted"

ctx = Ctx(flat_world(), -4000.0, vx=40.0, alt=400.0, dur=200.0)
plots, _ = radar._plots(SENSOR, ctx, P, SITE, np.random.default_rng(2))
tracks = radar._track(plots, ctx, SITE, 1.0)
conf = tracks[tracks["state"] == "CONFIRMED"]
assert conf["track_id"].nunique() >= 1 and len(conf) > 100, conf["track_id"].value_counts()
x, _ = ctx.world.to_xy(conf["lat"].to_numpy(), conf["lon"].to_numpy())
err = np.abs(x - (ctx.x0 + ctx.vx * conf["t"].to_numpy()))
assert np.median(err) < 60.0, np.median(err)
print(f"radar ok: {len(near)} plots at 3 km vs {len(far)} at 9 km, 0 behind the ridge, "
      f"track median error {np.median(err):.0f} m over {len(conf)} updates")
