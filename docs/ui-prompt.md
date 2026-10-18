# Build the OASIS console

You are a world-class creative technologist: half motion/UI designer from the studios behind the screens in *Blade Runner 2049* and *Oblivion*, half senior WebGL/CesiumJS engineer. Build the single most beautiful, futuristic and *credible* 3D command console you have ever made. It is the screen a defence-tech jury watches during a 4-minute live demo today. It has to make them lean forward in the first 3 seconds and trust it by second 30.

## What it visualises
**OASIS** is a synthetic battlespace generator, our answer to the "Mirror World" challenge. Given a scenario, it builds **one true world** on real Ukrainian terrain (Copernicus 30 m elevation data; receivers on real radio masts from OpenStreetMap; a real Sentinel-2 satellite pass; the real sun). Every sensor then records only what physics lets it observe:
- radio direction-finders (lines of bearing + crossed-bearing position fixes)
- raw IQ spectrum snapshots
- an RF-cued camera
- microphones
- a satellite image
- Remote ID / drone telemetry (which can *lie*: GNSS spoofing)
- civilian sighting reports

An **answer key** links every record to the object that really produced it. The console's job is to make one idea visceral: **the sensor picture is not the truth, and the gap between them is computed, not invented.**

The hero scenario: the Ros river valley near Korsun-Shevchenkivskyi, Cherkasy oblast, 4 Nov 2026, 08:55–14:35 UTC, in two acts.
- **Morning:** a Shahed crosses while Sentinel-2A passes overhead.
- **Dusk (sunset 14:29Z):**
  - a hostile Mavic slips behind a ridge, hidden from one receiver
  - its pilot is located from his controller's signal
  - a jammer blinds 2.4 GHz
  - a fiber-optic FPV is invisible to radio but heard by microphones
  - an FPV destroys receiver RF2's mast

## The data (your only input). Treat `data.js` as the source of truth.
You get a folder containing `dashboard/data.js` (it defines `window.MW = {...}`) plus `sensors/<id>/...` media referenced by relative paths. Load it with `<script src="./data.js"></script>` *before* your bundle. Also support **drag-and-drop of a data.js file** onto the page to load another scenario. If a field differs from the description below, adapt to the real file and note it.

```
MW.scenario  {name, start (ISO UTC), duration_s, area {lat, lon, size_km}, weather {wind_from_deg, wind_mps, temp_c, rh_pct, visibility_km, cloud_pct}}
MW.terrain   {west, south, east, north, nx, ny, h[]}   heights in metres, row-major, rows SOUTH->NORTH, cols WEST->EAST.
             This is the exact DEM the physics used: render THIS, not a third-party terrain.
MW.objects   [{id, type, kind (drone|bird|operator|emitter), side (hostile|friendly|neutral|unknown), controls, t[], lat[], lon[], alt[]}]
             1 Hz truth samples; t = seconds since scenario start; alt is metres on the SAME vertical datum as terrain.
MW.sensors   [{id, type (rf_df|rf_iq|camera|microphone|remote_id|telemetry|satellite|reports), lat, lon, ground, alt, mast_m, dead_t|null}]
MW.classes   [signal class names]          MW.links ["mavic_1:video", ...]          MW.labels ["target","friendly","clutter","false_alarm"]
MW.rf        {sensorId: {t[], brg[], std[], snr[], pwr[], cls[], obj[], link[], los[], label[]}}
             One entry per detection: bearing (deg true), its 1-sigma, SNR dB, received power dBm, class index.
             obj/link/los/label come from the answer key: obj = index into MW.objects or -1; los = 1 if the path was line-of-sight.
MW.fixes     {t[], lat[], lon[], smaj[], smin[], orient[], ce[], cep50[], cls[], obj[], err[]}
             Crossed-bearing positions computed from sensor data only. Error ellipse semi-axes in m, orientation deg from north;
             err = metres from truth (null if unknown).
MW.shadow    {sensorId: {west, south, east, north, nx, ny, agl[]}}
             Per receiver: the minimum height above ground a drone needs to be visible to it (terrain shadow / dead zones).
MW.events    [{t, label, kind}]   computed key moments, e.g. "mavic_1 hidden from RF2 by terrain", "RF2 destroyed by fpv_1",
             "jammer_1 on", "Sentinel-2A pass"
MW.media     [{sensor, kind (image|audio|iq|event), t, src}]   time-stamped camera frames, spectrograms, satellite PNGs, WAV audio
MW.audit     null | {scenario, summary {pass, fail, skip}, checks [{id, name, status PASS|FAIL|SKIP, value, threshold, detail}],
                     baseline: same shape (a one-shot-LLM dataset audited the same way) | null}
```
Story beats in hero time (t = seconds after 08:55:00Z):
- t≈699: Sentinel-2A pass + Shahed
- t=18427: 14:02:07Z, the hostile Mavic at the challenge brief's own example point
- t≈19131–19256: the Mavic's leg hidden from RF2 by terrain
- t 19850–19970: jammer
- t≈20311: RF2 destroyed

