# OASIS console handoff

Branch: `dashboard-ui`. This is the standalone Cesium/Vite OASIS console from `docs/ui-prompt.md`, including the Night Glass art direction from `docs/ui-prompt-v2.md`: full-bleed terrain, floating controls, six analysis tabs, Cinema, a skippable opening and ten PRESENT chapters. The branch includes the demo data, screenshots, browser checks and this handoff.

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

The browser checks cover the current layout, opening, Cinema, satellite detail, imports, missing data, audio, keyboard controls, all ten PRESENT chapters and responsive layouts. They serve the production build under a nested URL to verify relative asset paths.

## Where to edit

- `dashboard/index.html` and `dashboard/src/styles.css`: layout, type and controls.
- `dashboard/src/globe.js`, `layers/`: terrain, camera, truth, RF, fixes and dead zones.
- `dashboard/src/panels/`: feeds, inspector and audit.
- `dashboard/src/main.js`, `state.js`, `timeline.js`, `present.js`: replay and interactions.
- `dashboard/src/data.js`: strict input validation; never execute dropped JavaScript.
- `dashboard/scripts/export_data.py`: package an existing `out/ros-valley/` run with `npm run data:export`.

The product name is OASIS. Keep `window.MW`, relative asset paths and Vite `base: './'` for data and static-deployment compatibility. Audit scores and missing observations must come from the supplied dataset. `demo.zip` is a frozen handoff snapshot; refresh it deliberately when changing the demo data.

## Live preview

- HTTPS: https://<machine>.<tailnet>.ts.net:8444/
- DNS-independent tailnet fallback: http://<tailnet-ip>:8080/

Both require access to the team's tailnet. The current Mac deployment is a background static server managed by launchd, serving `../mw-dashboard-ui/dist/` from this branch's worktree. Rebuild in that worktree to update these URLs. See the root README for start/stop instructions. A local build does not deploy to another machine automatically.

## Current limits

- The frozen audit is 9 PASS, 0 FAIL, 1 SKIP. The one-shot baseline and timestamped microphone media are absent; the UI reports those absences.
- The real Sentinel backdrop is historical context; timestamped satellite observations are separate feed images.
- Relief exaggeration is visual only. Height and signal readouts stay in physical units.
- Rendering sleeps after a finite idle drift. The 60 fps target still needs a physical-device benchmark; automated checks use SwiftShader.
- `main` also contains simulator/backend work. Keep UI changes on a branch from `origin/dashboard-ui`; merge backend updates deliberately.
