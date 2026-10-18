# OASIS

**Synthetic aerial defence scenarios over real Ukrainian terrain.** OASIS writes one true world (where every drone, pilot, decoy and response asset really was, second by second) and then simulates what each sensor would physically have recorded. You get the sensor files *and* an answer key that traces every record back to the object that caused it, and why.

> Defence AI needs data where the answer is known. Real recordings are scarce, sensitive and unlabelled, and they never contain the edge cases (jamming, spoofing, fibre-optic drones, decoys). OASIS makes that data, and proves it is physically consistent.

![The same 2.5 m delta-wing drone through the OASIS camera model at 400 m and 2,140 m](docs/media/drone_near_far.png)
*The camera model draws a Blender-rendered airframe at its true angular size and viewing angle: 32 px across at 400 m, about 6 px at 2,140 m.*

## Why it beats asking an LLM for a dataset
Same 10-minute window, same scenario file, same file layout, same 10 independent checks. The baseline is one call to a strong general model that was given the full scenario and asked for physically realistic data (`baselines/oneshot/`).

| | **OASIS** | **One-shot LLM** |
|---|---|---|
| Records in the window | 2,716 | 40 |
| Timestamps | consistent to 0.5 ms | run backwards |
| Bearings vs true geometry | 95% within 2σ; recovers the hidden mast calibration offsets (+0.8°/−0.6°) | biased +29°/−49° |
| Reported fix uncertainty | honest: 52% of fixes inside CEP50 | "too good": 8 m errors with a 50 m CEP, 100% inside |
| Terrain occlusion | receivers go silent while a ridge blocks the path | the drone never goes behind terrain |
| Distance law | fitted path-loss exponent 1.9 at RF1 and 4.2 at RF2 (inside the physical 1.5–4.5 band) | too little data to test |
| **Audit** | **7 pass · 0 fail** | **1 pass · 3 fail** |

The auditor (`python -m mirrorworld audit`) never uses OASIS's own propagation model. It works from geometry, the DEM line of sight, causality and statistics, so the comparison isn't circular.

## Quickstart
```sh
uv sync
uv run python -m mirrorworld run scenarios/ros-valley.yaml --skip-missing   # hero day → out/ros-valley/
uv run python -m mirrorworld audit out/ros-valley                           # physics checks → audit.md / audit.json
uv run python -m mirrorworld dash out/ros-valley --serve                    # 3D replay at localhost:8765/dashboard/
```
**Other ways to make a scenario:**
```sh
uv run python -m mirrorworld.builder --sector random --template intercepted --drones 12 --seed 4 --run
uv run python generate_scenario.py --preset lost_contact --sector kharkiv_ne --seed 1     # asset-catalog presets
uv run python generate_scenario.py --matrix --seed 1                                     # every preset × sector, audited
uv run python -m mirrorworld prompt "two Mavics scouting a dam at dusk, a fibre-optic FPV up the river" -o scenarios/new.yaml --run
```
Prompt mode needs `OPENAI_API_KEY` in `.env`. The LLM only fills scenario intent. Coordinates, sensor sites, flight paths and times of day are computed from terrain and the sun.

## What a run produces (`out/<name>/`)
| path | what |
|---|---|
| `truth/tracks.csv` | every object's position and velocity on one UTC clock, plus what its own GNSS *believed* (spoofing lives here) |
| `sensors/<id>/` | only what that sensor recorded, with no truth columns |
| `answer_key/<id>.csv` | for each record: the object that produced it, its role, and the physics behind it (line of sight, diffraction loss, SNR, …) |
| `fused/fixes.csv`, `fixes.cot.xml` | crossed-bearing positions computed from sensor data alone, as TAK Cursor-on-Target |
| `audit.json` / `audit.md` | the independent checks |

**Sensors (one module each in `mirrorworld/sensors/`):**
| Sensor | What it records |
|---|---|
| `rf_df` | Direction-finding receivers on real radio masts. Terrain diffraction is ITU-R P.526-16 delta-Bullington over the Copernicus 30 m DEM (validated against the reference implementation), with correlated shadowing, Rician fading, co-channel interference and barrage jamming. Bearing error grows with SNR and with terrain-blocked paths. **Controller uplinks are separate transmitters, so crossed bearings locate the pilot.** Outputs are CSV and TAK lines of bearing. |
| `rf_iq` | Raw 2.4 GHz IQ snapshots (SigMF) with every burst at its physical power. Per-burst labels are in the answer key. |
| `radar` | X-band plots with terrain masking, Swerling-1 fluctuation, birds vs drones confusion, clutter, and an alpha-beta tracker with gaps |
| `camera` | Pan-tilt camera cued by RF fixes or radar tracks. The scene uses the real sun position, a horizon ray-marched from the DEM, and **3D drone models rendered in Blender** (`tools/render_sprites.py`), drawn at true pixel size and viewing angle, then hazed, blurred, noised and JPEG-compressed. Includes simulated detector output. |
| `satellite` | The real Sentinel-2 pass computed from orbit data, over a real Sentinel-2 L2A background. Movers are inserted at true size with per-band timing smear and a sun-cast shadow. |
| `microphone` | Per-microphone WAVs with speed-of-sound delay, Doppler, ISO 9613-1 absorption, terrain screening and wind, plus a CFAR tone detector. In the hero day the radio-silent fibre-optic FPV is recorded by no sensor at all, and the log book says so. |
| `remote_id` | DroneID-style broadcasts that leak the pilot's position and carry the drone's *believed* (spoofable) GNSS |
| `telemetry` | Our own drone's log, which drifts under GNSS spoofing |
| `reports` | Civilian (ePPO-style) and observer reports in Ukrainian and English, generated only when that person could physically see or hear the object |
| `c2` | Command-post alerts (new track, approaching site, lost contact, sensor silent), response-asset status and protected-site status, all derived from sensor data only |

