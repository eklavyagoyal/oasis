# Gameplan: OASIS (hand-in 16:00 CEST)

**One line:** We don't predict drones; we *write* the truth and then simulate exactly what every sensor would have recorded. Defence AI teams get the recordings **plus the answer key**, the data they can't safely or legally collect themselves. *We make the exam; their software takes it.*

**Pitch spine:** One true world on real Ukrainian terrain → physics decides what each sensor sees → every record traces back to the object that caused it → our auditor proves it, and catches a one-shot LLM dataset failing the same checks.

Roles: **Core** (generator, integration), **Pitch** (deck, demo script, presenting), **QA** (two people: run, inspect, README, backup video).

---

## Scope (locked)
- **Where:** Ukraine only, three pre-baked sectors. `random` picks one.
  - **Ros valley:** the brief's own place; the hero scenario.
  - **Kupiansk / Oskil river:** front sector with chalk bluffs.
  - **Vovchansk:** border sector, river valley.
- **Terrain:** real 30 m terrain + satellite texture, baked offline. Nothing is fetched live during the demo.
- **Simulation:** Python, deterministic from a seed. It runs the whole scenario first and writes files; the UI replays at 1×–60×. Nothing is simulated in the browser.
- **LLM role:** prompt → knobs/config only. All physics and sensor maths is code.
- **Knobs:** seed, sector, drone count (1–50), drone mix, entry side + heading, time of day, sensor preset, defence on/off. Templates: **incoming / intercepted / lost-contact**.
- **Ground assets:** RF-01/RF-02 (direction finding), RADAR-01, CAM-01 (EO), ACOUSTIC-01, C2-01 (alerts + response-asset status), SITE-01 (protected site: approached / reached / not reached).
- **Aircraft archetypes:** Geran-2/Shahed, Gerbera decoy, Orlan-10, ZALA, Supercam, plus small UAS (Mavic, analog FPV, fiber FPV).
- **Response assets:** interceptor drone, mobile AD team, AD battery. They're status changes (available → alerted → responding → outcome); no weapon mechanics.
- **Out of scope:** Telegram/X scraping (pitch slide only), live data, regions outside Ukraine, 3D buildings.

## Status board
| Part | Stream | State |
|---|---|---|
| Contract, config schema, platform catalog (incl. archetypes + response assets) | Core | ✅ |
| World (Copernicus 30 m DEM), truth, CLI | Core | ✅ |
| **RF direction finding:** ITU-R P.526 terrain physics, jamming, find-the-pilot, crossed-bearing fixes, TAK CoT | Core | ✅ |
| Raw IQ snapshots (SigMF, per-burst labels) | Core | ✅ |
| Hero scenario: real masts, two acts, ridge leg routed by the terrain map | Core | ✅ |
| Auditor + one-shot LLM baseline | Core | 🔍 in review |
| 3D replay console + data exporter | Core | 🔨 |
| Camera, satellite, microphones, Remote ID + telemetry, reports + prompt mode | Core (parallel builds) | 🔨 |
| Scenario builder: sectors, knobs, templates | Core | 🔨 |
| Radar (RADAR-01) and C2-01 alerts + response status | Core | 🔨 |
| Polished console from `docs/ui-prompt.md` | Core | 🔨 |
| Deck + demo script | Pitch | 🔨 |
| QA of merged outputs, README draft, backup video | QA | 🔨 |

---

## Timeline
| CEST | Stream | What |
|---|---|---|
| **13:15–14:15** | Core | Merge parallel builds as they land; re-run hero + audit after each merge; `OPENAI_API_KEY` into `.env` |
| | Pitch | Deck skeleton + demo script (beats below) |
| | QA | Open each merged output, sanity-check realism, log issues; README draft; start the backup recording |
| **~13:45** | Core | Data bundle (`data.js` + media) to the console build |
| **14:15–14:45** | all | **Integration:** one command → all sensors → audit → console. Bake the three sectors. Audit stays honest |
| **14:45–15:00** | Core | Prompt-mode run on a new prompt; screenshots |
| **15:00** | — | **FEATURE FREEZE.** Bug fixes only |
| **15:00–15:40** | Pitch (lead), all | Numbers from `audit.md` into the deck; two rehearsals; backup video final |
| **15:40–15:50** | Core | Hand-in checklist → repo public |
| **16:00** | Pitch | Present |

**Stretch, only if time frees before 14:30:** tracker + 30 s path forecast scored against truth, shown as a forecast cone.

---

