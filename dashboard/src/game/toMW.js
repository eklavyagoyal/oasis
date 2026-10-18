import { CAT, toLL } from './seed.js';

const FIXES_EMPTY = () => Object.fromEntries(
  ['t', 'lat', 'lon', 'smaj', 'smin', 'orient', 'ce', 'cep50', 'cls', 'obj', 'err'].map((key) => [key, []]),
);
const sideOf = (side) => ({ hostile: 'hostile', friendly: 'friendly', civilian: 'neutral', neutral: 'neutral', unknown: 'unknown' })[side] || 'unknown';
const tileFrame = (tile) => ({ lat: tile.lat, lon: tile.lon, cosLat: Math.cos((tile.lat * Math.PI) / 180) });

function fixedObject(asset, frame, durationS) {
  const [lon, lat] = toLL(frame, asset.x, asset.y);
  const kind = CAT[asset.type] === 'structures' ? 'site' : 'response';
  return {
    id: asset.id,
    type: asset.type,
    kind,
    side: sideOf(asset.side),
    t: [0, durationS],
    lat: [lat, lat],
    lon: [lon, lon],
    alt: [asset.z, asset.z],
    altitude_reference: 'MSL',
    synthetic: asset.synthetic !== false,
    real: asset.real === true,
    ...(asset.name ? { name: asset.name } : {}),
    ...(asset.source ? { source: asset.source } : {}),
  };
}

function movingObject(id, type, kind, side, records, extra = {}) {
  const ordered = records.filter((row) => row.id === id).sort((a, b) => a.t - b.t);
  const rows = [];
  for (const row of ordered) {
    if (rows.length && rows.at(-1).t === row.t) rows[rows.length - 1] = row;
    else rows.push(row);
  }
  if (!rows.length) return null;
  return {
    id,
    type,
    kind,
    side,
    t: rows.map((row) => row.t),
    lat: rows.map((row) => row.lat),
    lon: rows.map((row) => row.lon),
    alt: rows.map((row) => row.alt),
    agl: rows.map((row) => row.agl),
    hp: rows.map((row) => row.hp),
    state: rows.map((row) => row.state),
    altitude_reference: 'MSL',
    synthetic: true,
    ...extra,
  };
}

export function toMW(run, world, cfg) {
  const tile = world.tile;
  const frame = tileFrame(tile);
  const durationS = cfg.durationS;
  const objects = world.assets.map((asset) => fixedObject(asset, frame, durationS));
  for (const drone of run.drones) {
    const object = movingObject(drone.id, drone.type, 'drone', 'hostile', run.tracks, {
      wave: drone.wave,
      target: drone.target,
      synthetic: true,
    });
    if (object) objects.push(object);
  }
  for (const track of run.tracks) {
    if (objects.some((object) => object.id === track.id)) continue;
    if (track.id.startsWith('INT-')) {
      const object = movingObject(track.id, 'interceptor', 'response', 'friendly', run.tracks);
      if (object) objects.push(object);
    }
  }
  const terrainMode = world.cfg.terrainMode;
  const terrainLabel = terrainMode === 'baked'
    ? 'Real terrain · baked demo sector'
    : 'Real terrain · AWS Terrarium';
  const provenance = {
    kind: 'oasis.browser-approximation',
    label: 'Browser simulation approximation; not a recording or physics-grade sensor pipeline.',
    terrain: world.provenance.terrain,
    osm: world.provenance.osm,
    assets: {
      mapped_features: world.assets.filter((asset) => asset.source?.name === 'OpenStreetMap').length,
      synthetic_assets: world.assets.filter((asset) => asset.synthetic !== false).length,
      note: 'All unmapped structures, sensors, and defenders are procedural. OSM proximity does not make a generated sensor or military asset real.',
    },
    model: {
      detection: 'Synthetic range + terrain line-of-sight rules; no observed sensor stream.',
      damage: 'Simplified browser model with abstract HP and seeded probabilities; values are not measured performance.',
      altitude: 'Track alt values are metres MSL; AGL is retained separately where available.',
    },
    unavailable: { rf: true, fixes: true, media: true, audit: true, weather: true },
    clock: 'scenario.start is a deterministic simulation clock anchor, not an observed event timestamp.',
  };
  return {
    scenario: {
      name: `OASIS browser approximation · ${cfg.worldSeed}/${cfg.scenarioSeed}`,
      label: terrainMode === 'baked' ? 'BAKED DEMO SECTOR · BROWSER APPROXIMATION' : 'UKRAINE TERRAIN · BROWSER APPROXIMATION',
      start: cfg.start,
      duration_s: durationS,
      area: { lat: tile.lat, lon: tile.lon, size_km: tile.size_km },
      weather: { wind_from_deg: 0, wind_mps: 0, temp_c: 0, rh_pct: 0, visibility_km: 0, cloud_pct: 0 },
    },
    terrain: world.terrain,
    objects,
    sensors: [],
    classes: [],
    links: [],
    labels: [],
    rf: {},
    fixes: FIXES_EMPTY(),
    shadow: {},
    events: run.events.map((event) => ({ t: event.t, kind: event.kind, label: event.text })),
    media: [],
    provenance: {
      ...provenance,
      terrain_label: terrainLabel,
      weather_note: 'Zero-valued placeholders satisfy the existing dataset schema; no weather observation was supplied.',
    },
    game: {
      world: world.assets,
      cfg,
      tile,
      record: run,
    },
  };
}
