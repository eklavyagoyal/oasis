# OASIS implementation contract

## Locked scope
- Branch: `oasis-sim`, based on latest `origin/main` including Eklavya's Night Glass dashboard. Never push main.
- Flow: cloned OSIRIS entry, rebranded OASIS with Ukraine highlighted -> seed dialog -> Eklavya's existing simulation screen -> end summary.
- Browser seed engine for this iteration. Its tracks/detection/HP are synthetic simplified simulation, not real recordings or the Python physics pipeline.
- Preserve existing dashboard layout, assets, replay imports and controls. No second simulation UI.
- No testing during implementation. Final production build only at end; user handles local testing. No added test code.
- Incremental commits and pushes. Parent owns git, shared integration, browser, package.json and Vercel settings.

## Parallel owners
| Owner | Files | Deliverable |
|---|---|---|
| Entry | `dashboard/src/entry.js`, `dashboard/src/entry.css` | OSIRIS-derived full-screen entry + seed dialog, no simulation screen |
| Engine | `dashboard/src/game/*.js`, `ukraine.json`, excluding CONTRACT.md; `docs/DATA-PIPELINE.md` | validated config, world generation, MW adapter, saved records, recorded overlay |
| Data audit | `dashboard/src/panels/{feeds,inspector,audit}.js`, `dashboard/src/present.js`, `docs/DATA-REALITY.md` | trace current readings to actual source; plain labels; hide missing feeds; honest provenance report |
| Parent | main.js, index.html, global CSS, package/config, git, browser | attach entry and generated datasets to Eklavya's original screen |

All child progress goes to ignored `.agent-notes/{entry,engine,data}.md` in each worktree. No other reports, tests, installs, commits or pushes by children. Exactly one browser owner: parent. Children never use browser tools or start servers.

## Entry API
`createEntry({ onGenerate, onReplay, onExport, getCounts })` returns `{ show(), hide(), destroy() }`.
- `onGenerate(cfg, progress)` resolves after generated data has opened in the existing dashboard; reject shows error in seed dialog. `progress(message)` updates visible generation status.
- cfg: `{worldSeed,scenarioSeed,tileKm,durationS,drones,mix,entry,defence,radar,acoustic}`. Seeds integers 0..4294967295; tileKm 10/16/20; durationS 3600/21600/86400; drones 1..30; entry random/N/E/S/W. DEFAULTS in seed.js.
- Plain DOM and source-derived OSIRIS styles/map. May import `maplibre-gl` (parent installs). No React/Next app. Original screen remains mounted under entry overlay.
- Root `#oasis-entry`, form `#seed-form`, actions `#enter-simulation`, `#replay-hero`, `#generate-world`; accessible modal, keyboard focus, reduced-motion.
- Copy OASIS only, no live intelligence claims, donations/crypto or decorative fake counters. Real UTC; real IndexedDB counts. Ukraine inclusive outline from game/world.js.

## Engine API
`generateWorld(cfg, { world = null, onProgress = () => {} } = {})` from `game/generate.js` resolves `{dataset, world, run}`.
- `world` is a persisted full snapshot: id, seed, exact grid, site, tile metadata, original fixed assets, provenance. Supplying it must keep terrain and fixed assets exactly unchanged; scenario options change moving assets only. Save world/run locally; report storage failure without hiding generated run. No silent flat-terrain replacement.
- `dataset` must pass existing `validateData` unchanged. `game` contains `{world: originalAssets, cfg, tile, record}`.
- `toMW` object tracks, fixed sites/response objects, sensors and events all derive from actual recording. Do NOT invent RF angles, signal power, uncertainty or physics audit; rf/fixes/media empty when unavailable. Clearly mark provenance as browser approximation, range+LOS, HP invented.
- Use existing baked terrain when explicitly selected; new Ukraine worlds use real Terrarium terrain with provenance/credits, no false 30 m precision claims. Every procedural asset flagged synthetic, OSM location is not a real military sensor.
- `createRecordedLayer(globe,data)` from `game/layer.js` returns `{ update(t, {coverage,links,labels}), destroy() }`; draw recorded fixed HP, aircraft/interceptors, detections and collisions at replay time. Must support seeking backward, not depend on live mutable simulation state. No phantom pending objects.
- IDs cannot silently collide when fixed-world options change. Preserve full snapshot for deterministic reruns and later export.

## Parent integration
- main.js start(data, {skipOpening}) still renders original dashboard; generated datasets add recorded overlay only. Capture hero dataset before switching.
- Entry shown immediately, no auto-dismiss. REPLAY HERO opens original replay without old timed intro. ENTER SIMULATION opens seed dialog.
- New world action opens entry/seed dialog. Run again keeps world snapshot and increments scenario seed. Export downloads IndexedDB bundle; end summary uses recorded counts, no fabricated metrics.
- Keep feed and audit tabs honest on generated worlds: no sensor data, no audit, no RF measurements supplied. Disable unavailable controls instead of creating plausible numbers.

## Push order
1. Latest base + recovered engine and contract, no UI replacement.
2. OSIRIS-derived entry and seed screen connected to original replay.
3. Generation, recorded playback, storage, same-world rerun, summary, provenance corrections.
4. Final build/fixes and static Vercel config.
