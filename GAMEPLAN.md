# Gameplan: Mirror World (hand-in 16:00 CEST)

**One line:** We don't predict drones; we *write* the truth and then simulate exactly what every sensor would have recorded. Defence AI teams get the recordings **plus the answer key**, the data they can't safely or legally collect themselves. *We make the exam; their software takes it.*

**Pitch spine:** One true world on real Ukrainian terrain → physics decides what each sensor sees → every record traces back to the object that caused it → our auditor proves it, and catches a one-shot LLM dataset failing the same checks.

---

## Status board (13:05)
| Part | Owner | State |
|---|---|---|
| Contract, config schema, platform catalog | Claude | ✅ `CONTRACT.md` |
| World (Copernicus 30 m DEM), truth, CLI | ompw → Claude review | ✅ |
| **RF direction finding**: ITU-R P.526 terrain physics, jamming, find-the-pilot, crossed-bearing fixes, TAK CoT | Claude | ✅ |
| Raw IQ snapshots (SigMF, per-burst labels) | ompw | ✅ |
| Hero scenario: real masts, two acts, ridge leg routed by terrain map | Claude | ✅ `scenarios/ros-valley.yaml` |
| 3D dashboard (Cesium, our own DEM, no keys) + data exporter | ompw (worktree `mw-dashboard`) | 🔨 |
| Camera (RF-cued, real sun, DEM horizon, true pixel size) | ompw (`mw-camera`) | 🔨 relaunched after content filter |
| Satellite (real S2A pass 09:06:39Z, band-timing colour smear) | ompw (`mw-satellite`) | 🔨 |
| Microphones (delay, Doppler, ridge muffling; catches the fiber FPV) | ompw (`mw-acoustic`) | 🔨 |
| Remote ID + telemetry (pilot GPS leak, GNSS spoofing drift) | ompw (`mw-lying`) | 🔨 |
| Civilian/observer reports + prompt mode (OpenAI) | ompw (`mw-llm`) | 🔨 needs `OPENAI_API_KEY` |
| Auditor + one-shot LLM baseline | ompw (`mw-audit`) | 🔨 baseline needs the key |
| Beautiful console (external agent, `docs/ui-prompt.md`) | Eklavya | 🔨 |

Claude reviews every agent's diff, merges into `main`, and re-runs the hero after each merge.

---

## Timeline
| CEST | Who | What |
|---|---|---|
| **13:05–14:00** | Claude | Merge agents as they land; fix integration bugs; re-run hero + audit after each merge |
| | Eklavya | `OPENAI_API_KEY` into `.env`; drive the UI agent; unblock decisions |
| | Abhi | Pitch deck skeleton + demo script (beats below) |
| | Alankrit, Sheika | QA as modules merge: run, open outputs, sanity-check realism, log issues; README draft; record a backup demo video |
| **~13:30** | Claude | Hand Eklavya the data bundle (`data.js` + media) for the UI agent |
| **14:00–14:30** | all | **Integration:** one command → all sensors → audit → dashboard. Audit must be honest (no loosened thresholds) |
| **14:30–15:00** | Claude + Eklavya | Second scenario from a text prompt (e.g. Kaniv dam at dusk) to prove prompt mode; screenshots; drop the UI agent's `dist/` in |
| **15:00** | — | **FEATURE FREEZE.** Only bug fixes after this |
| **15:00–15:40** | Abhi (lead), all | Numbers into the deck from `audit.md`; two full rehearsals; backup video final |
| **15:40–15:50** | Claude + Eklavya | Hand-in checklist below → repo public |
| **16:00** | Abhi + Eklavya | Present |

**Stretch, only if a slot frees before 14:30** (Eklavya decides): a small tracker + 30 s path forecast scored against truth, shown as a forecast cone in the dashboard. This is "an algorithm trained and graded on Mirror World".

---