## Demo script (~4 min)
1. **Globe → Ukraine → "Enter sector".** Real terrain, receivers on two **real** radio masts from OpenStreetMap.
2. **09:06:39Z: Sentinel-2A really passes.** A Shahed at 1,200 m is smeared into colour fringes because each band is captured a fraction of a second apart.
3. **14:02:07Z: the brief's exact example point.** Our Mavic is there; the bearings cross on it, and the fix lands a few hundred metres off, as a real one would.
4. **Lost contact.** The terrain map routed the drone through RF-02's dead zone. RF-02 loses it for ~2 min, RF-01 keeps it, and received power drops ~30 dB.
5. **Find the pilot.** The controller uplink is a separate transmitter, and crossed bearings land on the pilot.
6. **Jammed.** A 2.4 GHz barrage blinds RF-01; 868 MHz control survives; a hill shields RF-02.
7. **Invisible to radio.** A fiber-optic FPV produces zero RF detections, but the microphones, camera and radar catch it.
8. **Lying sensors.** Remote ID leaks the pilot's GPS; friendly telemetry drifts ~2 km under GNSS spoofing while RF stays on truth.
9. **Intercepted.** C2-01 alerts, the interceptor responds, the outcome is recorded, and SITE-01 is not reached.
10. **Proof.** Audit scorecard: OASIS vs one-shot LLM, same checks, same scenario.

## Deck (6 slides)
1. **Problem:** defence AI is starved of labelled, multi-sensor data and edge cases.
2. **What it is:** one world → physics → sensor files + answer key.
3. **Live demo.**
4. **Proof:** the audit table vs one-shot LLM.
5. **Why it's real:**
   - ITU-R P.526 terrain diffraction, validated against the reference code to 1e-14 dB
   - real DEM, masts, orbits and sun
   - TAK/CoT, SigMF, WAV and GeoTIFF outputs
   - a 5.7 h scenario generates in ~10 s
6. **Who pays:** C-UAS vendors (training, benchmarking), militaries (sensor siting: "where is my network blind?"), integrators (TAK-native test feeds). Telegram/X ingestion is roadmap.

## Q&A prep
| Question | Answer |
|---|---|
| How do you know the physics is right? | Validated propagation code, real terrain, and an auditor whose checks don't use our own model (geometry, line of sight, causality). |
| Why better than asking a general LLM once? | One-shot output looks plausible line by line but fails cross-checks: bearings that don't point at the drone, signal that ignores the hill, clocks that disagree. The audit table shows it. |
| Can it use our real data? | Every number lives in `catalog.py` and the sensor params. Calibrate against real recordings and the generator inherits it. |
| Scale? | Seeded and deterministic; knobs or a prompt → a new scenario in seconds; any sector. |
| What's not real? | Tactics, exact military waveforms and some emitter powers. These are public-source archetypes, documented in `docs/research/`. |

---

## Risks → mitigations
| Risk | Mitigation |
|---|---|
| Build-tooling content filter | Neutral wording, or rebuild that part in Core |
| No OpenAI key | Template reports; prompt mode and baseline need the key, so get it in by 13:45 |
| WebGL or network fails on the presenting laptop | Pre-baked outputs, cached terrain/orbits/imagery, backup video, screenshots in the deck |
| Merge breaks the hero | Re-run hero + tests after every merge; `main` must always run |
| Time | 15:00 freeze is real |

## Hand-in checklist (15:40)
- [ ] Clean clone → `uv sync` → `uv run python -m mirrorworld run scenarios/ros-valley.yaml` works
- [ ] `audit` and `dash --serve` work; screenshots in README
- [ ] Per-scenario outputs: hero dataset zip as a GitHub Release asset, plus a small browsable sample under `examples/`
- [ ] README: what, why, quickstart, outputs and formats, physics notes, data licences and attribution (Copernicus, ESA WorldCover, OSM, Sentinel-2, imagery), credits
- [ ] `git ls-files` contains no `chat.md`, no challenge PDF, no `.env`
- [ ] Repo → public: `gh repo edit --visibility public --accept-visibility-change-consequences`

## Commands
```
uv sync
uv run python -m mirrorworld run scenarios/ros-valley.yaml            # generate (add --skip-missing while modules land)
uv run python -m mirrorworld audit out/ros-valley                     # proof
uv run python -m mirrorworld dash out/ros-valley --serve              # 3D console at localhost:8765/dashboard/
uv run python -m mirrorworld prompt "..." -o scenarios/new.yaml --run # text → scenario
uv run python -m mirrorworld.builder --sector random --seed 7 --run   # knobs → scenario
```
