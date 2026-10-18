"""LLM-lane self-check: the deterministic physics/geometry (no network, no API key).
Run with `uv run python tests/test_llm.py`."""
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mirrorworld import prompt as P  # noqa: E402
from mirrorworld.config import Area  # noqa: E402
from mirrorworld.sensors import reports  # noqa: E402
from mirrorworld.world import World  # noqa: E402


def bare_world(grid, spacing):
    """World without a DEM download: local frame on a synthetic grid."""
    w = World.__new__(World)
    w.lat0, w.lon0 = 49.37, 31.20
    w.cos0 = math.cos(math.radians(w.lat0))
    w.grid = np.asarray(grid, dtype=np.float32)
    w.spacing = float(spacing)
    w.n = w.grid.shape[0]
    w.x0 = w.y0 = -w.spacing * (w.n - 1) / 2.0
    w.sources = ["synthetic"]
    return w


AREA = Area(lat=49.37, lon=31.20, size_km=16)
HALF = AREA.size_km * 500.0

# --- sun position vs the researched sunset/civil-dusk times (docs/research/geo-data.md) ---
ts = lambda s: datetime(2026, 11, 3, tzinfo=timezone.utc).timestamp() + s  # noqa: E731
elev = reports.sun_elevation_deg
at_sunset = float(elev(ts(14 * 3600 + 30 * 60 + 35), 49.3754, 31.1882))  # 14:30:35Z
at_civil = float(elev(ts(15 * 3600 + 4 * 60 + 14), 49.3754, 31.1882))    # 15:04:14Z
assert -2.5 < at_sunset < 0.5, f"sun elevation at researched sunset: {at_sunset:.2f} deg"
assert -7.0 < at_civil < -5.0, f"sun elevation at researched civil-dusk end: {at_civil:.2f} deg"

# --- perception: seen at 300 m in LOS at dusk; behind a wall: not seen, 15 dB quieter ---
flat = bare_world(np.zeros((201, 201)), 100.0)
grid = np.zeros((201, 201))
grid[:, 96:105] = 100.0  # a 100 m wall across the middle
wall = bare_world(grid, 100.0)
person = np.array([-400.0, 0.0, 1.7])
obj = np.array([400.0, 0.0, 30.0])
los_flat, los_wall = bool(flat.los(person, obj)), bool(wall.los(person, obj))
assert los_flat and not los_wall, "flat ground has LOS, the wall blocks it"

r_wall = float(np.hypot(*(obj - person)[:2]))
quiet = reports.hear_level_db(110.0, r_wall, los_wall) - reports.hear_level_db(110.0, r_wall, los_flat)
assert abs(quiet + reports.LOS_PENALTY_DB) < 1e-9, f"terrain screening delta {quiet}"
assert reports.can_hear(110.0, r_wall, los_flat) and not reports.can_hear(110.0, r_wall, los_wall), \
    "the same object must be heard in the open and inaudible behind the wall"

r_seen = 300.0
sun_dusk = reports.sun_elevation_deg(ts(14 * 3600 + 20 * 60), 49.37, 31.20)  # ~civil dusk
assert float(sun_dusk) > reports.CIVIL_DUSK_DEG
assert bool(reports.can_see(los_flat, 0.35, r_seen, float(sun_dusk))), "300 m quad in LOS at dusk must be seen"
assert not bool(reports.can_see(los_wall, 0.35, r_seen, float(sun_dusk))), "behind the wall: not seen"
assert not bool(reports.can_see(los_flat, 0.35, r_seen, -8.0)), "after dark: not seen"
assert not bool(reports.can_see(los_flat, 0.35, 5000.0, float(sun_dusk))), "5 km quad is < 1 arcmin: not seen"

# --- episode detection: >= 15 s continuous, short gaps merged, sub-threshold ignored ---
per = np.zeros(60, dtype=bool)
per[10:40] = True                      # 30 s episode
per[50:55] = True                      # 5 s blip
assert reports.episodes(per) == [(10, 39)], reports.episodes(per)
per2 = np.zeros(60, dtype=bool)
per2[5:12] = per2[13:21] = True        # 7 s + 8 s with a 1 s dropout -> one 16 s episode
assert reports.episodes(per2) == [(5, 20)], reports.episodes(per2)

