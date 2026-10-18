# OASIS console: art-direction pass (v2)

You built a working console. Now make it look like a product a defence buyer would pay seven figures for, and that a design team would want to steal. Today it reads as "generated dashboard": every surface the same dark box, everything outlined, mono text everywhere, equal weights, cyan-on-black, and a dead brown slab in the middle. This pass is **art direction, not features**. Keep every feature, the data contract, the keyboard shortcuts and PRESENT mode. Change how it looks, moves and feels. The product name is **OASIS** (wordmark everywhere; remove "Mirror World").

## Diagnosis of the current build (fix all of it)
1. **The 3D scene is the product, and it's the weakest part.** It's a flat brown tray with tiny labels and thin lines. The jury will stare at it for 4 minutes.
2. **Too much chrome.** Every panel is boxed, every section has a border, and the panels steal ~45% of the screen from the terrain.
3. **No typographic hierarchy.** It's mono everywhere and most text is the same size. Nothing is big, nothing is quiet.
4. **Colour has no discipline.** Accents are scattered, and the cyan/amber borders look like a template.
5. **Controls are browser-default or generic** (audio players, checkboxes, toggles).
6. **The motion is mechanical.**

## The new look: "Night Glass"
A calm, luminous instrument floating over a real landscape at dusk. Deep blue-black glass and warm-white type, with light used only where something happens.

**Palette.** Use CSS variables only, and colour carries meaning only.
```
--void:#06080B  --surface:#0B0E13  --glass:rgba(14,17,23,.56)  --glass-strong:rgba(14,17,23,.78)
--hairline:rgba(255,255,255,.08)  --inner-highlight:rgba(255,255,255,.06)
--text:#F4F1EA  --text-2:#A3A09A  --text-3:#6B6862
--accent:#6FF2C5   (system, selection, focus, primary action: the ONLY brand accent, ≤5% of pixels)
--signal:#FFC266   (RF energy: rays, spectrum, signal readouts)
--hostile:#FF5470  --friendly:#6AA8FF  --neutral:#8E96A3  --truth:#FFFFFF
--pass:#6EE7B7  --fail:#FF5470
```
- Glass panels use `backdrop-filter: blur(24px) saturate(160%)`, a 1px `--hairline` border, a 1px top inner highlight, and a 14px radius on floating cards (8px inside).
- Shadows are very soft (`0 24px 80px rgba(0,0,0,.45)`).

**Type** (Google Fonts):
- **Unbounded 600:** only the OASIS wordmark and hero numerals (the big clock, audit score, PRESENT chapter numbers). Tracking −0.02em.
- **Geist 400/500/600:** all UI text.
- **Geist Mono 400/500:** every number, time, coordinate and id, with `font-variant-numeric: tabular-nums`.
- **Scale:** 11 / 12 / 13 / 15 / 20 / 28 / 44 / 64. At most 3 sizes per panel.
- **Labels:** uppercase Geist 500, 10–11 px, letter-spacing 0.14em, `--text-3`. Body 13 px `--text-2`. Key values large in `--text`.

**Space:** an 8 px grid, 24 px outer margins, 16 px panel padding. Separate with space, not borders: a hairline divider at most, never boxes inside boxes.

**Motion:**
- Default easing `cubic-bezier(.16,1,.3,1)` at 240–420 ms. Panels enter with a 40 ms stagger (fade + 8 px rise).
- Numbers count to their new value. Nothing bounces. Honour `prefers-reduced-motion`.

**Controls:** custom-styled toggles, a segmented control and sliders in the palette. No default browser checkbox or audio UI anywhere: audio gets a play button plus a live waveform/spectrum canvas.

## The scene (where most of the effort goes)
- **Real ground.** `MW.terrain.texture` = `{src:"texture.jpg", west, south, east, north, credit}`. It's a baked Sentinel-2 true-colour image of exactly this area, already shaded by the simulation's own DEM.
  - Drape it with `SingleTileImageryProvider` over that rectangle and make it the default basemap.
  - Fall back to tiles only if `texture` is null.
  - Keep its credit visible: restyle the Cesium credits small and unobtrusive, but don't remove attribution.
- **Relief:** `scene.verticalExaggeration` 2.5 by default, labelled honestly ("relief ×2.5") with a slider 1–4. The ravines and the Ros valley must read in 3D.
- **Light:**
  - The real sun from the scenario clock (`enableLighting`, `SunLight`, atmosphere on, gentle fog). Dusk must look like dusk; the morning act like morning.
  - Add an HDR-ish bloom post-process kept subtle (bloom only bright emissive things: rays, fixes, hostile halos).