## Scenarios
- **Hero** (`scenarios/ros-valley.yaml`, area centre 49.3700° N · 31.2000° E): a two-act day on 4 Nov 2026.
  - **Morning:** a Sentinel-2A pass catches a Shahed.
  - **Dusk:** a hostile Mavic at the challenge brief's example point at 14:02:07Z, then a leg routed through a receiver's terrain shadow; pilot geolocation; a 2.4 GHz jammer; a fibre-optic FPV; GNSS spoofing; a protected site; and an FPV that destroys a receiver mast.
- **Seed engine** (`mirrorworld/builder.py`): knobs + a seed → a validated scenario.
  - **The built world is fixed per sector.** The protected site, the air-defence positions, the receiver masts (sited on the DEM for coverage) with their calibration offsets, and the microphones come from the sector alone. They are identical for every seed (`tests/test_builder.py` checks it).
  - **The seed drives only what moves:** drone types, entry sides, corridors, altitudes, timing, interceptor rendezvous, birds, the jammer window and the weather.
  - **Templates:** *incoming*, *intercepted* (interceptors launched from the AD team to exact rendezvous points), *lost-contact* (a leg hidden in a receiver's terrain shadow plus a fibre-optic FPV), *saturation* (one-way drones in 2–3 tight waves from one side) and *recon-strike* (a recon UAV orbits the AD battery and a loitering munition follows it in).
  - Times of day come from the sun.
  - Sweep: `python -m mirrorworld.builder --template saturation --seeds 1-4 --run` builds, simulates and audits one scenario per seed.
- **Log book** (`python -m mirrorworld.logbook out/<name>`): one time-ordered account per run, in three voices. TRUTH is what happened, SENSOR is the first record each sensor made of each object, and C2 is what the command post concluded. It ends with the outcome per hostile and the audit.
- **Runs page** (`scripts/publish_runs.py <built console>`): every run gets its own console, its log book and its raw files, behind one index.
- **Asset catalog** (`data/assets.json`, `data/scenario_presets.json`) feeds `generate_scenario.py`. The archetypes are Geran-2/Shahed, Gerbera, Orlan-10, ZALA, Supercam and Lancet, and the response assets are interceptor drones, ground teams and air-defence markers, with fictional protected sites.

## The console
- `python -m mirrorworld dash` writes `out/<name>/dashboard/`: a static Cesium replay plus `data.js`, and a baked Sentinel-2 terrain texture so nothing is fetched live.
- The full console lives in `dashboard/` (Vite + CesiumJS) and runs from the same `data.js`:
  ```sh
  npm install && npm run data:export && npm run dev
  ```
  `npm run build` produces a static `dist/` you can serve with any web server.
- **Modes:** operator view (sensor data only), god mode (truth), and delta (both, with error lines).
- **Remote access:** tailnet-only via `tailscale serve`, never public (see `CONTRACT.md` → Remote access).

## Repository
```
mirrorworld/        engine: config, world (DEM), truth, sensors/, builder, audit, dashboard exporter, prompt
scenarios/          hero + baked sector scenarios        tests/       one self-check per module
data/               asset catalog and presets             baselines/   one-shot LLM comparison dataset
dashboard/          Vite + Cesium console                 docs/        research notes and briefs
tools/              Blender sprite renderer               scripts/     status board
```
Every module has a self-check: `uv run python tests/test_<module>.py`.

## Data sources and attribution
- Terrain: Copernicus DEM GLO-30, © DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018, provided under COPERNICUS by the European Union and ESA.
- Imagery: contains modified Copernicus Sentinel data (Sentinel-2 L2A via the Earth Search STAC catalogue).
- Radio-mast locations: © OpenStreetMap contributors (ODbL).
- Orbits: CelesTrak. Ephemeris: JPL DE421.
- Console basemap outside the scenario area: Esri, Maxar, Earthstar Geographics.
- Platform numbers are public-source archetypes, not performance data. Sources are in `docs/research/`.
