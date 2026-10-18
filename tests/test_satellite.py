"""satellite self-check: plain asserts, run with `uv run python tests/test_satellite.py`."""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mirrorworld.sensors import satellite as sat  # noqa: E402

GS = 10.0  # m/px, the Sentinel-2 GSD

# --- 1. band-delay displacement: a 50 m/s mover smears 50*1.005/10 = 5 px B02 -> B04 ---------
def state(obj, t):  # constant-velocity truth, as Context.state would give
    return {"x": 50.0 * t, "y": 0.0, "z": 0.0, "vx": 50.0, "vy": 0.0, "vz": 0.0}

pos = sat.band_positions(state, "mover", 100.0)
d_px = abs(pos["B04"]["x"] - pos["B02"]["x"]) / GS
assert abs(d_px - 5.0) <= 0.5, f"B02->B04 smear {d_px:.2f} px, want 5 +- 0.5"
assert abs(abs(pos["B03"]["x"] - pos["B02"]["x"]) / GS - 50 * 0.527 / GS) < 1e-9
assert pos["B08"]["x"] < pos["B03"]["x"] < pos["B04"]["x"], "push-broom order B02 B08 B03 B04"
assert pos["B02"]["x"] == 50.0 * 100.0, "B02 has no acquisition delay"

# --- 2. parallax: a 1,200 m target at 10 deg zenith appears 211 m from its ground point ------
assert abs(sat.parallax_offset_m(1200.0, 10.0) - 211.0) <= 1.0
assert sat.parallax_offset_m(1200.0, 0.0) == 0.0
# displaced away from the satellite: satellite due east (az 90) -> target appears to the west
de, dn = sat.parallax_ground_offset_m(1200.0, 10.0, 90.0)
assert de < 0 and abs(dn) < 1e-6, "parallax must point away from the satellite azimuth"

# --- 3. shadow: offset = h/tan(sun_elev), thrown along the anti-sun azimuth ------------------
for el in (15.0, 24.8, 60.0):
    assert abs(sat.shadow_offset_m(1200.0, el) - 1200.0 / math.tan(math.radians(el))) < 1e-9
assert abs(sat.shadow_offset_m(1200.0, 45.0) - 1200.0) < 1e-9
de, dn = sat.anti_sun_offset_m(1200.0, 45.0, 90.0)  # sun due east -> shadow to the west
assert abs(math.hypot(de, dn) - 1200.0) < 1e-6 and de < 0 and abs(dn) < 1e-6

# --- 4. sub-pixel coverage + mixing: footprint area is recovered from the coverage map -------
cov, (r0, r1, c0, c1) = sat.sprite_coverage("delta", 2.5, 0.0, 20.0, 20.0, 40, GS)
area = cov.sum() * GS * GS
assert abs(area - 2.5 * 3.5 / 2) / (2.5 * 3.5 / 2) < 0.15, f"delta area {area:.2f} m2, want 4.38"
band = np.full((40, 40), 0.20)
sat.stamp_object(band, cov, (r0, r1, c0, c1), 0.08)
assert band.min() >= 0.08 - 1e-12 and band.max() <= 0.20 + 1e-12
assert abs(band.mean() - (0.20 - cov.sum() * (0.20 - 0.08) / band.size)) < 1e-12, "mixing rule"
sat.stamp_shadow(band, cov, (r0, r1, c0, c1))
mixed = 0.20 * (1 - cov) + 0.08 * cov  # object-mixed ground, per covered fraction
want = mixed * (1 - 0.5 * cov)  # then shadowed: ground keeps 50% over the covered fraction
assert abs(band[r0:r1, c0:c1].mean() - want.mean()) < 1e-12, "shadow darkens 50% of the cover"
assert abs(band.mean() - (0.20 * (band.size - cov.size) + want.sum()) / band.size) < 1e-12

print("all satellite tests passed")
