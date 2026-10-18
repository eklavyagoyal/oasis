"""Dashboard export self-check: plain asserts, run with `uv run python tests/test_dashboard.py`.
Needs a generated run at out/ros-valley (uv run python -m mirrorworld run scenarios/ros-valley.yaml --skip-missing).
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mirrorworld.config import M_PER_DEG  # noqa: E402
from mirrorworld.dashboard import build  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "out" / "ros-valley"
mw = build(OUT)

# --- schema keys ---------------------------------------------------------
for key in ("scenario", "terrain", "objects", "sensors", "classes", "links", "labels",
            "rf", "fixes", "shadow", "events", "media", "audit"):
    assert key in mw, f"missing top-level key {key!r}"
for key in ("name", "start", "duration_s", "area", "weather"):
    assert key in mw["scenario"], f"missing scenario.{key}"
for key in ("west", "south", "east", "north", "nx", "ny", "h"):
    assert key in mw["terrain"], f"missing terrain.{key}"
assert mw["labels"] == ["target", "friendly", "clutter", "false_alarm"]
assert mw["scenario"]["start"].endswith("Z")

# --- parallel arrays -----------------------------------------------------
for o in mw["objects"]:
    n = len(o["t"])
    assert n > 0, f"{o['id']} has no samples"
    assert len(o["lat"]) == len(o["lon"]) == len(o["alt"]) == n, f"{o['id']} arrays"
for sid, r in mw["rf"].items():
    n = len(r["t"])
    for key in ("brg", "std", "snr", "pwr", "cls", "obj", "link", "los", "label"):
        assert len(r[key]) == n, f"rf[{sid}].{key} length != t"
f = mw["fixes"]
n = len(f["t"])
for key in ("lat", "lon", "smaj", "smin", "orient", "ce", "cep50", "cls", "obj", "err"):
    assert len(f[key]) == n, f"fixes.{key} length != t"
assert all(0 <= c < len(mw["classes"]) for r in mw["rf"].values() for c in r["cls"])
assert all(o == -1 or 0 <= o < len(mw["objects"]) for r in mw["rf"].values() for o in r["obj"])

# --- terrain -------------------------------------------------------------
t = mw["terrain"]
assert t["nx"] == t["ny"] == 241
assert len(t["h"]) == t["nx"] * t["ny"], "terrain heights = nx*ny"
assert t["west"] < t["east"] and t["south"] < t["north"]
for sid, sh in mw["shadow"].items():
    assert sh["nx"] == sh["ny"] == 121
    assert len(sh["agl"]) == sh["nx"] * sh["ny"], f"shadow[{sid}] = nx*ny"
    assert all(0 <= v <= 3000 for v in sh["agl"])

# --- mavic_1 at the brief's truth point (t=18427) ------------------------
mavic = next(o for o in mw["objects"] if o["id"] == "mavic_1")
i = min(range(len(mavic["t"])), key=lambda k: abs(mavic["t"][k] - 18427))
assert abs(mavic["t"][i] - 18427) < 0.51, f"no ~1 Hz sample near t=18427 (got {mavic['t'][i]})"
dx = (mavic["lon"][i] - 31.1882) * M_PER_DEG * math.cos(math.radians(49.37))
dy = (mavic["lat"][i] - 49.3754) * M_PER_DEG
assert math.hypot(dx, dy) < 20, f"mavic_1 at t=18427 is {math.hypot(dx, dy):.1f} m off the truth point"

# --- events --------------------------------------------------------------
labels = [e["label"] for e in mw["events"]]
assert "mavic_1 hidden from RF2 by terrain" in labels, "missing mavic_1/RF2 terrain occlusion"
assert "RF2 destroyed by fpv_1" in labels
assert "mavic_1 airborne" in labels and "mavic_1 ends" in labels
assert "jammer_1 on" in labels and "jammer_1 off" in labels
assert [e["t"] for e in mw["events"]] == sorted(e["t"] for e in mw["events"]), "events not sorted"

print("all dashboard tests passed")
