# OASIS browser data pipeline (`oasis-sim`)

This contract describes the browser simulator export on branch `oasis-sim`. It is a full world snapshot plus run records—not a terrain summary and not a Python RF recording.

## Export and persistence

- Browser IndexedDB database `oasis`, version 1, has `worlds` and `runs` stores; runs have a `worldId` index.
- Export envelope: `{ schema: "oasis.export/1", exported_at, worlds: [World], runs: [Run] }`.
- `worlds` and `runs` are arrays of complete records. Preserve the original JSON on ingestion; do not infer missing measurements.
- World ID format: `w{worldSeed}-{tileKm}km-{terrainMode}-d{defence?1:0}r{radar?1:0}a{acoustic?1:0}-{fingerprint}`. The final lowercase hex fingerprint hashes terrain, fixed assets, site, and fixed flags; the ID also binds requested tile size and terrain mode. Run ID is `{worldId}/s{scenarioSeed}-{Date.now()}`; the timestamp means repeated seeds may have different run IDs.

## World snapshot

A `World` is `{ id, worldSeed, cfg, site: {lat, lon}, tile, terrain, assets, provenance, created_at }`.

- `cfg` is the full generation config. Fixed-world identity is determined by `worldSeed`, `tileKm`, `terrainMode`, `defence`, `radar`, and `acoustic`.
- `tile` contains its centre (`lat`, `lon`), bounds (`west`, `south`, `east`, `north`), `size`/`size_m` in metres, `sizeKm`/`size_km` in km, and `cosLat`.
- `terrain` is the full DEM grid and metadata (bounds, `nx`, `ny`, elevation array `h`, and available source/texture metadata), not just min/max. `assets` is the full fixed-asset snapshot, including procedural and any mapped assets. Keep provenance and `real`/`synthetic` distinctions.
- World seed drives the selected site (live terrain), seeded placement of fixed assets, and world-generation randomness. A saved-world rerun reuses the exact terrain/assets; it cannot change the fixed-world identity options above.
- `scenarioSeed` drives moving entities (types, waves, routes, launch times) and combat dice. Reproduction also requires the same world snapshot, remaining `cfg`, and code/data version; seed equality alone is insufficient.

## Run record (`schema: "oasis.run/1"`)

`record()` returns `{ id, worldId, schema, meta, cfg, tile, world, drones, tracks, detections, collisions, damage, events, summary }`.

- `meta` includes run ID, world ID, start-time anchor, creation time, provenance, and model label. `tile` has centre/bounds and `size_m`. `world` is the fixed assets' end-of-run state: `{id,type,cat,side,name,real,x,y,z,lat,lon,hp,hp_max,alive,state,ammo}`.
- `drones` describes each moving attacker: `{id,type,wave,entry,target,t0,state,first_detected_t,detected_by,end_t,agl_cruise,speed,path}`. `path` is a list of local `[x,y]` waypoints. `summary` contains outcomes, defence counts, detection time and record counts.

| Array | Row shape | Meaning |
|---|---|---|
| `tracks` | `{t,id,x,y,z,lat,lon,alt,agl,hp,state}` | 1 Hz truth samples for flying drones and interceptors, plus terminal positions. |
| `detections` | `{sensor,target,t_start,t_end}` | Per-sensor/per-target contact interval; closes on loss of contact or run end. |
| `collisions` | `{t,a,b,kind,x,y}` | Impact, jam-crash, debris, or interceptor hit/miss. |
| `damage` | `{t,target,by,hp_before,hp_after,destroyed}` | Abstract HP changes. |
| `events` | `{t,kind,text,...}` | Event log; optional detail includes `id`, `by`, `target`, `p`, `roll`, and `hit`. |

## Time, coordinates, units

- `t`, `t0`, interval endpoints and event times are seconds since simulation start. Simulation steps at 0.5 s; scans/truth tracks are recorded at 1 Hz. `meta.start` is a deterministic clock anchor, not an observed timestamp.
- Local `x`, `y`, `z`, waypoints and collision `x`,`y` are metres; x is east and y north from the tile centre. `lat`,`lon` are WGS84 degrees (track coordinates rounded to 1e-6).
- Track `z` and `alt` are metres MSL; `agl`/`agl_cruise` are metres AGL. `speed` is m/s. `hp`, `hp_max`, and damage values are abstract game HP, not physical units. `p`/`roll` are unitless probabilities/dice values.
- Seeds are unsigned 32-bit integers: 0–4,294,967,295 inclusive.

## Ingestion recommendations (Supabase/Postgres)

- Keep `worlds` and `runs` parent rows, with child tables for drones, tracks, detections, collisions, damage and events; retain source JSON in `jsonb` (or object storage for the full terrain grid) so no fields are lost.
- Use `BIGINT` for both seeds, with `CHECK (seed BETWEEN 0 AND 4294967295)`; PostgreSQL `integer` cannot represent the full uint32 range. Keep IDs as text and `world_id` as a foreign key.
- Make import idempotent on exported IDs: upsert worlds by `worlds.id`, runs by `runs.id`, and replace/upsert that run's child rows transactionally. Do not make `(world_id, scenario_seed)` unique: run IDs include a timestamp and same-seed runs can be distinct exports. If child rows need keys, include stable source-array ordinals.
- Batch large track inserts; do not split or downsample the preserved source record during ingestion. Partition model evaluation by `worldId` (train/test worlds), not by run, to avoid map leakage.

## Model boundary and partner handoff

- Browser detections are synthetic range + terrain line-of-sight rules (acoustic ignores terrain screening); outcomes use simplified seeded probabilities and abstract HP. The browser export does **not** generate RF bearings/angles, SNR, power, fixes, media, or measured sensor streams. `toMW()` marks these as unavailable and emits empty RF/fix/media collections; zero weather values are schema placeholders, not observations.
- Physics-grade RF simulation data is produced by the separate Python pipeline under `mirrorworld/` (sensor outputs plus answer keys/fused products), not by this browser export. Keep the two sources and their provenance distinct; neither should be called field-measured without evidence.
- The ingestion/data-pipeline partner can implement against this export contract now; no dependency on UI completion, and no need to edit `entry`, `main`, or `flow`.
