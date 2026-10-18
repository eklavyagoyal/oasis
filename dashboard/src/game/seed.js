// Seed engine: world seed -> tile + fixed assets (the "map"); scenario seed -> movable assets (the "match").
// Same seeds = same world and same match (Minecraft-style). Runs on the loaded MW.terrain DEM.
import A from './assets.json';
import { heightAt as demHeight } from '../data.js';

export const STATS = Object.fromEntries(Object.values(A.categories).flat().map((a) => [a.id, a]));
export const CAT = Object.fromEntries(Object.entries(A.categories).flatMap(([c, l]) => l.map((a) => [a.id, c])));
export const RULES = A.defaults;
export const M_PER_DEG = 111195;  // mirrorworld/config.py
// Cruise altitude bands (m AGL) and roles from mirrorworld/builder.py.
export const ALT_AGL = {
  shahed136: [300, 1500], gerbera: [300, 1500], lancet: [100, 400], fpv_analog: [10, 40], fpv_fiber: [10, 40],
  orlan10: [150, 500], zala: [150, 500], supercam: [150, 500], dji_mavic3: [60, 150],
};
export const ONE_WAY = new Set(['shahed136', 'gerbera', 'lancet', 'fpv_analog', 'fpv_fiber']);
export const SILENT = new Set(['gerbera', 'fpv_fiber']);  // no radio links in catalog.py: RF can't hear them
export const DEFAULTS = {
  worldSeed: 7, scenarioSeed: 1, tileKm: 10, durationS: 3600,
  start: '2026-01-01T00:00:00.000Z', drones: 6, entry: 'random', waveSpanS: 240,
  mix: ['shahed136', 'gerbera', 'orlan10', 'fpv_analog'], defence: true, radar: true, acoustic: true,
};
const PREFIX = {
  rf_df: 'RF', radar: 'RADAR', camera: 'EO', acoustic: 'MIC', remote_id: 'RID', comms_mast: 'MAST', substation: 'SUBSTATION',
  village_house: 'HOUSE', bridge: 'BRIDGE', fuel_depot: 'FUEL', c2_post: 'C2', ad_team: 'MFG', ad_battery: 'AD',
  interceptor: 'INT-BASE', jammer: 'EW',
};
const SENSOR_MAST_M = 30;

// Seeded generator (FNV-1a hash -> mulberry32). rng(seed, 'place') and rng(seed, 'wave') are independent streams.
export function rng(seed, name = '') {
  let h = 2166136261;
  for (const ch of `${seed}:${name}`) h = Math.imul(h ^ ch.charCodeAt(0), 16777619);
  let a = h >>> 0;
  const r = () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  r.range = (lo, hi) => lo + r() * (hi - lo);
  r.int = (lo, hi) => Math.floor(r.range(lo, hi + 1));
  r.pick = (l) => l[Math.floor(r() * l.length)];
  return r;
}

// ---- tile: a size x size km square cut out of the loaded DEM; x east / y north in metres from its centre ----
// Exact centre from `site` (or cfg.lat/cfg.lon) when the DEM was fetched for that site; otherwise a seeded random offset (replay DEM).
export function makeTile(grid, cfg, site) {
  const c = site || (Number.isFinite(cfg.lat) && Number.isFinite(cfg.lon) ? cfg : null);
  let lat, lon;
  if (c) ({ lat, lon } = c);
  else {
    const r = rng(cfg.worldSeed, 'tile');
    lat = r.range(grid.south, grid.north);
    lon = r.range(grid.west, grid.east);
  }
  if (lat < grid.south || lat > grid.north || lon < grid.west || lon > grid.east)
    throw new Error('Tile center is outside the supplied terrain grid.');
  const mPerLon = M_PER_DEG * Math.cos((lat * Math.PI) / 180);
  const availableW = 2 * Math.min((lon - grid.west) * mPerLon, (grid.east - lon) * mPerLon);
  const availableH = 2 * Math.min((lat - grid.south) * M_PER_DEG, (grid.north - lat) * M_PER_DEG);
  const size = Math.min(cfg.tileKm * 1000, availableW, availableH);
  if (!Number.isFinite(size) || size <= 0) throw new Error('Terrain grid has no usable area around the selected tile center.');
  const tileCosLat = Math.cos((lat * Math.PI) / 180);
  const T = { grid, lat, lon, size, sizeKm: size / 1000, cosLat: tileCosLat };
  const half = size / 2;
  [T.west, T.south] = toLL(T, -half, -half);
  [T.east, T.north] = toLL(T, half, half);
  T.requestedSizeKm = cfg.tileKm;
  return T;
}
export const toLL = (T, x, y) => [T.lon + x / (M_PER_DEG * T.cosLat), T.lat + y / M_PER_DEG];  // [lon, lat]
export const heightAt = (T, x, y) => demHeight(T.grid, ...toLL(T, x, y));
export function los(T, a, b, steps = 32) {  // terrain line of sight between {x, y, z(m MSL)} points
  for (let s = 1; s < steps; s++) {
    const t = s / steps;
    if (heightAt(T, a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t) > a.z + (b.z - a.z) * t) return false;
  }
  return true;
}

function entity(type, x, y, T, n) {
  const s = STATS[type], cat = CAT[type], ground = heightAt(T, x, y);
  return {
    id: `${PREFIX[type] || type.toUpperCase()}-${n}`, type, cat, side: s.side === 'civilian' ? 'civilian' : 'friendly', synthetic: true,
    x, y, ground, z: ground + (cat === 'sensors' ? SENSOR_MAST_M : 2), hp: s.hp, hpMax: s.hp, alive: true, state: 'IDLE',
  };
}

