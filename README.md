# OASIS: live build status

_Updated 17:25 CEST, 18 Oct 2026. Auto-generated on the `status` branch; `main` holds the product._

**OASIS** generates synthetic aerial defence scenarios over real Ukrainian terrain: one true world, every sensor's physically faithful recordings, and an answer key tracing each record to its cause.

## What changed since the last update

- The hand-in is self-contained: the pitch deck (pptx and pdf), the full hero dataset without its heavy media, and the scenario, audit and log book of every generated run.
- The README points to the live console, and the three-minute pitch script sits next to the deck.
- The third-party licence file and the design references now use neutral names.

## Commits on main since the last update

- Neutral names: third-party licence file and design references (357c366)
- Live console at oasis.eklavyagoyal.com; the 3-minute pitch script next to the deck (e1c1cae)
- Self-contained hand-in: the pitch deck (pptx and pdf), the complete hero dataset without heavy media, and the scenario, audit and log book of every generated run (bf9fa22)

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
