# OASIS: live build status

_Updated 16:10 CEST, 18 Oct 2026. Auto-generated on the `status` branch; `main` holds the product._

**OASIS** generates synthetic aerial defence scenarios over real Ukrainian terrain: one true world, every sensor's physically faithful recordings, and an answer key tracing each record to its cause.

## What changed since the last update

- New front door: a 3D globe with Ukraine highlighted, a seed dialog (world seed, scenario seed, attacker mix, duration) and instant browser exercises that play inside the existing console.
- Five fixed showcase scenarios (power station, water works, hospital) reproduce their planned outcomes on the full sensor set; two audit fully clean.
- Map markers are now high-resolution glass badges, coloured by side and status, for sites, teams, sensors and drones.
- Fixed while integrating: the seed dialog rejected every attacker type, and the entry globe failed to load in production builds.

## Commits on main since the last update

- Seed screen: accept attackers by catalog category (the catalog's side field names nations, not roles); bundle the map library's worker so the entry globe loads in production builds (3244f09)
- Console flow: neutral comments, drop a link to a guide that does not exist (eb8213b)
- Drop the internal iteration notes from the console branch (46e278b)
- feat: connect OSIRIS entry and seed screen to Night Glass simulation (e120f03)
- fix: retain source provenance and complete browser run records (9ec1fa1)
- feat: render recorded browser runs inside existing Cesium map (5483b81)
- feat: transplant OSIRIS entry and Ukraine seed screen into Vite (4f91300)
- fix: distinguish generated readings from real terrain in existing console (b4437aa)
- feat: recover browser seed engine on latest Night Glass base (9df2347)
- Console: glass badge markers (dark disc, coloured ring and glow, white catalog glyph) rendered at 128 px; colour by side and status for sites, teams, sensors and drones (971aef9)
- Add five fixed replay showcase scenarios (28022b6)

## Sensor modules on main

`c2`, `camera`, `microphone`, `radar`, `remote_id`, `reports`, `rf_df`, `rf_iq`, `satellite`, `telemetry`

## Self-checks (run now)

| check | result |
|---|---|
| `audit` | ✅ |
| `builder` | ✅ |
| `c2` | ✅ |
| `camera` | ✅ |
| `dashboard` | ✅ |
| `foundation` | ✅ |
| `llm` | ✅ |
| `lying` | ✅ |
| `microphone` | ✅ |
| `radar` | ✅ |
| `rf_iq` | ✅ |
| `satellite` | ✅ |

## Hero audit (independent physics checks)

**9 pass · 0 fail · 1 skip**

| check | status | value |
|---|---|---|
| Provenance | PASS | 0 |
| Clock sync | PASS | 0 |
| Bearing geometry | PASS | 0.948 |
| Terrain shadow | SKIP | — |
| Occlusion gaps | PASS | 0.0 |
| Fix calibration | PASS | 0.5254 |
| Range law | PASS | 4.154 |
| Acoustic delay | PASS | 0.0017 |
| Spoof visibility | PASS | — |
| Cross-sensor time | PASS | 1.0 |

One-shot LLM baseline on the same window: **1 pass · 3 fail · 6 skip**

## Run it

```
uv sync
uv run python -m mirrorworld run scenarios/ros-valley.yaml --skip-missing
uv run python -m mirrorworld audit out/ros-valley
uv run python -m mirrorworld dash out/ros-valley --serve
uv run python generate_scenario.py --matrix --seed 1
```