# --- behaviour paths stay inside the area ---
for behaviour, target in [("patrol", None), ("transit", None), ("loiter", None),
                          ("attack_sensor", (3000.0, 2000.0)), ("static", None)]:
    for x, y in [(0.0, 0.0), (7000.0, -7000.0), (-6500.0, 6800.0)]:
        wps, loop, attack = P.behaviour_path(behaviour, x, y, AREA.size_km / 2.0, 80.0, target=target)
        assert len(wps) >= (2 if behaviour != "static" else 1), behaviour
        for wx, wy, _ in wps:
            assert abs(wx) <= HALF and abs(wy) <= HALF, f"{behaviour} waypoint ({wx}, {wy}) leaves the area"
        if behaviour == "attack_sensor":
            assert attack and math.hypot(wps[1][0] - target[0], wps[1][1] - target[1]) < 1.0
        if behaviour in ("patrol", "loiter"):
            assert loop

# --- auto-siting: >= 2 sites >= 4 km apart, on the high ground ---
grid = np.full((201, 201), 100.0)
for cx, cy in [(4500.0, 4500.0), (-4500.0, -4500.0)]:
    yy, xx = np.mgrid[-10000:10000:201j, -10000:10000:201j]
    grid += 300.0 * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * 1500.0 ** 2))
world = bare_world(grid, 100.0)
sites = P.auto_sites(world, AREA, n_sites=2)
assert len(sites) >= 2, f"auto-siting returned {len(sites)} sites"
for i in range(len(sites)):
    for j in range(i + 1, len(sites)):
        d = float(np.hypot(*(sites[i] - sites[j])))
        assert d >= P.RF_MIN_SEP_M - 1e-6, f"sites {i},{j} only {d:.0f} m apart"

# --- template reports verbalise the structured facts, and only them ---
fact = {
    "record_id": "HUM1-000000", "reporter_type": "eppo", "obs_time_utc": "2026-11-04T14:02:10.000Z",
    "perceived": "hear", "est_type": "шахед (звук мопеда)", "est_type_en": "shahed (moped sound)",
    "count": 2, "direction_deg": 178.0, "est_distance_m": 2450.0, "est_alt_m": None,
}
uk, en = reports._render_template(fact)
assert "шахед" in uk and "2.5" in uk and "×2" in uk, uk
assert "shahed" in en and "2.5" in en and "×2" in en, en
assert "з півдня" in uk and "the south" in en, (uk, en)
fact_obs = dict(fact, reporter_type="observer", perceived="both", est_alt_m=120.0)
uk, en = reports._render_template(fact_obs)
for text in (uk, en):
    assert "SALUTE" in text and fact_obs["obs_time_utc"] in text, text

# --- LLM text enforcement: templates keep the facts, drifted prose is rejected ---
fact_obs = dict(fact, reporter_type="observer", perceived="both", est_alt_m=120.0)
uk_obs, en_obs = reports._render_template(fact_obs)
for text in (uk_obs, en_obs):
    assert "SALUTE" in text and fact_obs["obs_time_utc"] in text, text
assert reports.check_fact_text(fact, *reports._render_template(fact))[0], "civilian template must pass"
assert reports.check_fact_text(fact_obs, uk_obs, en_obs)[0], "observer template must pass"
drift_uk = "Чую шахед, летить з півдня на північ, низько."  # wrong cue, no numbers
assert not reports.check_fact_text(fact_obs, drift_uk, "I hear a shahed flying south to north, low.")[0]
wrong_cue = "Бачу шахед (звук мопеда), азимут 178, десь 2,4 км."
assert not reports.check_fact_text(fact, wrong_cue, "Seeing shahed at 178 deg, 2.4 km out.")[0], \
    "see-cue text for a hear-only fact must be rejected"
good_uk = "Чую шахед (звук мопеда) ×2, з півдня, десь 2,4 км."
good_en = "Hearing shahed (moped sound) x2, from the south, about 2.4 km out."
assert reports.check_fact_text(fact, good_uk, good_en)[0], "grounded prose must pass"
# "Бачу" contains "чу" as a substring: the cue check must not false-positive on the right cue
see_uk = "Бачу шахед (звук мопеда), з півдня, десь 2,4 км."
see_en = "I see a shahed (moped sound), from the south, about 2.4 km out."
assert reports.check_fact_text(dict(fact, perceived="see"), see_uk, see_en)[0], \
    "a see-cue text for a see fact must pass"
assert not reports.check_fact_text(dict(fact_obs, est_alt_m=None), see_uk, see_en)[0], \
    "observer reports must be SALUTE"

print("all LLM-lane tests passed")
