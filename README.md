# OASIS: live build status

_Updated 14:41 CEST, 18 Oct 2026. Auto-generated on the `status` branch; `main` holds the product._

**OASIS** generates synthetic aerial defence scenarios over real Ukrainian terrain: one true world, every sensor's physically faithful recordings, and an answer key tracing each record to its cause.

## What changed since the last update

- Engine runs end to end on real terrain: truth plus 11 sensor types (RF direction finding, raw IQ, radar, two cameras, Sentinel-2 satellite, microphones, Remote ID, telemetry, human reports, C2 alerts)
- Radar added: terrain-masked X-band plots with Swerling fluctuation and a tracker; it cues a camera so frames catch real drones
- Asset catalog drives real runs: generate_scenario.py turns preset × sector × drone × response × site into audited OASIS scenarios
- Coordinates instead of place names everywhere on screen; Ukraine-only
- Proof: OASIS 7 PASS vs one-shot LLM 1 PASS / 3 FAIL on the same 10-minute window

## Commits on main since the last update

- Live status board script for the status branch; hero microphones at 8 kHz (26818d7)
- Radar: X-band plots with terrain masking, Swerling-1 Pd, class confusion, clutter, alpha-beta tracker; radar-cued camera; hero gains RADAR-01, CAM-02, SITE-01, AD team, C2-01; state() cached per object (78daf64)
- UI brief: drop the last place name (2274b5c)
- UI brief: coordinates instead of place names; Ukraine-only world (c644426)
- Show coordinates, never place names: coordinate labels in the data, coordinate-based scenario names, neutral emitter ids (603050e)
- C2: event log and status board from the other sensors' outputs (5d448df)
- generate_scenario.py: asset-catalog presets drive real OASIS runs (builder + physics + audit), blind observations + answer key + truth outcome; --matrix for every preset x sector (31b9984)
- builder: deterministic knobs+seed -> validated Scenario YAML (346cfa2)
- Catalog: variants and aliases for the asset catalog (Lancet, Octopus/JEDI, AD markers, fictional sites) (52b85d6)
- docs: art-direction brief v2 for the console; ignore baked texture in the UI public dir (e35469b)
- Bake a real Sentinel-2 true-colour + DEM-hillshade terrain texture into the dashboard bundle; microphone fixes (CFAR tracker, harmonic power orientation, off-air sources) (744b395)
- microphone: per-mic WAVs with retarded-time Doppler/delay, ISO 9613-1 absorption, Maekawa terrain screening, wind; CFAR tone tracker (835c8d3)
- camera: radar cueing (confirmed tracks with altitude) alongside RF fixes (02a9141)
- reports: low-frequency air absorption (1 dB/km) so engines are heard at realistic ranges (cf15939)
- Lane D: physics-grounded human reports (HUM1) and LLM prompt mode (98a696c)
- Security: safe-token ids and module-name sensor types, HTML escaping in the console, host allow-list and no listings on the static server, plain relative media paths, SRI on Cesium CDN (3e19f71)
- dash: data.js exporter + static Cesium console (own DEM terrain, LOBs, fixes, shadows, feeds) (ef32060)
- Add synthetic scenario asset catalog and presets (c64fde5)
- Requirement: tailnet-only remote access via tailscale serve + SSH (8536dbd)
- camera: EO1 PTZ camera — RF-fix cueing, real sun + DSM horizon scene, hazed silhouettes, simulated detector with answer key (456d47f)
- satellite: real S2A pass + real L2A background + sub-pixel movers with band fringes and sun shadows (3583819)
- One-shot LLM baseline dataset (fair 10-minute window) for the audit comparison (ef18bc1)
- gitignore: anchor out/ and cache/ to the repo root (03027a9)
- Audit: --window for like-for-like comparisons, value-level truth-leak check, minimum-sample guards, path-loss exponent law (f9ba263)
- Fixes emitted in time order; spoof check only compares spoofed objects (1fadc57)
- baseline: runnable as a plain script (6fa0259)
- lying sensors: Remote ID (DroneID-style) + own-drone telemetry logs (2e7b6cb)
- Name the system OASIS (2a8bef5)
- Catalog: aircraft archetypes, response assets, protected site, radar cross-sections; scope v2 in GAMEPLAN (d96889e)
- audit: independent physics audit + one-shot LLM baseline (556ac9d)
- GAMEPLAN.md: status board, timeline to hand-in, demo script, deck, Q&A, checklist (837a140)
- docs: design brief for the Mirror World console (02da0e7)
- rf_iq: SigMF IQ snapshots of the 2.4 GHz band with per-burst labels in the answer key (cdfbb4f)
- Contract: media.csv convention for the 3D dashboard (acf34fd)
- Contract: hero scenario facts, lane notes; research notes in docs/research (af6a174)
- Foundation (world, truth, CLI) + RF engine + two-act hero day (cf8b6fc)
- Team contract, config schema, platform catalog, hero scenario (350baae)
- Start Mirror World repo (89b1081)

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
| Clock sync | FAIL | 2 |
| Bearing geometry | PASS | 0.9484 |
| Terrain shadow | PASS | 18.14 |
| Occlusion gaps | PASS | 0.0 |
| Fix calibration | PASS | 0.4695 |
| Range law | PASS | 2.127 |
| Acoustic delay | FAIL | 0.0517 |
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
