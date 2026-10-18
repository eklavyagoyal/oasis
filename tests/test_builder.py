"""Builder tests: plain asserts, run with `uv run python tests/test_builder.py`."""
import math
import sys
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mirrorworld import config  # noqa: E402
from mirrorworld.builder import BOX_M, Knobs, build  # noqa: E402
from mirrorworld.catalog import CATALOG  # noqa: E402
from mirrorworld.world import World  # noqa: E402


def polyline(world, obj):
    wps = np.asarray(obj.path, float)
    wx, wy = world.to_xy(wps[:, 0], wps[:, 1])
    seg = np.hypot(np.diff(wx), np.diff(wy))
    return np.concatenate([[0.0], np.cumsum(seg)]), np.stack([wx, wy], 1)


def polypoint(world, obj, t):
    """Object x, y at t along its polyline, exactly as truth.py flies it."""
    cum, pts = polyline(world, obj)
    speed = obj.speed_mps if obj.speed_mps is not None else CATALOG[obj.type]["speed_mps"]
    s = float(np.clip(speed * (t - obj.start_s), 0.0, cum[-1]))
    i = int(np.clip(np.searchsorted(cum, s, side="right") - 1, 0, len(pts) - 2))
    frac = (s - cum[i]) / (cum[i + 1] - cum[i]) if cum[i + 1] > cum[i] else 0.0
    return pts[i] + frac * (pts[i + 1] - pts[i])


# --- determinism: same knobs + seed -> byte-identical YAML -----------------
k = Knobs(seed=1, sector="ros-valley")
text1, scen = build(k)
text2, _ = build(k)
assert text1 == text2, "same knobs + seed must give byte-identical YAML"
text3, _ = build(Knobs(seed=2, sector="ros-valley"))
assert text3 != text1, "different seed must give a different scenario"

# --- validity: parses, validates, everything >= 300 m inside the area ------
d = yaml.safe_load(text1)
sc = config.Scenario.model_validate(d)
assert sc.name == "ros-valley-s1" and sc.seed == 1
for who in list(sc.objects) + list(sc.sensors):
    if getattr(who, "pos", None):
        pts = [who.pos]
    elif getattr(who, "path", None):
        pts = [(p[0], p[1]) for p in who.path]
    else:
        continue  # mounted sensor
    for lat, lon in pts:
        dx = (lon - sc.area.lon) * config.M_PER_DEG * math.cos(math.radians(sc.area.lat))
        dy = (lat - sc.area.lat) * config.M_PER_DEG
        assert abs(dx) <= BOX_M + 0.5 and abs(dy) <= BOX_M + 0.5, f"{who.id} violates the 300 m margin"

# --- drone count knob -----------------------------------------------------
hostiles = [o for o in sc.objects if o.side == "hostile" and CATALOG[o.type]["kind"] == "drone"]
assert len(hostiles) == k.drones, f"{len(hostiles)} hostile drones, knob says {k.drones}"
assert len({o.id for o in sc.objects} | {s.id for s in sc.sensors}) == len(sc.objects) + len(sc.sensors)

# --- RF sites pairwise >= 3.5 km, C2-01 last ------------------------------
w = World(sc)
rf = [s for s in sc.sensors if s.id.startswith("RF-")]
xy = [(float(w.to_xy(*s.pos)[0]), float(w.to_xy(*s.pos)[1])) for s in rf]
for i in range(len(xy)):
    for j in range(i + 1, len(xy)):
        dist = math.hypot(xy[i][0] - xy[j][0], xy[i][1] - xy[j][1])
        assert dist >= 3500.0, f"{rf[i].id}-{rf[j].id} only {dist:.0f} m apart"
assert sc.sensors[-1].id == "C2-01", "C2-01 must be the last sensor"

# --- defence=True: the rendezvous lands on the hostile's path at time T ----
kd = Knobs(seed=4, sector="ros-valley", template="incoming", defence=True, drones=4,
           mix={"shahed136": 1.0}, birds=False, wifi=False)
_, scen = build(kd)
wd = World(scen)
ints = [o for o in scen.objects if o.type == "interceptor"]
oneway = [o for o in scen.objects if o.side == "hostile"
          and o.type in ("shahed136", "gerbera", "fpv_analog", "fpv_fiber")]
assert len(ints) == min(3, len(oneway) // 2) == 2, \
    f"{len(ints)} interceptors for {len(oneway)} one-way hostiles"
for it in ints:
    t = it.end_s
    assert t is not None and it.start_s >= 0.0
    ix, iy = polypoint(wd, it, t)  # where the interceptor is at T = the rendezvous point
    best, best_obj = 1e9, None
    for h in oneway:
        hx, hy = polypoint(wd, h, t)
        dist = math.hypot(ix - hx, iy - hy)
        if dist < best:
            best, best_obj = dist, h
    assert best < 50.0, f"{it.id} rendezvous is {best:.1f} m off its hostile at t={t}"
    assert best_obj.end_s == t, f"{best_obj.id} must end at the rendezvous T={t}"
    cum, _ = polyline(wd, best_obj)  # T strictly before it reaches SITE-01 (path end)
    speed = best_obj.speed_mps
    assert t < best_obj.start_s + cum[-1] / speed, f"{best_obj.id} rendezvous is after path end"

assert all(o.end_s is None or o.end_s >= o.start_s for o in scen.objects)

print("all builder tests passed")
