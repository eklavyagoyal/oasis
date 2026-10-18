# Mirror World: team contract (read first)

There's one world state on one clock, observed by many sensors. Every sensor output depends only on the truth, the real terrain, the weather and the seed.
Sensor files never contain truth. The **answer key** maps every record back to the object that produced it.
No hidden failures: network calls get timeouts and bounded retries, and errors are raised with context. Never fall back silently to flat terrain or made-up data. Any degraded mode must be explicit and recorded in `run.json`.

Timeline (CEST): 12:20 contract on main · 12:45 foundation (world/truth/CLI) on main · 13:30 RF engine on main · **15:00 feature freeze** · 15:00–15:40 integration, audit, deck · 15:50 repo public · 16:00 hand-in.
Git: work on `main`, edit only your own lane's files, commit small and often, `git pull --rebase` before every push. If you need a contract change, ask in chat. Don't edit someone else's file.

## Run
    uv sync
    uv run python -m mirrorworld run scenarios/ros-valley.yaml                 # -> out/ros-valley/
    uv run python -m mirrorworld run scenarios/ros-valley.yaml --skip-missing  # while lanes are unfinished
    uv run python -m mirrorworld audit out/ros-valley                          # lane B
    uv run python -m mirrorworld view out/ros-valley                           # lane B
    uv run python -m mirrorworld prompt "..." -o scenarios/new.yaml            # lane D

## Conventions
- **Time**: `t` is float seconds since `start`. Files carry `time_utc`, ISO 8601 with milliseconds and a `Z` (`2026-11-03T14:02:07.250Z`), formatted by `ctx.iso(t)`.
- **Position**: WGS84 `lat`, `lon`. Heights are `alt_msl_m` (DEM datum) and `alt_agl_m`. CoT `hae` = `alt_msl_m` (geoid offset ignored).
- **Local frame**: `x_m` east and `y_m` north of the area centre (equirectangular, `config.M_PER_DEG`). Convert with `ctx.world.to_xy(lat, lon)` and `ctx.world.to_ll(x, y)`.
- **Angles**: bearing/azimuth in degrees true, clockwise from north, [0, 360). Elevation in degrees above horizontal.
- **Units**: m, s, m/s, MHz, dBm, dB.
- **Randomness**: always `ctx.rng("name")`, seeded from the scenario seed plus the name. Your lane can't shift anyone else's numbers.
- **Record ids**: `<sensor_id>-<n:06d>`, unique within the scenario.
- **Dead sensors**: drop records where `ctx.alive(sensor, t)` is False (see `destroyed_by`).

## Output: `out/<name>/`
| path | content |
|---|---|
| `scenario.yaml` | resolved input |
| `run.json` | seed, timings, data sources (DEM URLs, TLE epoch, S2 scene id), skipped sensors, degraded modes |
| `truth/objects.csv` | `id,type,kind,side,controls` |
| `truth/tracks.csv` | `t,time_utc,object_id,lat,lon,alt_msl_m,alt_agl_m,x_m,y_m,z_m,vx,vy,vz,speed_mps,heading_deg,gnss_lat,gnss_lon,gnss_alt_msl_m` |
| `sensors/<id>/...` | **only** what that sensor recorded (no truth columns) |
| `answer_key/<id>.csv` | `record_id,object_id,link,label` + that sensor's truth columns (true bearing, range, LOS, ...) |
| `fused/fixes.csv`, `fused/fixes.cot.xml` | positions from crossed bearings, computed from sensor data only |
| `viewer.html`, `scenario.kml` | replay |

- `label` is one of `target` (hostile), `friendly`, `clutter` (neutral: Wi-Fi, geese, farmer), or `false_alarm` (empty `object_id`).
- `gnss_*` is what the object's own GNSS believes: truth plus about 1.5 m noise, or the spoofed position. Telemetry and Remote ID read `gnss_*`, never `lat`/`lon`.

## Sensor module interface
```python
# mirrorworld/sensors/<type>.py, where <type> is the sensor `type:` in the YAML
def run(sensors: list[Sensor], ctx: Context) -> None:
    """Receives ALL sensors of this type at once. Writes ctx.out/'sensors'/<id>/... and ctx.out/'answer_key'/<id>.csv."""
```
Run order: `rf_df` first (camera reads `fused/fixes.csv`), then the remaining types in config order.

`Context` (`mirrorworld/__main__.py`):
- `cfg`: Scenario
- `world`: World
- `truth`: DataFrame of tracks.csv
- `objects`: {id: Obj}
- `out`: Path
- `rng(name)` → np.random.Generator
- `iso(t)` → str
- `state(object_id, t)` → dict of arrays `x, y, z, vx, vy, vz` at any `t` (NaN when inactive)
- `sensor_xyz(sensor)` → antenna position, resolving `mount`, z = ground + `mast_m`
- `alive(sensor, t)` → bool array

`World` (`mirrorworld/world.py`):
- `to_xy`, `to_ll`
- `height(x, y)`
- `profile(xa, ya, xb, yb, n)` → heights `(..., n)`
- `los(a_xyz, b_xyz)` → bool, with Earth curvature (k = 4/3)

Shared physics: `rf_df.path_loss_db(world, tx_xyz, rx_xyz, f_mhz)` (free space + terrain diffraction). Use it for anything radio (e.g. Remote ID).
Platform numbers (size, speed, links, sound) live in `mirrorworld/catalog.py`. Tune them there.

