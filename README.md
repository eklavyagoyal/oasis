# OASIS

Synthetic aerial defence scenarios over real Ukrainian terrain: ground truth, the records each sensor produced, and an answer key linking observations to their sources.

The static **Mirror World console** implements [the UI brief](docs/ui-prompt.md) with CesiumJS 1.124 and Vite. It opens in Delta mode at 14:02:07 UTC, showing the real Ros valley output already available in this workspace.

For an immediate frontend setup with the included demo, see [the dashboard handoff](dashboard/README.md).

## Run the console

Requires Node 20.19+ or 22.12+ and a browser with WebGL2. Use a local HTTP server, not `file://`.

```sh
npm install
npm run data:export
npm run dev
```

Open the address Vite prints. `data:export` requires the repository's Python environment (`uv sync`), existing `out/ros-valley/` output, and its simulation DEM cache. It reads those files and produces `dashboard/public/data.js` plus referenced media. It does not run the simulation or manufacture missing observations. If the DEM cache is absent, the existing terrain loader retrieves Copernicus data with its bounded network timeout/retry settings.

If you already have a dashboard dataset, put `data.js` in `dashboard/public/` and its media at the relative paths recorded in `MW.media`; skip `data:export`. The page loads `./data.js` before its application bundle. The console remains usable as a scenario loader when no dataset is installed.

```sh
npm run build
npx serve dist
```

`dist/` is the complete static site: `index.html`, `data.js`, `sensors/`, bundled application assets, and local Cesium assets/workers. It also works under a nested URL. To replace the deployed scenario, replace `dist/data.js` and its referenced media. Rebuilding restores the dataset from `dashboard/public/`.

No API key, ion token, geocoder, Bing imagery, or Google tiles are used. Public Esri imagery is the default; the **BASEMAP** button switches to OpenStreetMap. Google Fonts and imagery need internet access. Fonts have local fallbacks; imagery failure is surfaced while the DEM remains available.

### Tailscale deployment on this Mac

