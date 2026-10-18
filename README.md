# OASIS: live build status

_Updated 15:23 CEST, 18 Oct 2026. Auto-generated on the `status` branch; `main` holds the product._

**OASIS** generates synthetic aerial defence scenarios over real Ukrainian terrain: one true world, every sensor's physically faithful recordings, and an answer key tracing each record to its cause.

## What changed since the last update

- Seed engine: each sector's built world (protected site, air-defence positions, receiver masts, microphones) is now fixed and the seed only changes what moves; two new templates, a saturation raid and a recon-strike.
- Every run now gets a log book: one timeline of what really happened, what each sensor first recorded and what the command post concluded, ending with the audit.
- Running the full pipeline found and fixed two crashes (fixed-wing drones in the camera, newer airframes at the microphones) and an audit error (speed of sound assumed 20 °C air).
- The 3D console is merged into main, with asset-catalog icons for sites, teams, drones and sensor masts.

## Commits on main since the last update

- README: seed engine, log book and runs page; distance-law numbers from the current audit; the fibre FPV claim matches the data; machine hostnames replaced by placeholders (29d3136)
- Audit uses the scenario's air temperature for the speed of sound (was a fixed 343 m/s, the 20 C value); reports carry t and, like microphones, stop at the end of the recording window; publish_runs.py gives every run its own console, log book and raw files (8cd871c)
- Seed engine: the sector's built world (site, AD positions, masts, calibration, mics) is fixed, the seed drives only what moves; saturation and recon-strike templates; --seeds sweeps; log book per run; camera and microphone handle every catalog airframe (569db75)
- Console: asset-catalog icons for sites, teams, drones and sensor masts; coordinate label and asset layer carried through the exporter (c989323)
- Console validator: link -1 means no link (false alarm), as in the data contract (ba84ef6)
- Console: accept site/response objects; the truth layer leaves them to the assets layer (ab48e60)
- Console: full landscape as dimmed context (no clip), coordinates instead of place names, high-value asset layer, readable type (6214680)
- Console: never clip the globe; the full landscape renders as dimmed context around the sector (31aa236)
- Every run must include the signal trace (an rf_df sensor) (b420a2e)
- Add Mirror World challenge brief to docs (c93cdab)

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

**8 pass · 1 fail · 1 skip**

| check | status | value |
|---|---|---|
| Provenance | PASS | 0 |
| Clock sync | FAIL | 1 |
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