// ---- world: fixed assets on real terrain. Sensors on high ground, village and bridge low, defence near what it protects ----
// `features` (optional): [{type, lat, lon, name}] from world.js#loadFeatures. Real ones go first (real: true), the rest is procedural.
export function populate(T, cfg, features) {
  const r = rng(cfg.worldSeed, 'place'), half = Math.max(0, T.size / 2 - Math.min(300, T.size * 0.05)), counts = {}, out = [];
  const add = (type, x, y, extra) => {
    x = Math.max(-half, Math.min(half, x));
    y = Math.max(-half, Math.min(half, y));
    counts[type] = (counts[type] || 0) + 1;
    const e = Object.assign(entity(type, x, y, T, counts[type]), extra);
    out.push(e);
    return e;
  };
  const real = {};  // type -> [{x, y, name}] inside the tile
  for (const f of features || []) {
    const x = (f.lon - T.lon) * M_PER_DEG * T.cosLat, y = (f.lat - T.lat) * M_PER_DEG;
    if (Math.abs(x) <= half && Math.abs(y) <= half) (real[f.type] = real[f.type] || []).push({ x, y, name: f.name || '', osm: f.osm });
  }
  const R = (t) => real[t] || [];
  const tag = (p) => ({ real: true, synthetic: false, ...(p.name ? { name: p.name } : {}), ...(p.osm ? { source: p.osm } : {}) });
  const cands = [];  // 30 x 30 jittered candidate sites
  for (let i = 0; i < 30; i++)
    for (let j = 0; j < 30; j++) {
      const x = -half + ((i + r()) / 30) * 2 * half, y = -half + ((j + r()) / 30) * 2 * half;
      cands.push({ x, y, h: heightAt(T, x, y) });
    }
  const high = [...cands].sort((a, b) => b.h - a.h), low = [...cands].sort((a, b) => a.h - b.h);
  const far = (p, list, d) => list.every((q) => Math.hypot(p.x - q.x, p.y - q.y) >= d);
  const near = (p, rMin, rMax) => {
    const a = r() * 2 * Math.PI, d = r.range(rMin, rMax);
    return [p.x + Math.cos(a) * d, p.y + Math.sin(a) * d];
  };

  // Two RF receivers on the highest points >= 35% of the tile apart (crossed bearings need a baseline), camera on mast 1.
  // Real masts first: the best-separated pair if it has a usable baseline (>= 20% of the tile), else the highest terrain.
  const dist = (p) => Math.hypot(p[0].x - p[1].x, p[0].y - p[1].y), rm = R('comms_mast');
  let masts = [];
  for (let i = 0; i < rm.length; i++)
    for (let j = i + 1; j < rm.length; j++) if (!masts.length || dist([rm[i], rm[j]]) > dist(masts)) masts = [rm[i], rm[j]];
  if (masts.length && dist(masts) < T.size * 0.2) masts = [];
  masts.forEach((p) => { add('comms_mast', p.x, p.y, tag(p)); add('rf_df', p.x, p.y); });
  for (const p of high)
    if (masts.length < 2 && far(p, masts, T.size * 0.35)) {
      masts.push(p);
      add('comms_mast', p.x, p.y);
      add('rf_df', p.x, p.y);
    }
  add('camera', masts[0].x + 15, masts[0].y);
  if (cfg.radar) {
    const site = high.find((p) => far(p, masts, T.size * 0.2)) || high[2];
    add('radar', site.x, site.y);
  }
  // Village in the lowest third, substation next to it, bridge at the lowest point (river), fuel depot low.
  const rv = [...R('village')].sort((a, b) => Math.hypot(a.x, a.y) - Math.hypot(b.x, b.y));  // nearest real village
  const village = rv[0] || r.pick(low.slice(0, Math.floor(low.length / 3)));
  for (let i = 0, nh = r.int(4, 8); i < nh; i++) add('village_house', ...near(village, 40, 400), village.name ? { real: false, synthetic: true, name: village.name } : {});
  const subs = R('substation').slice(0, 2).map((p) => add('substation', p.x, p.y, tag(p)));
  const sub = subs[0] || add('substation', ...near(village, 500, 900));
  const br = R('bridge').slice(0, 2);
  if (br.length) br.forEach((p) => add('bridge', p.x, p.y, tag(p)));
  else add('bridge', low[0].x, low[0].y);
  const fu = R('fuel_depot')[0];
  if (fu) add('fuel_depot', fu.x, fu.y, tag(fu));
  else add('fuel_depot', ...near(r.pick(low.slice(0, 200)), 0, 300));
  const c2 = add('c2_post', ...near({ x: 0, y: 0 }, 0, T.size * 0.15));
  if (cfg.acoustic) for (let i = 0; i < 3; i++) add('acoustic', ...near(sub, 1500, 2500));
  if (cfg.defence) {  // mobile fire groups around the substation, interceptor crew at C2, EW next to the site
    for (let i = 0; i < 2; i++) add('ad_team', ...near(sub, 600, 1500));
    add('interceptor', ...near(c2, 100, 300));
    add('jammer', ...near(sub, 150, 400));
    if (T.sizeKm >= 16) add('ad_battery', ...near(sub, 1500, 2500));
  }
  return out;
}
