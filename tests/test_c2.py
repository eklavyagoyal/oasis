"""c2 self-check: plain asserts, run with `uv run python tests/test_c2.py`."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mirrorworld.sensors import c2  # noqa: E402

# --- grid: the south-west corner cell is A1 --------------------------------
assert c2.grid_label(-8000.0, -8000.0, 16.0) == "A1"
assert c2.grid_label(-7999.0, -7999.0, 16.0) == "A1"
assert c2.grid_label(0.0, 0.0, 16.0) == "I9"
assert c2.grid_label(7999.0, 7999.0, 16.0) == "P16"

# --- a line approaching a site: NEW -> APPROACHING -> CLOSE in that order ---
site = [("SITE-01", 0.0, 0.0)]
obs = [c2.Obs(t=10.0 * i, x=0.0, y=4000.0 - 180.0 * i, cls="OcuSync video", source="rf_fix")
       for i in range(23)]  # 4 km out, closing at 18 m/s down to and past the site
rows, alerts, tracks = c2.track(obs, site, 16.0, 200.0)
kinds = [a["kind"] for a in alerts]
assert kinds[0] == "NEW TRACK" and kinds.count("NEW TRACK") == 1
i_app, i_close = kinds.index("APPROACHING"), kinds.index("CLOSE")
assert 0 < i_app < i_close, kinds
assert kinds.count("APPROACHING") == 1 and kinds.count("CLOSE") == 1
assert alerts[i_app]["message"].startswith("APPROACHING SITE-01")
assert alerts[i_close]["message"].startswith("CLOSE TO SITE-01")
assert alerts[i_close]["level"] == "critical"
assert tracks[0].state == "CONFIRMED" and tracks[0].n == 23

# --- a 90 s gap loses contact 60 s after the last update --------------------
obs = [c2.Obs(t=float(i), x=100.0 * i, y=5000.0, cls="Radar track", source="radar")
       for i in range(3)]
obs += [c2.Obs(t=float(92 + i), x=100.0 * i, y=5000.0, cls="Radar track", source="radar")
        for i in range(2)]  # reappears 90 s later: too late for the 20 s gate -> new track
rows, alerts, tracks = c2.track(obs, [], 16.0, 400.0)
lost = [a for a in alerts if a["kind"] == "LOST CONTACT"]
assert len(lost) == 1 and abs(lost[0]["t"] - 62.0) < 1e-9, lost  # last update t=2 + 60 s
assert lost[0]["level"] == "warn"
assert [a["kind"] for a in alerts].count("NEW TRACK") == 2  # the gap > 20 s starts a new track
assert any(r["state"] == "LOST" for r in rows)
assert any(r["state"] == "DROPPED" and abs(r["t"] - 302.0) < 1e-9 for r in rows)

# --- a sensor that stops reporting goes SENSOR SILENT -----------------------
streams = {"RF1": np.arange(0.0, 200.0, 1.0), "RF2": np.arange(0.0, 100.0, 1.0)}
grids = {"RF1": (0.0, 0.0), "RF2": (1000.0, 0.0)}
alerts = c2.silent(streams, grids, 16.0, 200.0)
assert len(alerts) == 1, alerts
assert alerts[0]["kind"] == "SENSOR SILENT" and "RF2" in alerts[0]["message"]
assert abs(alerts[0]["t"] - 159.0) < 1e-9  # RF2's last detection is t=99
assert alerts[0]["level"] == "warn"

# --- answer-key attribution: majority, '' if none, 'mixed' on a tie ---------
assert c2.vote([]) == ("", "false_alarm")
assert c2.vote([("mavic_1", "target"), ("mavic_1", "target"), ("", "false_alarm")]) == ("mavic_1", "target")
assert c2.vote([("a", "target"), ("b", "clutter")]) == ("mixed", "mixed")

print("all c2 tests passed")
