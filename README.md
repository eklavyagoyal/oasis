# OASIS: live build status

_Updated 14:57 CEST, 18 Oct 2026. Auto-generated on the `status` branch; `main` holds the product._

**OASIS** generates synthetic aerial defence scenarios over real Ukrainian terrain: one true world, every sensor's physically faithful recordings, and an answer key tracing each record to its cause.

## What changed since the last update

- 3D drone models: delta wing, quadcopter and fixed wing rendered from every viewing angle and drawn by the camera at true size and aspect (32 px at 400 m, about 6 px at 2,140 m)
- High-value assets on the map and in the data: protected sites with 1 km approach and 100 m impact rings, response teams with live status from the command post
- Console: readable type, surrounding landscape rendered as dimmed context, coordinates instead of place names, real satellite terrain
- README rewritten for the hand-in with the proof table: OASIS 7 pass vs one-shot LLM 1 pass / 3 fail

## Commits on main since the last update

- README: 3D drone near/far through the camera model (3c5ad6e)
- gitignore: baked texture in the console public dir (c46047a)
- 3D drone sprites rendered in Blender and drawn by the camera at true size and aspect; high-value assets (protected sites, response teams) in the data and on the console; console source; README for the hand-in (0ed36c7)

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

**8 pass · 2 fail · 0 skip**

| check | status | value |
|---|---|---|
| Provenance | PASS | 0 |
| Clock sync | FAIL | 1 |
| Bearing geometry | PASS | 0.9484 |
| Terrain shadow | PASS | 18.14 |
| Occlusion gaps | PASS | 0.0 |
| Fix calibration | PASS | 0.4695 |
| Range law | PASS | 2.127 |
| Acoustic delay | FAIL | 0.0516 |
| Spoof visibility | PASS | — |
| Cross-sensor time | PASS | 1.0 |

## Run it

```
uv sync
uv run python -m mirrorworld run scenarios/ros-valley.yaml --skip-missing
uv run python -m mirrorworld audit out/ros-valley
uv run python -m mirrorworld dash out/ros-valley --serve
uv run python generate_scenario.py --matrix --seed 1
```