Open [the deployed console](https://eklavyas-macbook-pro.tailbc1933.ts.net:8444/) from a device connected to the same tailnet. Tailscale Serve runs in the background and proxies HTTPS port 8444 to the static `dist/` server on `127.0.0.1:4173`.

If a client cannot resolve the MagicDNS hostname, [the IP fallback](http://100.79.203.26:8080/) serves the same build through a tailnet-only TCP forwarder. Use `http://` for this endpoint; the device-to-device transport is encrypted by Tailscale, without browser TLS. To restore the HTTPS hostname, enable **Use Tailscale DNS settings** on the affected client and check its browser's DNS configuration. An HTTP reverse proxy requires the hostname, so the IP fallback deliberately uses `--tcp`.

The server is managed by `~/Library/LaunchAgents/com.mirrorworld.console.plist`, so disconnecting SSH does not stop it. It starts when this macOS user logs in; the Mac must remain awake and connected to Tailscale. Server output is in `~/Library/Logs/MirrorWorld/console.log`. Run `npm run build` to update the served files, then refresh the browser.

To stop this deployment:

```sh
tailscale serve --https=8444 off
tailscale serve --tcp=8080 off
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.mirrorworld.console.plist
```

To start it again:

```sh
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.mirrorworld.console.plist
tailscale serve --bg --https=8444 http://127.0.0.1:4173
tailscale serve --bg --tcp=8080 tcp://127.0.0.1:4173
```

## Use the console

- **Operator:** recorded bearings and position fixes. Truth objects, answer-key associations, shadow overlays, and object-specific density are hidden. Click an amber fix to inspect its reported position and ellipse.
- **God mode:** sampled truth tracks and physical sensor sites. Sensor observations and feed images are hidden.
- **Delta:** both layers, with error connections to truth at the fix's own timestamp. An older selected-object fix can remain visible for 60 seconds and is labelled with its age.
- **Terrain dead zones:** enable the layer, choose a receiver, and set the height from 0–300 m AGL. Red indicates the supplied shadow raster's minimum visible height exceeds the selected height.
- **Density:** switch between all recorded signals and the selected object. The label states the active scope. This matters because RF2 can lose the Mavic while still detecting other emitters.
- **Feeds:** select EO, IQ/RF, satellite or audio. Only the selected channel's media is loaded. The latest capture at or before the playhead is held with an age label; future captures are never shown. The expand button opens an image at full size. Audio requires an explicit click, uses WebAudio decoding, follows replay speed, and resynchronizes after seeking.
- **Audit:** supplied PASS/FAIL/SKIP checks and baseline scores, with expandable evidence. Missing audit results stay explicitly unscored.
- **Present:** ten event-led beats with camera flights, layer changes and captions; the first beat slowly orbits the island. Each beat advances after 20 seconds. Optional **VOICE ON** uses the browser's speech synthesis. The final scorecard waits for you; exiting restores the prior replay state.

| Key | Action |
| --- | --- |
| Space | Play/pause |
| ← / → | Seek −/+10 seconds; previous/next beat during PRESENT |
| [ / ] | Lower/higher playback speed |
| 1–9 | First nine dataset key moments |
| G | Cycle Operator / God / Delta |
| P | Enter/exit PRESENT |
| F | Follow/unfollow the selected truth object |
| Esc | Exit PRESENT or close a dialog |
| ⌘K / Ctrl+K | Open command palette |

Command examples: `jump 14:02`, `jump 14:14:40`, `follow mavic_1`, `dead zones RF2 40 m`, `operator mode`, `present`. Jump commands use UTC on the scenario start date. The secondary clock shows Europe/Kyiv time.

Drag a `data.js` or JSON file onto the page, or use **LOAD SCENARIO**. Imported files must contain strict JSON, optionally wrapped in `window.MW = …;`. They are parsed and validated without executing JavaScript. A rejected import leaves the current world intact. Media must already be served at its recorded relative paths; a dropped file does not grant access to adjacent files on disk. External media URLs, executable imports, and path traversal are rejected. Files are limited to 100 MB.

## Data fidelity and current availability

The packaged local run contains **15 objects, 10 configured sensors, 25,092 RF records, 1,300 fused fixes, four IQ PNGs, and a 601 × 601 DEM**. The exported audit snapshot reports **6 PASS, 1 FAIL, 3 SKIP**; the scorecard displays **6/10**, including skipped checks in the denominator. The reported failure is the range-law check; the console preserves it. There is no one-shot baseline. Camera frames, microphone recordings, satellite chips, Remote ID, telemetry, and civilian reports are absent from the packaged output. Missing feeds and baseline scores remain explicit; no demo observations or scores have been substituted.

The exporter adapts the available repository output to the brief:

- Input truth is 2 Hz; the export retains one sample per second plus each object's final sample. Times are not assumed to be integer seconds.
- `power_dbm`, `bearing_deg`, and the fused CSV's ellipse columns become the documented compact arrays. Empty fix errors become JSON `null`.
- Older IQ output has no `media.csv`; its PNG timestamps come from the associated SigMF capture metadata. New `media.csv` files are supported automatically.
- Shadow rasters use `World.min_visible_agl` on the same DEM, sampled at about 150 m. The render terrain retains the original 30 m grid.
- The longest computed RF2/Mavic terrain-hidden interval in this existing output starts at **t=18983.5** and lasts **461 seconds**, differing from the shorter illustrative interval in the brief. RF2 destruction is **t=20310.5**. Key moments preserve the generated evidence.
- There is no supplied Sentinel pass event. PRESENT uses the brief's t≈699 story position while explicitly reporting the missing satellite capture.

Terrain is sampled bilinearly with clamped edges. Source rows run south-to-north; Cesium heightmap tile rows are reversed to north-to-south. The island is clipped to the scenario area. Truth altitude and terrain share the source DEM datum without geoid conversion; truth entities use `HeightReference.NONE`. Terrain exaggeration changes only displayed terrain and is labelled whenever it differs from 1×. Full-globe mode continues clamping the supplied DEM outside its bounds; it is geographic context, not a global elevation dataset.

Bearings show measured azimuth projected above the DEM for visibility; they do not encode range or elevation. Rays use a three-second window and fixed primitive pools, with a 300 ms travelling pulse. Fix ellipses retain their reported axes and orientation. Selected-object power plots dim NLOS records and never extrapolate gaps. The IQ cursor is a replay indicator over a recorded image, not an additional RF measurement. Solar direction follows Cesium's scenario clock; the displayed elevation is a geometric approximation, and the warm tint is a display treatment. Camera HUD reticles do not invent detection boxes absent from the input.

Cesium's [custom heightmap provider](https://cesium.com/learn/cesiumjs/ref-doc/CustomHeightmapTerrainProvider.html) has no vertex-normal channel. The console enables terrain shadow casting and receiving, but its lighting is not a replacement for the simulation's physics.

## Verification and deliverables

```sh
npm test
npx playwright install chromium
npm run build
npm run test:browser
```

The data tests cover interpolation, lifetimes, index/array validation, JSON-only imports, media paths, audit shape, and the actual export. Browser tests serve the production build at `/nested/console/` and exercise mode separation, commands, keyboard replay, all ten presentation beats, scenario replacement, missing feeds/images, WebAudio, and the audit UI. Test-only audio/audit fixtures are never included in the delivered dataset.

Three visual iterations were captured at both 1440×900 and 1920×1080; layout checks also cover 1280×720 and 390×844. See [the review notes](docs/ui-review/README.md). The checks use headless Chromium/SwiftShader; **60 fps on a physical MacBook Air has not been benchmarked**. Primitive pools, binary time-window searches, sampled positions and paused rendering limit work, but the hardware target still needs a device run.

- [Delta at dusk](docs/screenshots/delta-dusk.png)
- [Terrain dead zones](docs/screenshots/dead-zones.png)
- [Audit state](docs/screenshots/audit.png)
- [20-second PRESENT recording](docs/screenshots/present.mp4)

Source modules live under `dashboard/src/`: `globe.js`, `data.js`, `layers/`, `panels/`, `timeline.js`, `present.js`, and `commands.js`. The exporter and verification/capture scripts are under `dashboard/scripts/`. Generated datasets, dependencies and `dist/` are ignored by git.

## Generate simulation output

The existing Python pipeline is unchanged:

```sh
uv sync
uv run python -m mirrorworld run scenarios/ros-valley.yaml --skip-missing
```

See [CONTRACT.md](CONTRACT.md) for sensor output and answer-key conventions.