Prefer `MW.events` when present.

## Non-negotiables (engineering)
- **Stack:** CesiumJS 1.124+ (npm or `cdn.jsdelivr.net/npm/cesium@1.124.0`), Vite, TypeScript or modern JS. No UI framework is required; use one only if it truly helps. The output is a **static build** (`dist/`, `base: './'`, relative URLs only) that runs from any static server.
- **No API keys, no Cesium ion.** No Bing, no Google tiles, no ion geocoder.
  - Terrain: `CustomHeightmapTerrainProvider` (GeographicTilingScheme) sampling `MW.terrain` bilinearly, clamped at edges.
  - Imagery: Esri World Imagery (`https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}`, credit "Esri, Maxar, Earthstar Geographics"), with an OpenStreetMap fallback toggle.
  - Fonts from Google Fonts.
- **Heights:** put objects at `alt` and the terrain from `h` on the same reference, so drones fly at their true clearance above the ridges you render. Use `heightReference: NONE`.
- **Performance:** 60 fps on a MacBook Air at 1440×900 with ~30k detections.
  - Lines of bearing are a pooled `PolylineCollection`/`Primitive` rebuilt from a time window on clock tick, never thousands of Entities.
  - Truth uses `SampledPositionProperty`. Fixes are pooled.
  - Use `requestRenderMode` when paused.
  - Lazy-load media and decode audio with WebAudio.
- **Robust:** any missing sensor or media shows a designed empty state ("NO SIGNAL" with subtle animated static). No console errors. Clean at 1280×720, 1440×900, 1920×1080 and on a projector.
- **Accessible:** full keyboard control, visible focus, text contrast ≥ 4.5:1, honour `prefers-reduced-motion`.

## Visual direction
**References:** *Blade Runner 2049* / *Oblivion* UI restraint; real C2 consoles (Anduril Lattice, Palantir Gotham); open-source globe consoles. Then go **past** them: calmer, sharper, more cinematic. **Avoid:**
- SaaS cards
- rounded pastel widgets
- purple-blue AI gradients
- neon overload
- emoji
- lorem ipsum

**Palette** (colour carries meaning only):
| Role | Colour |
|---|---|
| Void | `#04060A` |
| Panel glass | `rgba(10,14,20,.62)`, `backdrop-filter: blur(14px) saturate(140%)` |
| Hairlines | `rgba(140,170,200,.14)` |
| Text | `#D8E2EC` / `#7D8A99` |
| System/sensors | cyan `#39E6FF` |
| RF signal | amber `#FFB000` |
| Hostile | `#FF3355` |
| Friendly | `#4DA3FF` |
| Neutral | `#9AA4AE` |
| Truth | pure white |
| Pass | `#3DFF9A` |

**Type:** Space Grotesk for labels (small caps, +0.12em tracking); JetBrains Mono with tabular numerals for every number, time and coordinate.
**Grid:** 8 px. **Corners:** 2 px max.
**Motion:** 180–260 ms, `cubic-bezier(.2,.8,.2,1)`, no bounce. Numbers tick when they change.

**The globe:**
- **ISLAND mode (default):** `globe.cartographicLimitRectangle` = the scenario area, so the real terrain floats as a lit slab in the void. Its edges glow faintly, and a dim graticule surrounds it. Toggle to the full globe.
- **Light:** `enableLighting` + terrain shadows driven by the scenario clock, so the dusk act gets real long shadows across the valley and real orange light. Morning looks like morning.
- **Imagery:** darkened and desaturated by default ("night ops"), with a toggle to natural colour. Optional glowing elevation contours (`Material` ElevationContour, every 10 m) to make terrain legible. Terrain exaggeration slider 1–4×, labelled honestly.
- **Sensors:** masts as thin light pillars with a slow "listening" ring pulse. A destroyed sensor flickers out and turns ash grey.
- **Lines of bearing:** light rays shot from the mast along the measured bearing (a ~300 ms travelling pulse, fading over 3 s), coloured by signal class, with brightness scaled by SNR. When the path is non-line-of-sight, the ray looks fainter and noisier.
- **Fixes:** holographic error ellipses that ripple in when created and decay.
- **Dead zones** (`MW.shadow`): translucent red drapes showing where a drone at the slider height (0–300 m) is invisible to that receiver. This is the "behind the ridge" visual and must look stunning.
- **Truth objects:** crisp vector glyphs by kind (quad, delta wing, flock, operator, emitter) with a velocity tick and a gradient trail. Hostiles get a slow halo pulse. The selected object gets a screen-space reticle with live readouts (alt AGL, speed, which receivers can see it right now).

