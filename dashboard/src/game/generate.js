import { CAT, DEFAULTS, makeTile, populate } from './seed.js';
import { randomSite, loadTerrain, loadFeatures, TERRAIN_SOURCE, OSM_SOURCE } from './world.js';
import { makeScenario } from './scenario.js';
import { createSim, runToEnd, record } from './sim.js';
import { worldId, runId, findWorld, getWorld, saveWorld, saveRun } from './store.js';
import { toMW } from './toMW.js';
import { validateData } from '../data.js';

function config(input) {
  const cfg = { ...DEFAULTS, durationS: 3600, terrainMode: 'live', start: '2026-11-04T06:00:00Z', ...input };
  for (const key of ['worldSeed', 'scenarioSeed']) {
    if (!Number.isInteger(cfg[key]) || cfg[key] < 0 || cfg[key] > 4294967295) throw new Error(`${key} must be an unsigned 32-bit integer.`);
  }
  if (![10, 16, 20].includes(cfg.tileKm)) throw new Error('Tile size must be 10, 16 or 20 km.');
  if (![3600, 21600, 86400].includes(cfg.durationS)) throw new Error('Duration must be 1, 6 or 24 hours.');
  if (!Number.isInteger(cfg.drones) || cfg.drones < 1 || cfg.drones > 30) throw new Error('Drone count must be 1 to 30.');
  if (!['random', 'N', 'E', 'S', 'W'].includes(cfg.entry)) throw new Error('Invalid entry direction.');
  if (!['live', 'baked'].includes(cfg.terrainMode)) throw new Error('Invalid terrain mode.');
  if (!Array.isArray(cfg.mix) || !cfg.mix.length || cfg.mix.some((id) => CAT[id] !== 'attackers')) throw new Error('Choose one or more supported attacker types.');
  for (const key of ['defence', 'radar', 'acoustic']) if (typeof cfg[key] !== 'boolean') throw new Error(`Invalid ${key} option.`);
  if (!Number.isFinite(Date.parse(cfg.start))) throw new Error('Invalid simulation start time.');
  return cfg;
}

function fingerprint(value) {
  let hash = 2166136261;
  for (const char of JSON.stringify(value)) hash = Math.imul(hash ^ char.charCodeAt(0), 16777619);
  return (hash >>> 0).toString(16);
}

export async function generateWorld(input, { world: supplied = null, onProgress = () => {}, bakedData = null } = {}) {
  const cfg = config(input), warnings = [];
  let world = supplied, fresh = false;
  if (world) {
    for (const key of ['worldSeed', 'tileKm', 'terrainMode', 'defence', 'radar', 'acoustic']) {
      if (world.cfg[key] !== cfg[key]) throw new Error(`Same-world rerun cannot change ${key}. Generate a new world instead.`);
    }
  } else {
    try { world = await findWorld(cfg); }
    catch (error) { warnings.push(`Saved-world lookup unavailable: ${error.message}`); }
  }
  if (!world) {
    fresh = true;
    let site, terrain;
    if (cfg.terrainMode === 'baked') {
      if (!bakedData?.terrain) throw new Error('No real baked demo terrain is available. Retry terrain loading.');
      terrain = structuredClone(bakedData.terrain);
      site = { lat: bakedData.scenario.area.lat, lon: bakedData.scenario.area.lon };
      onProgress('Using the real baked demo-sector terrain, not a random Ukraine tile.');
    } else {
      site = randomSite(cfg.worldSeed);
      onProgress(`Loading real elevation terrain at ${site.lat.toFixed(4)}, ${site.lon.toFixed(4)}…`);
      terrain = await loadTerrain(site.lat, site.lon, cfg.tileKm);
    }
    const tile = makeTile(terrain, cfg, site);
    let features = [], osmStatus = 'not_requested', osmError = null;
    if (cfg.terrainMode !== 'baked') {
      onProgress('Loading mapped OpenStreetMap infrastructure…');
      try { features = await loadFeatures(tile); osmStatus = 'available'; }
      catch (error) { osmStatus = 'unavailable'; osmError = error.message; warnings.push(`${error.message}; fixed assets are procedural.`); }
    }
    onProgress(`Placing fixed assets; ${features.length} mapped features available.`);
    const assets = populate(tile, cfg, features);
    const tileInfo = { lat: tile.lat, lon: tile.lon, cosLat: tile.cosLat, west: tile.west, south: tile.south, east: tile.east, north: tile.north, size: tile.size, size_m: tile.size, sizeKm: tile.sizeKm, size_km: tile.sizeKm };
    const provenance = {
      terrain: cfg.terrainMode === 'baked'
        ? { name: 'Baked demo-sector elevation terrain', source: bakedData.provenance || {}, label: 'Real terrain; explicitly selected baked demo sector.' }
        : { ...TERRAIN_SOURCE, nx: terrain.nx, ny: terrain.ny },
      osm: { ...OSM_SOURCE, status: osmStatus, features: features.length, error: osmError },
    };
    const fp = fingerprint({ terrain, assets, site, cfg: { defence: cfg.defence, radar: cfg.radar, acoustic: cfg.acoustic } });
    world = { id: worldId(cfg.worldSeed, cfg.tileKm, { ...cfg, fingerprint: fp }), worldSeed: cfg.worldSeed, cfg: { ...cfg }, site, tile: tileInfo, terrain, assets, provenance, created_at: new Date().toISOString() };
    if (Math.abs(tile.sizeKm - cfg.tileKm) > 0.01) warnings.push(`Baked terrain limits this tile to ${tile.sizeKm.toFixed(2)} km, not ${cfg.tileKm} km.`);
  } else onProgress('Reusing the exact saved terrain and fixed assets.');
  const tile = { ...world.tile, grid: world.terrain };
  onProgress('Computing seeded trajectories, detection intervals and outcomes…');
  const drones = makeScenario(tile, world.assets, cfg);
  const simulation = runToEnd(createSim({ tile, world: world.assets, drones, cfg }));
  const run = record(simulation, { id: runId(world.id, cfg.scenarioSeed), worldId: world.id, start: cfg.start, created_at: new Date().toISOString(), provenance: world.provenance, model: 'browser approximation; not physics-grade sensor measurements' });
  const dataset = validateData(toMW(run, world, cfg));
  dataset.game.tile.grid = world.terrain;
  onProgress('Saving the full world snapshot and run to this browser…');
  try {
    if (fresh && !await getWorld(world.id)) await saveWorld(world);
    await saveRun(run);
    onProgress('World and run saved locally. Opening the simulation.');
  } catch (error) { warnings.push(`Local save failed: ${error.message}. Keep this page open and export the current run.`); }
  return { dataset, world, run, warnings };
}
