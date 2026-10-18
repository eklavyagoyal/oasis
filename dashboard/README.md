# OASIS console handoff

Branch: `dashboard-ui`. This is the standalone Cesium/Vite console from `docs/ui-prompt.md`, with the Night Glass art-direction work from `docs/ui-prompt-v2.md` in progress. The first pushed checkpoint includes the working replay, all panels and PRESENT mode, local Sentinel-2 terrain imagery and relief controls. Further visual changes will follow on the same branch.

## Start immediately

From the repository root, with Node 20.19+ or 22.12+:

```sh
git fetch origin
git switch -c dashboard-friend origin/dashboard-ui
npm ci
unzip -o dashboard/demo.zip -d dashboard/public
npm run dev
```

The frozen synthetic Ros valley demo is included in `demo.zip`: `data.js`, the baked terrain texture and all referenced media. No simulation, API keys or Python environment are needed for this UI workflow. Cesium assets are copied locally by `predev` / `prebuild`. Google Fonts and optional online basemaps need internet; the default Sentinel texture is local.

```sh
npm test
npm run build
npx playwright install chromium
npm run test:browser
```

The existing browser checks also cover imports, missing data, audio, keyboard controls and responsive layouts. Some expectations describe the v1 panel arrangement and will be updated alongside the v2 layout.

## Where to edit

- `dashboard/index.html` and `dashboard/src/styles.css`: layout, type and controls.
- `dashboard/src/globe.js`, `layers/`: terrain, camera, truth, RF, fixes and dead zones.
- `dashboard/src/panels/`: feeds, inspector and audit.
- `dashboard/src/main.js`, `state.js`, `timeline.js`, `present.js`: replay and interactions.
- `dashboard/src/data.js`: strict input validation; never execute dropped JavaScript.
- `dashboard/scripts/export_data.py`: package an existing `out/ros-valley/` run with `npm run data:export`.

The product name is OASIS. Keep `window.MW`, relative asset paths and Vite `base: './'` for data and static-deployment compatibility. Audit scores and missing observations must come from the supplied dataset. `demo.zip` is a frozen handoff snapshot; refresh it deliberately when changing the demo data.

## Live preview

- HTTPS: https://eklavyas-macbook-pro.tailbc1933.ts.net:8444/
- DNS-independent tailnet fallback: http://100.79.203.26:8080/

Both require access to the team's tailnet. The current Mac deployment is a background static server managed by launchd. See the root README for start/stop instructions. A local build does not deploy to another machine automatically.