## Lanes
**A: core + RF.** Owner: Eklavya + Claude.
- Files: `pyproject.toml`, `mirrorworld/{__main__,config,catalog,world,truth}.py`, `mirrorworld/sensors/rf_df.py`, `scenarios/`.
- Physics: per link, per receiver, per tick: real DEM profile → free space + ITU-R P.526 Bullington diffraction + location-correlated shadowing + Rician/Rayleigh fading. Noise floor (kTB + NF + man-made) plus co-channel interference (Wi-Fi, jammer). DF bearing error grows as 1/√SNR, plus a site calibration bias and NLOS wild bearings. Uplinks are DF'd at the operator. Least-squares crossed-bearing fixes with CEP → CoT.
- Done when the hero run writes truth, RF CSV/CoT, fixes and answer key, and RF2 loses `mavic_1` behind the ridge.

**B: prove it + show it.** Files: `mirrorworld/audit.py`, `mirrorworld/viewer.py`, `baselines/oneshot/`.
- **Audit** reads `sensors/` and `fused/` (the data), then `truth/` and `answer_key/` (for scoring). Its checks must be **independent of our propagation model**:
  1. bearing residual vs true geometry (mean ≈ calib bias, spread matches reported `bearing_std_deg`)
  2. DEM line-of-sight vs power: NLOS records show excess loss over free space
  3. RF detection gaps line up with terrain occlusion intervals
  4. fix error vs reported `ce`: about 50% inside if `ce` = CEP
  5. timing: every timestamp is inside the scenario window, camera/RF times agree, acoustic delay = range / 343 m/s
  6. provenance: every record has exactly one answer-key row, and no truth columns appear under `sensors/`
  - Output: `audit.md` + `audit.json` with PASS/FAIL and numbers.
- **One-shot baseline**: ask an LLM *once* for the same scenario in our file layout (keep the prompt in `baselines/oneshot/PROMPT.md`), then run the audit on it. The side-by-side table is the pitch slide.
- **Viewer**: a single self-contained HTML file (Leaflet from CDN, data inline):
  - imagery basemap, truth trails, sensors
  - bearing lines flashing at their timestamps, fixes with `ce` circles
  - time slider and play
  - panels showing the current camera frame, audio and satellite image
  - also writes `scenario.kml` (gx:Track) for Google Earth
- Start now on a small hand-made `out/` fixture. Switch to the real output when lane A lands.

**C: real sky.** Files: `mirrorworld/sensors/{camera,satellite}.py`.
- **Camera**: pinhole PTZ on a mast.
  - **Cue from the newest RF fix**, not the truth (`params.cue: rf`, assume 100 m AGL for elevation), so the target sits off-centre by the real DF error or misses the frame.
  - Frame:
    - sky colour from the real sun elevation
    - **horizon silhouette ray-marched from the DEM**
    - target at true angular size (`span_m / range × f_px`), contrast fading with range (Koschmieder, `weather.visibility_km`)
    - noise, then JPEG
    - burn-in label `EO1 2026-11-03 14:02:07.25Z FOV 3.0°`
  - Detector confidence is a function of pixels on target and contrast → `sensors/EO1/detections.csv`.
  - Answer key: true bbox, range, pixels on target, `in_frame`.
- **Satellite**:
  - Find the real pass from TLEs (skyfield + CelesTrak) and use a real Sentinel-2 L2A background (Earth Search STAC COGs).
  - Insert objects sub-pixel along with their sun-cast shadow. Sample each band at its own acquisition time, so moving objects smear into colour fringes.
  - **If there's no pass in the window, write nothing and note it in `run.json`, including the nearest pass times.** We'll add a morning act around a real pass.

**D: real sound + lying sensors + humans + prompt.** Files: `mirrorworld/sensors/{microphone,remote_id,telemetry,reports}.py`, `mirrorworld/prompt.py`.
- **Microphone**: per-mic WAV at 16 kHz.
  - Harmonics of the catalog `f0_hz` at **emission time τ = t − r/c**, which gives Doppler for free.
  - Attenuation: 1/r spreading, ISO 9613-1 absorption, terrain screening (`world.los` → Maekawa), up/down-wind.
  - Rural ambient noise, BWF time reference. Only write audio around activity (files ≤ 10 min).
  - Detections CSV uses *arrival* times.
- **remote_id**: objects whose `remote_id` resolves true broadcast a 1 Hz ASTM F3411-style JSON message (serial, `gnss_*` position so spoofing shows, speed, operator position). A message is received only when `path_loss_db` closes the BLE/Wi-Fi link.
- **telemetry**: our own (friendly) drones' logs, 5 Hz MAVLink-like CSV built from `gnss_*`. Spoofing shows up as drift and jumps.
- **reports**:
  - Observers and ePPO-style civilians report only what they could actually hear (acoustic level) or see (LOS + angular size).
  - 1–4 min delay, human error on direction, distance and type.
  - Text comes from OpenAI given the structured facts (`OPENAI_API_KEY`), in Ukrainian + English. Without a key, use a template and record `text_source=template`.
- **prompt**: OpenAI → Scenario JSON (pydantic schema) → validate → retry once with the error → YAML.
  - Resolve place names via Nominatim.
  - Never let the LLM invent numbers we can compute. Sensor sites come from DEM high points.
