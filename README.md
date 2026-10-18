# OASIS: live build status

_Updated 16:40 CEST, 18 Oct 2026. Auto-generated on the `status` branch; `main` holds the product._

**OASIS** generates synthetic aerial defence scenarios over real Ukrainian terrain: one true world, every sensor's physically faithful recordings, and an answer key tracing each record to its cause.

## What changed since the last update

- The README was rewritten and checked against the current runs: the live console flow, the scenario library, the five showcase stories with reproduced outcomes, the airframe markers and the full list of known limits.
- The entry screen and the scenario titles now describe exactly what they open: physics-engine scenarios, with the hero day spanning 08:55 to 14:35 UTC.

## Commits on main since the last update

- Entry screen: describe the physics-engine scenarios it now opens (c18731e)
- Neutral wording for the propagation validation credit; the hero's library title matches its 08:55-14:35 UTC window (7054784)
- README: verified against the current runs; live console flow, scenario library, showcase stories with reproduced outcomes, Blender airframe markers, updated known limits, fresh screenshots (781bad6)

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