## Demo script (~4 min, PRESENT mode drives it)
1. **One world, real terrain.** Ros valley, Cherkasy oblast, 4 Nov 2026. Copernicus 30 m terrain. Receivers on two **real** radio masts from OpenStreetMap.
2. **09:06:39Z: Sentinel-2A really passes.** A Shahed at 1,200 m is smeared into colour fringes because each band is captured a fraction of a second apart (the brief's own example, done for real).
3. **14:02:07Z: the brief's exact example point.** Our Mavic is there; the bearings from both masts cross on it, and the fix lands a few hundred metres off, as a real one would.
4. **Behind the ridge.** The terrain-shadow map routed the drone through RF2's dead zone. RF2 loses it for about 2 minutes, RF1 keeps it, and the received power drops ~30 dB. Computed, not narrated.
5. **Find the pilot.** The controller's uplink is a separate transmitter; crossed bearings land on the pilot (~360 m median).
6. **Jammed.** A 2.4 GHz barrage jammer blinds RF1; 868 MHz FPV control survives; a hill shields RF2. The IQ spectrogram floods.
7. **Invisible to radio.** A fiber-optic FPV produces zero RF detections. The microphones hear it, and civilians report "FPV, heard not seen".
8. **Lying sensors.** Remote ID leaks the pilot's GPS. Our own drone's telemetry drifts ~2 km under GNSS spoofing while RF fixes stay on the truth.
9. **Sensor down.** An FPV hits RF2's mast; RF2 goes dark at that exact second.
10. **Proof.** Audit scorecard: Mirror World vs a one-shot LLM dataset, same checks, same scenario.

## Deck (6 slides, Abhi)
1. Problem: defence AI is starved of labelled, multi-sensor data and edge cases.
2. What Mirror World is: one world → physics → sensor files + answer key (pipeline diagram from `CONTRACT.md`).
3. Live demo (the console).
4. Proof: the audit table vs one-shot LLM.
5. Why it's real:
   - ITU-R P.526 terrain diffraction, validated against the ITU reference code to 1e-14 dB
   - real DEM, masts, satellite orbits and sun
   - TAK/CoT, SigMF, WAV and GeoTIFF outputs
   - a 5.7 h scenario generates in ~10 s
6. Who pays: C-UAS vendors (training and benchmarking), militaries (sensor siting: "where is my network blind?"), integrators (TAK-native test feeds).

## Q&A prep
| Question | Answer |
|---|---|
| How do you know the physics is right? | Validated propagation code, real terrain, and an auditor whose checks don't use our own model (geometry, line of sight, causality). |
| Why is this better than asking Claude/ChatGPT once? | One-shot output looks plausible line by line but fails cross-checks: bearings that don't point at the drone, signal that ignores the hill, clocks that disagree. The audit table shows it. |
| Can it use our real data? | Every number lives in `catalog.py` and the sensor params. Calibrate against your recordings and the generator inherits it. |
| Scale? | Seeded and deterministic. A prompt or random config → a new scenario in seconds. Any location in Ukraine. |
| What's not real? | Tactics, exact military waveforms, and some emitter powers. These are public-source approximations, marked in `docs/research/`. |

---

## Risks → mitigations
| Risk | Mitigation |
|---|---|
| Agent model content filter (Xiaomi via OpenRouter) | Neutral wording / switch model / Claude takes it |
| No OpenAI key | Template reports; prompt mode and baseline need the key, so get it in by 13:30 |
| WebGL or network fails on the presenting laptop | Pre-generated outputs, cached DEM/TLE/S2 in `cache/`, backup video, screenshots in the deck |
| Merge breaks the hero | Re-run hero + tests after every merge; `main` must always run |
| Time | 15:00 freeze is real |

## Hand-in checklist (15:40)
- [ ] Clean clone → `uv sync` → `uv run python -m mirrorworld run scenarios/ros-valley.yaml` works
- [ ] `audit` and `dash --serve` work; screenshots in README
- [ ] Per-scenario outputs attached: hero dataset zip as a **GitHub Release** asset, plus a small browsable sample committed under `examples/`
- [ ] README: what, why, quickstart, outputs and formats, physics notes, data licences and attribution (Copernicus, ESA WorldCover, OSM, Esri, Sentinel-2), credits (God's Eye View inspiration, MIT)
- [ ] `git ls-files` contains no `chat.md`, no challenge PDF, no `.env`
- [ ] Repo → public (`gh repo edit eklavyagoyal/mirror-world --visibility public --accept-visibility-change-consequences`)

## Commands
```
uv sync
uv run python -m mirrorworld run scenarios/ros-valley.yaml            # generate (add --skip-missing while modules land)
uv run python -m mirrorworld audit out/ros-valley                     # proof
uv run python -m mirrorworld dash out/ros-valley --serve              # 3D console at localhost:8765/dashboard/
uv run python -m mirrorworld prompt "..." -o scenarios/new.yaml --run # text → scenario
```
