# Five fixed replay scenarios

These YAML files contain fixed aircraft tracks, sensor placements, and response tracks. They use the same central-valley terrain tile, which is cached on this workstation; a new workstation may need to download it once. Rerunning a file changes neither its story nor its seed. All protected sites and events are fictional. A site being "reached" means the aircraft crossed the simulation's site boundary; no damage is estimated.

| Scenario | Aircraft | Response | Fictional site | Planned result |
| --- | --- | --- | --- | --- |
| `01-shahed-power` | 3 Shahed-type | JEDI | Power station | 1 intercepted, 2 reach site |
| `02-decoy-water` | 2 Shahed-type, 2 Gerbera | Octopus | Water works | 2 intercepted, 2 reach site |
| `03-recon-power` | 2 Shahed-type, 2 Orlan-10 | Generic interceptor | Power station | 1 intercepted, 1 reaches site; both recon aircraft turn away |
| `04-low-fpv-water` | 2 analog FPV, 2 fiber FPV | JEDI | Water works | 2 intercepted, 2 reach site |
| `05-lost-contact-hospital` | Mavic reconnaissance, fiber FPV | JEDI response misses | Hospital | Neither reaches site; fiber FPV stops 0.8 km short |

From the repository root, generate one replay and serve it:

```sh
uv run python run_showcase.py 01-shahed-power --serve
```

Open `http://localhost:8765/dashboard/`. Choose any of the five names in the table. To generate and browse all five from one local page:

```sh
uv run python run_showcase.py all --serve
```

Open `http://localhost:8765/` and select a replay. Omit `--serve` to generate all five without starting the local server.

Each run writes `out/showcase/<name>/` with truth, sensor records, answer keys, an audit, `summary.json`, and a self-contained `dashboard/`. The runner compares the actual interception and site-boundary counts with the planned result and stops on a mismatch. The dashboard's **Key Moments** list shows computed interceptions, site reaches, and misses; clicking one jumps to that time. The run is deterministic from its checked-in YAML and seed.

Current module limits: radar and C2 sensor implementations are absent, so the runner skips their records while retaining their map markers. Satellite texture lookup also needs network access; the dashboard falls back to map tiles when it is unavailable. The latest local audits passed every check for scenarios 3 and 5; scenarios 1, 2, and 4 have RF audit failures recorded in their `audit.json` files. These are sensor-model findings, not outcome mismatches.
