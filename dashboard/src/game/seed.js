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
  worldSeed: 7, scenarioSeed: 1, tileKm: 10, drones: 6, entry: 'random', waveSpanS: 240,
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
export function makeTile(grid, cfg) {
  const r = rng(cfg.worldSeed, 'tile'), cosLat = Math.cos(((grid.south + grid.north) / 2) * Math.PI / 180);
  const demW = (grid.east - grid.west) * M_PER_DEG * cosLat, demH = (grid.north - grid.south) * M_PER_DEG;
  const size = Math.min(cfg.tileKm * 1000, demW, demH);
  const dx = r.range(-(demW - size) / 2, (demW - size) / 2), dy = r.range(-(demH - size) / 2, (demH - size) / 2);
  const lat = (grid.south + grid.north) / 2 + dy / M_PER_DEG, lon = (grid.west + grid.east) / 2 + dx / (M_PER_DEG * cosLat);
  const T = { grid, lat, lon, size, sizeKm: size / 1000, cosLat };
  const half = size / 2;
  [T.west, T.south] = toLL(T, -half, -half);
  [T.east, T.north] = toLL(T, half, half);
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
    id: `${PREFIX[type] || type.toUpperCase()}-${n}`, type, cat, side: s.side === 'civilian' ? 'civilian' : 'friendly',
    x, y, ground, z: ground + (cat === 'sensors' ? SENSOR_MAST_M : 2), hp: s.hp, hpMax: s.hp, alive: true, state: 'IDLE',
  };
}

// ---- world: fixed assets on real terrain. Sensors on high ground, village and bridge low, defence near what it protects ----
// `plan` (optional): [{type, x, y}] from an external planner; used only if it has >= 6 valid fixed assets.
export function populate(T, cfg, plan) {
  const r = rng(cfg.worldSeed, 'place'), half = T.size / 2 - 300, counts = {}, out = [];
  const add = (type, x, y) => {
    x = Math.max(-half, Math.min(half, x));
    y = Math.max(-half, Math.min(half, y));
    counts[type] = (counts[type] || 0) + 1;
    const e = entity(type, x, y, T, counts[type]);
    out.push(e);
    return e;
  };
  const valid = (plan || []).filter((p) => STATS[p.type] && CAT[p.type] !== 'attackers' && Number.isFinite(p.x) && Number.isFinite(p.y));
  if (valid.length >= 6) {
    valid.forEach((p) => add(p.type, p.x, p.y));
    return out;
  }
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
  const masts = [];
  for (const p of high) if (masts.length < 2 && far(p, masts, T.size * 0.35)) masts.push(p);
  masts.forEach((p) => { add('comms_mast', p.x, p.y); add('rf_df', p.x, p.y); });
  add('camera', masts[0].x + 15, masts[0].y);
  if (cfg.radar) {
    const site = high.find((p) => far(p, masts, T.size * 0.2)) || high[2];
    add('radar', site.x, site.y);
  }
  // Village in the lowest third, substation next to it, bridge at the lowest point (river), fuel depot low.
  const village = r.pick(low.slice(0, Math.floor(low.length / 3)));
  for (let i = 0, nh = r.int(4, 8); i < nh; i++) add('village_house', ...near(village, 40, 400));
  const sub = add('substation', ...near(village, 500, 900));
  add('bridge', low[0].x, low[0].y);
  add('fuel_depot', ...near(r.pick(low.slice(0, 200)), 0, 300));
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

const TARGET_WEIGHT = { substation: 4, fuel_depot: 3, comms_mast: 2, radar: 2, c2_post: 2, bridge: 1, village_house: 1 };

// ---- scenario: one match on this world. Only movable assets change; fixed assets stay put ----
export function makeScenario(T, world, cfg) {
  const r = rng(cfg.scenarioSeed, 'wave'), half = T.size / 2;
  const targets = world.filter((e) => TARGET_WEIGHT[e.type]).flatMap((e) => Array(TARGET_WEIGHT[e.type]).fill(e));
  const mix = cfg.mix.length ? cfg.mix : ['shahed136'], counts = {};
  return Array.from({ length: cfg.drones }, () => {
    const type = r.pick(mix), s = STATS[type], [lo, hi] = ALT_AGL[type] || [100, 300];
    const side = cfg.entry === 'random' ? r.pick('NESW') : cfg.entry, along = r.range(-half * 0.9, half * 0.9);
    const entry = { N: [along, half], S: [along, -half], E: [half, along], W: [-half, along] }[side];
    const tgt = r.pick(targets);
    let path;
    if (ONE_WAY.has(type)) {
      path = [entry, [(entry[0] + tgt.x) / 2 + r.range(-800, 800), (entry[1] + tgt.y) / 2 + r.range(-800, 800)], [tgt.x, tgt.y]];
    } else {  // recon: loiter 1-2 km around the target, then leave by the opposite edge
      const loop = [0, 1, 2].map(() => { const a = r() * 2 * Math.PI, d = r.range(1000, 2000); return [tgt.x + Math.cos(a) * d, tgt.y + Math.sin(a) * d]; });
      path = [entry, ...loop, [-entry[0], -entry[1]]];
    }
    counts[type] = (counts[type] || 0) + 1;
    return {
      id: `${type.replace(/\d+$/, '').toUpperCase()}-${counts[type]}`, type, cat: 'attackers', side: 'hostile',
      path, wp: 1, t0: Math.round(r.range(0, cfg.waveSpanS)), agl: r.range(lo, Math.min(hi, lo * 3)), speed: s.speed_mps,
      x: entry[0], y: entry[1], z: heightAt(T, entry[0], entry[1]), heading: 0, hp: s.hp, hpMax: s.hp, alive: true,
      state: 'PENDING', target: ONE_WAY.has(type) ? tgt.id : null, entrySide: side,
    };
  });
}

// One call for the UI: world (tile + fixed) and scenario (movable). Reroll either seed independently.
export function generate(grid, cfg) {
  const tile = makeTile(grid, cfg), world = populate(tile, cfg);
  return { cfg: { ...cfg }, tile, world, drones: makeScenario(tile, world, cfg) };
}

// Save file: everything needed to rebuild exactly this world + match (the seeds are the save; positions for readers).
export const saveJSON = (G) => JSON.stringify({
  version: 1, cfg: G.cfg,
  tile: { lat: G.tile.lat, lon: G.tile.lon, size_m: G.tile.size, west: G.tile.west, south: G.tile.south, east: G.tile.east, north: G.tile.north },
  world: G.world.map(({ id, type, cat, side, x, y, ground, hpMax }) => ({ id, type, cat, side, x_m: Math.round(x), y_m: Math.round(y), ground_m: Math.round(ground), hp: hpMax })),
  drones: G.drones.map(({ id, type, path, t0, agl, speed, target, entrySide }) => ({ id, type, entry: entrySide, t0, agl_m: Math.round(agl), speed_mps: speed, target, path_m: path.map((p) => p.map(Math.round)) })),
}, null, 1);