## Information architecture
- **Top bar:** OASIS wordmark · scenario name · UTC clock with ms (large mono) · local time · sun elevation · wind vector · the mode switch · a ▶ PRESENT button.
- **Mode switch** (the conceptual heart, big, centred):
  - **OPERATOR**: only what sensors produced; no truth.
  - **GOD MODE**: truth only.
  - **DELTA**: both, plus white error lines from each fix to the truth with distance labels.

  Switching plays a 400 ms scan-line wipe across the globe.
- **Left rail:** layers (truth, rays per receiver, fixes, dead zones + height slider, contours, imagery style, island/globe, exaggeration) · legend · KEY MOMENTS (clickable, from `MW.events`).
- **Right rail:**
  - **FEEDS**, synced to the clock:
    - EO camera frame with a HUD overlay (reticle, timestamp, detection box)
    - IQ spectrogram with a sweeping cursor
    - satellite chip with zoom
    - microphone: play button plus a live WebAudio spectrum/waveform while the clock runs, seeking to stay in sync
  - **INSPECTOR** for the selected object:
    - type and side
    - received-power sparkline per receiver over time, with non-line-of-sight stretches dimmed so the ridge drop is obvious
    - fix error stats
  - **EVENT TICKER**: newest detections streaming in, colour-coded and capped.
  - **AUDIT**: `MW.audit` as a scorecard with huge numerals, e.g. "OASIS 10/10 · ONE-SHOT LLM 3/10". Each check is a PASS/FAIL chip with its value; expand for detail.
- **Bottom: a bespoke timeline** (not the stock widget look; style or replace it):
  - act bands (MORNING / DUSK)
  - event glyphs
  - per-receiver detection-density heat strips: RF2's strip visibly goes dark when it's occluded or destroyed
  - draggable playhead
  - speed chips 1× 5× 20× 60× 300×
- **⌘K command palette:** "jump 14:02", "follow mavic_1", "dead zones RF2 40 m", "operator mode", "present".
- **Keyboard:** Space play/pause, ←/→ ±10 s, [ ] speed, 1–9 key moments, G cycles modes, P presents, F follows the selection.

## PRESENT mode (the demo autopilot; build it with love)
A cinematic, narrated tour driven by `MW.events` plus these beats. Each beat sets the clock, flies the camera on a smooth eased spline, toggles the right layers, and shows a lower-third caption (title + one line of plain-English explanation + the key number). Advance with → or click; it auto-advances after ~20 s; Esc exits.
1. **One world, real terrain**: slow orbit of the island slab at golden hour.
2. **Two receivers on real towers**: dead zones at 40 m.
3. **09:06:39Z, Sentinel-2A passes**: the satellite feed shows the Shahed's colour-fringe smear.
4. **14:02:07Z, the brief's own example**: rays from RF1 and RF2 cross on the Mavic; DELTA reveals the truth a few hundred metres away.
5. **Behind the ridge**: RF2's ray dies while RF1 keeps tracking; the sparkline drops ~30 dB.
6. **Find the pilot**: rays on the controller's uplink cross on a man standing in a field.
7. **Jammed**: RF1's 2.4 GHz rays vanish while 868 MHz survives; the spectrogram floods.
8. **Invisible to radio**: a fiber-optic FPV with zero rays, while the microphone feed lights up.
9. **Sensor down**: the FPV hits RF2; the pillar flickers out; its density strip flatlines.
10. **Proof**: the audit scorecard against the one-shot LLM baseline.

## Process and quality bar
1. Start by loading the real `data.js` and printing a data summary to the console, so you understand the scenario before designing.
2. Build the globe and layers first, then the panels, then PRESENT mode.
3. **Iterate visually:** after each milestone, screenshot at 1440×900 and 1920×1080 (headless Chrome with SwiftShader, or your preview tool). Critique like a design director: alignment, rhythm, type scale, colour discipline, legibility over imagery. Fix, and repeat at least 3 times. The first version is never the one.
4. Keep the code modular and readable: `globe.ts`, `layers/*.ts`, `panels/*.ts`, `timeline.ts`, `present.ts`, `data.ts`.
5. **Deliver:**
   - the source
   - `npm run build` → `dist/`
   - a README with run instructions (`npx serve dist` next to a `data.js`)
   - 3 screenshots (DELTA mode at dusk, dead-zone view, audit card)
   - a 20-second screen recording of PRESENT mode if you can

The bar: a defence engineer should look at it and think it is a real product they would pay for, and a designer should want to steal it.
