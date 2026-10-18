# OASIS: live build status

_Updated 16:27 CEST, 18 Oct 2026. Auto-generated on the `status` branch; `main` holds the product._

**OASIS** generates synthetic aerial defence scenarios over real Ukrainian terrain: one true world, every sensor's physically faithful recordings, and an answer key tracing each record to its cause.

## What changed since the last update

- The console now opens onto a scenario library of eleven audited physics runs (the hero day, five seed-engine templates and five showcase stories) instead of a simplified browser approximation.
- Drones on the map are drawn as their Blender-rendered airframes, turned to their heading.
- Readability pass: graded imagery, dark backgrounds behind every map label and halos on overlay text, so everything reads on any terrain.

## Commits on main since the last update

- Runs page: titles per scenario and runs/index.json for the console's scenario library (0a5d816)
- Console: readable on any terrain (graded imagery, dark pills behind map labels, halo on overlay text); drones drawn as their Blender airframe inside the badge, turned to heading; Enter simulation opens a library of the audited physics runs instead of the browser approximation (7776acd)

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
