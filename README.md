# OASIS: live build status

_Updated 15:41 CEST, 18 Oct 2026. Auto-generated on the `status` branch; `main` holds the product._

**OASIS** generates synthetic aerial defence scenarios over real Ukrainian terrain: one true world, every sensor's physically faithful recordings, and an answer key tracing each record to its cause.

## What changed since the last update

- The hero day was re-run: its 10-minute window now passes 9 of 9 applicable independent checks, against 1 for the one-shot LLM dataset.
- The README now tells the full story: the check-by-check proof, the hero-day timeline, the seed engine with each template's audit, the log book and the known limits.
- Console markers and labels now scale with zoom, with detail lines only up close, so the overview stays clean.
- The console is live as a public static site (trimmed media), and the commit history carries no tool attribution.

## Commits on main since the last update

- Console: markers and labels scale with zoom (about 1x in the overview, up to 1.7x close in), detail lines only within 12 km, status shown as colour at any zoom, one marker and label per sensor mast (c40657d)
- README: the full story for the jury: proof table per check against the one-shot LLM (9 pass vs 1 pass), hero-day timeline, seed engine and templates with their audits, log book, console, known limits (c313830)

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