- **ISLAND mode** (default): the 16 km slab floats in the void.
  - A thin luminous rim in `--accent` at ~30% opacity.
  - A faint holographic grid plane far below with a soft glow pooling under the slab.
  - Outside the slab: near-black space with a hint of atmosphere.
  - A small orbit-on-idle (very slow) when not playing.
- **Objects:**
  - Crisp SDF/vector glyphs (quad, delta wing, fixed wing, flock, operator pin, emitter, mast) in billboards with a dark halo for legibility.
  - Trails are glowing gradient polylines that fade over 120 s.
  - Hostiles get a slow breathing halo. The selected object gets a screen-space bracket reticle and a leader-line callout (id, alt AGL, speed, which receivers see it right now).
  - Show at most ~6 labels at once by priority: selected > hostile > others. No label soup.
- **RF:**
  - Lines of bearing are glow polylines (`--signal`, or tinted by signal class) with a light pulse travelling outward from the mast on each detection, fading over 3 s.
  - Masts are thin vertical light pillars with a quiet "listening" ring. A destroyed mast flickers and dies to ash grey.
- **Fixes:** ground ellipses with a soft radial edge and a one-time ripple on creation. In DELTA mode, a thin white error line to the truth with a distance chip.
- **Dead zones:** a translucent `--hostile` drape with a contour edge, animated in when toggled. The "behind the ridge" beat must be one gorgeous picture.

## Layout
- The terrain is full-bleed. Everything else floats.
- **Top centre:** one glass "status pill": OASIS wordmark · scenario · big Geist-Mono UTC clock · the OPERATOR / GOD MODE / DELTA segmented control. Switching modes plays a light sweep across the terrain, and layers cross-fade.
- **Left:** a slim icon rail that expands into the Layers card. **Right:** the Feeds card stack (tabs: EO · IQ · SAT · AUDIO · AUDIT · INSPECTOR).
  - Feeds look like real monitors: the EO frame has a HUD (corner brackets, timestamp, detection box), the spectrogram has a sweeping time cursor, and the satellite chip has a zoom inset.
- **Bottom:** a slim 56 px timeline with act bands, event glyphs (hover → title), 2 px detection-density lines per receiver, a glowing playhead, and speed chips.
- **Cinema mode:** `H` hides all chrome. `P` = PRESENT.

## Signature moments (build these with care)
1. **Opening, ~6 s, skippable.**
   - A dark globe with a thin atmospheric rim.
   - Slow push toward Ukraine.
   - The sector's island lights up as the camera arrives.
   - A title card fades in: **OASIS** (Unbounded) / "ROS VALLEY · 4 NOV 2026 · ONE WORLD, EVERY SIGNAL".
2. **PRESENT chapters:**
   - A full-width lower third: a big chapter number (Unbounded), a 1-line title, a 1-line plain-English explanation, and one hero metric (e.g. "−30 dB behind the ridge", "7 PASS vs 1 PASS").
   - Eased camera flights, with only the relevant layers on.
3. **Audit card:** two huge numerals side by side, "OASIS 7/7" vs "ONE-SHOT LLM 1/4". Every check is a calm row with a PASS/FAIL chip and its value; expandable.

## Rules
- Keep the data contract, features, shortcuts, the static build (`base:'./'`) and no API keys.
- Escape every `data.js` string you render as HTML, or use `textContent`.
- Performance: 60 fps at 1440×900. Rays are pooled primitives. Pause rendering when idle.
- No lorem ipsum, no emoji, no gradients for decoration, no purple.
- Accessible: visible focus rings in `--accent`, text contrast ≥ 4.5:1.

## Process
1. **Screenshot first:** take screenshots of the current build at 1440×900 and 1920×1080 before you change anything.
2. **Order of work:** do the scene first, then the layout and type, then motion, then the signature moments.
3. **Critique loop:**
   - After each step, take screenshots and critique them like a design director: alignment to the 8 px grid, type sizes per panel, accent discipline, legibility over imagery, whether the terrain looks real.
   - Fix everything you find, and do at least 3 loops.
4. **Final check:** ask whether it looks like a real product a defence engineer would trust. If not, keep going.
5. **Deliver:** rebuild `dist/`, and save screenshots of DELTA at dusk, the dead-zone view, the audit card and the opening title card.
