// CesiumJS rendering layer for the game sim: static tile + assets built once in setGame, mutated in update.
import { color, palette } from '../globe.js';
import { toLL, heightAt, STATS, M_PER_DEG } from './seed.js';
import { iconUrl, ICON_SCALE } from '../layers/assets.js';
const C = window.Cesium;
const P = {
  tower: '<path d="M16 4 9 28M16 4l7 24M11 20h10M13 12h6M10 6a8 8 0 0 0 0 6M22 6a8 8 0 0 1 0 6"/>',
  antenna: '<path d="M16 8v20M11 13a7 7 0 0 1 10 0M7 9a13 13 0 0 1 18 0M12 28h8"/>',
  radar: '<path d="M6 10a14 14 0 0 0 16 16ZM14 18l8-8M16 26l-4 3h10"/><circle cx="23" cy="9" r="1.5"/>',
  camera: '<rect x="5" y="10" width="16" height="11" rx="2"/><path d="m21 14 6-3v9l-6-3M13 21v6h-5"/>',
  mic: '<rect x="12" y="4" width="8" height="14" rx="4"/><path d="M8 15a8 8 0 0 0 16 0M16 23v5M12 28h8"/>',
  'id-badge': '<rect x="6" y="7" width="20" height="18" rx="2"/><path d="M10 13h6M10 18h12M20 12h2"/>',
  house: '<path d="M5 15 16 6l11 9M8 13v13h16V13M14 26v-6h4v6"/>',
  bolt: '<path d="M18 3 8 18h7l-2 11 11-16h-7Z"/>',
  bridge: '<path d="M3 20h26M5 20a11 9 0 0 1 22 0M8 20v6M24 20v6M12 15v5M20 15v5M16 11v9"/>',
  fuel: '<path d="M7 27V7a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v20M5 27h16M10 10h6v5h-6ZM19 12h3l2 3v8a2 2 0 0 0 4 0v-9l-3-4"/>',
  flag: '<path d="M8 29V4M8 5h16l-4 5 4 5H8"/>',
  truck: '<path d="M3 21V11h15v10M18 14h6l4 4v3H3"/><circle cx="9" cy="23" r="2.5"/><circle cx="23" cy="23" r="2.5"/><path d="M8 11l6-6"/>',
  spaag: '<path d="M4 23h24l-3-5H7ZM11 18v-4h9v4M17 14l9-8M18 16l9-6"/><circle cx="8" cy="25" r="1.5"/><circle cx="24" cy="25" r="1.5"/>',
  quad: '<path d="m10 10 12 12m0-12L10 22"/><circle cx="9" cy="9" r="4"/><circle cx="23" cy="9" r="4"/><circle cx="9" cy="23" r="4"/><circle cx="23" cy="23" r="4"/><path d="m16 4-3 4h6Z"/>',
  wave: '<path d="M16 9v19M11 13a6 6 0 0 0 0 8M21 13a6 6 0 0 1 0 8M7 9a12 12 0 0 0 0 16M25 9a12 12 0 0 1 0 16"/><circle cx="16" cy="17" r="1.5"/>',
  delta: '<path d="m16 3 13 25-13-7-13 7Z"/>',
  wing: '<path d="M16 2v27M3 14l13-3 13 3M11 28l5-3 5 3"/>',
  xwing: '<path d="M16 3v26M6 8l20 16M26 8 6 24"/>',
  x: '<path d="m8 8 16 16M24 8 8 24"/>',
};
const ICON = { 'delta-wing': 'delta', 'delta-wing-hollow': 'delta', 'x-wing': 'xwing', 'fixed-wing': 'wing',
  'quad-red': 'quad', 'quad-red-dashed': 'quad', 'quad-grey': 'quad', 'quad-blue': 'quad', 'truck-blue': 'truck',
  'spaag-blue': 'spaag', 'ew-wave': 'wave' };
const cache = {};
// White strokes so billboard.color tints by side / damage state.
const svg = (k) => cache[k] ??= 'data:image/svg+xml,' + encodeURIComponent(
  `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 32 32"><defs><filter id="h" x="-40%" y="-40%" width="180%" height="180%"><feDropShadow dx="0" dy="0" stdDeviation="1.4" flood-color="${palette.void}" flood-opacity="1"/></filter></defs><g filter="url(#h)" fill="none" stroke="#fff" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">${P[k] ?? P.quad}</g></svg>`);
const iconOf = (type) => { const i = STATS[type]?.icon; return ICON[i] ?? (P[i] ? i : 'quad'); };
const sideColor = (side) => palette[side === 'civilian' ? 'neutral' : side] ?? palette.neutral;
const bar = (hp, max) => { const n = Math.round(5 * Math.max(0, hp) / (max || 1)); return '█'.repeat(n) + '░'.repeat(5 - n); };
const range = (v) => (typeof v === 'object' && v ? (v.default ?? Math.max(...Object.values(v))) : v) || 0;
const NOW = C.Cartesian3.ZERO;
const label = (fill) => ({
  font: '10px "Geist Mono"', fillColor: color(fill), outlineColor: color(palette.void), outlineWidth: 3,
  style: C.LabelStyle.FILL_AND_OUTLINE, pixelOffset: new C.Cartesian2(16, -12), horizontalOrigin: C.HorizontalOrigin.LEFT,
  disableDepthTestDistance: Number.POSITIVE_INFINITY, scaleByDistance: new C.NearFarScalar(2e3, 1, 4e4, 0.6),
});
const solid = (hex, a) => C.Material.fromType('Color', { color: color(hex, a) });
const dash = (hex, a, len = 16) => C.Material.fromType('PolylineDash', { color: color(hex, a), dashLength: len });

export function createGameLayer(globe) {
  const { viewer, scene } = globe;
  const src = new C.CustomDataSource('game');
  viewer.dataSources.add(src);
  const stat = scene.primitives.add(new C.PolylineCollection());   // tile, grid, coverage rings, planned paths
  const dyn = scene.primitives.add(new C.PolylineCollection());    // rebuilt each update: trails, links, fx
  const dots = scene.primitives.add(new C.PointPrimitiveCollection());
  let G = null, T = null, ex = 0, fixed = new Map(), drones = new Map(), rings = new Map(), paths = new Map();
  const trails = new Map(), dead = new Map();
  const pos = (x, y, z) => { const [lon, lat] = toLL(T, x, y); return globe.position(lon, lat, z); };
  const ground = (x, y, up = 3) => pos(x, y, heightAt(T, x, y) + up);
  const circle = (x, y, r, z, n = 48) => Array.from({ length: n + 1 }, (_, i) => {
    const a = (i / n) * 2 * Math.PI, px = x + r * Math.sin(a), py = y + r * Math.cos(a);
    return z == null ? ground(px, py, 6) : pos(px, py, z);
  });
  const line = (a, b, n) => Array.from({ length: n + 1 }, (_, i) =>
    ground(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n));

  function clear() {
    src.entities.removeAll(); stat.removeAll(); dyn.removeAll(); dots.removeAll();
    fixed = new Map(); drones = new Map(); rings = new Map(); paths = new Map(); trails.clear(); dead.clear();
    G = T = null; scene.requestRender();
  }

  function setGame(game) {
    clear(); G = game; T = game.tile; ex = scene.verticalExaggeration;
    const h = T.size / 2, corners = [[-h, -h], [h, -h], [h, h], [-h, h], [-h, -h]];
    const rim = corners.slice(1).flatMap((c, i) => line(corners[i], c, 60));
    stat.add({ positions: rim, width: 7, material: C.Material.fromType('PolylineGlow', { color: color(palette.system, 0.9), glowPower: 0.25 }) });
    for (let k = -h + 1000; k < h - 1; k += 1000) for (const [a, b] of [[[k, -h], [k, h]], [[-h, k], [h, k]]])
      stat.add({ positions: line(a, b, 40), width: 1, material: solid(palette.system, 0.12) });
    for (const e of game.world) {
      const c = sideColor(e.side);
      fixed.set(e.id, src.entities.add({
        position: pos(e.x, e.y, e.z),
        billboard: { image: svg(iconOf(e.type)), width: 26, height: 26, color: color(c), disableDepthTestDistance: Number.POSITIVE_INFINITY },
        label: { text: e.id.toUpperCase(), ...label(c) },
      }));
      const r = e.cat === 'sensors' ? range(STATS[e.type]?.detect_range_m) : e.cat === 'defenders' ? range(STATS[e.type]?.engage_range_m) : 0;
      if (!r) continue;
      const sens = e.cat === 'sensors', hex = sens ? palette.system : e.type === 'jammer' ? palette.rf : palette.friendly;
      rings.set(e.id, [
        stat.add({ positions: circle(e.x, e.y, r, null, 96), width: 1.2, material: sens ? solid(hex, 0.45) : dash(hex, 0.6) }),
        src.entities.add({ position: pos(e.x, e.y, e.z), ellipse: { semiMajorAxis: r, semiMinorAxis: r, material: color(hex, sens ? 0.035 : 0.02), classificationType: C.ClassificationType.TERRAIN } }),
      ]);
    }
    for (const d of game.drones) {
      drones.set(d.id, src.entities.add({
        position: NOW, show: false,
        billboard: { image: svg(iconOf(d.type)), width: 24, height: 24, color: color(palette.hostile), alignedAxis: C.Cartesian3.UNIT_Z, disableDepthTestDistance: Number.POSITIVE_INFINITY },
        label: { text: d.id.toUpperCase(), ...label(palette.hostile) },
      }));
      if (d.path?.length > 1) paths.set(d.id, stat.add({ show: false, width: 1, material: dash(palette.hostile, 0.22, 24),
        positions: d.path.map(([x, y]) => pos(x, y, d.z)) }));
    }
  }

  function update(S, opts = {}) {
    if (!G) return;
    if (scene.verticalExaggeration !== ex) setGame(G);  // static geometry depends on relief
    const showLabels = opts.labels !== false;
    for (const e of S.fixed) {
      const ent = fixed.get(e.id); if (!ent) continue;
      const c = e.alive ? color(sideColor(e.side)) : color(palette.muted, 0.5);
      ent.billboard.color = c; ent.label.fillColor = c; ent.label.show = showLabels;
      ent.label.text = `${e.id.toUpperCase()} ${bar(e.hp, e.hpMax)} ${Math.max(0, Math.round(e.hp))}`;
      for (const r of rings.get(e.id) ?? []) r.show = !!opts.coverage && e.alive;
    }
    dyn.removeAll(); dots.removeAll();
    const trail = (id, p, max) => { const t = trails.get(id) ?? []; t.push(p); if (t.length > max) t.shift(); trails.set(id, t); return t; };
    const drawTrail = (t, hex) => { if (t.length > 1) dyn.add({ positions: t, width: 2.5,
      material: C.Material.fromType('PolylineGlow', { color: color(hex, 0.55), glowPower: 0.12, taperPower: 0.6 }) }); };
    for (const d of S.drones) {
      const ent = drones.get(d.id); if (!ent) continue;
      const path = paths.get(d.id);
      if (path) path.show = d.state !== 'PENDING';
      if (d.state === 'PENDING') { ent.show = false; continue; }
      if (d.alive && d.state === 'INBOUND') {
        const p = pos(d.x, d.y, d.z);
        ent.show = true; ent.position = p; ent.billboard.rotation = -d.heading;
        ent.billboard.image = svg(iconOf(d.type)); ent.billboard.color = color(palette.hostile);
        ent.label.show = showLabels; ent.label.text = `${d.id.toUpperCase()} ${bar(d.hp, d.hpMax)} ${Math.max(0, Math.round(d.hp))}`;
        drawTrail(trail(d.id, p, 60), palette.hostile);
        continue;
      }
      if (!dead.has(d.id)) { dead.set(d.id, S.t); ent.position = pos(d.x, d.y, d.z); }
      const gone = S.t - dead.get(d.id) > 10 || d.state === 'EXITED';
      ent.show = !gone; ent.billboard.image = svg('x'); ent.billboard.rotation = 0;
      ent.billboard.color = color(palette.muted, 0.8); ent.label.fillColor = color(palette.muted, 0.8);
      ent.label.show = showLabels && !gone; ent.label.text = `${d.id.toUpperCase()} ${d.state}`;
      if (!gone) drawTrail(trails.get(d.id) ?? [], palette.muted);
    }
    for (const i of S.interceptors) {
      if (!i.alive) continue;
      const p = pos(i.x, i.y, i.z);
      dots.add({ position: p, pixelSize: 6, color: color(palette.friendly), outlineColor: color(palette.void), outlineWidth: 1.5, disableDepthTestDistance: Number.POSITIVE_INFINITY });
      drawTrail(trail('i:' + i.id, p, 15), palette.friendly);
    }
    if (opts.links) for (const [s, d] of S.links) dyn.add({ positions: [pos(s.x, s.y, s.z), pos(d.x, d.y, d.z)], width: 1,
      material: solid(s.type === 'rf_df' ? palette.rf : palette.system, 0.5) });
    for (const f of S.fx) {
      const age = S.t - f.t0;
      if (f.kind === 'boom' && age <= 2) {
        const k = Math.max(0.05, age / 2), r = f.r * k, air = f.z - heightAt(T, f.x, f.y) > 20;
        dyn.add({ positions: circle(f.x, f.y, r, air ? f.z : null, 32), width: f.small ? 1.5 : 2.5,
          material: solid(f.small ? palette.muted : palette.rf, 0.9 * (1 - k)) });
      } else if (f.kind === 'tracer' && age <= 1) {
        const hex = f.jam ? '#b48cff' : f.hit ? '#5fe3a1' : palette.muted, a = (f.hit || f.jam ? 0.9 : 0.35) * (1 - age);
        dyn.add({ positions: [pos(f.a.x, f.a.y, f.a.z), pos(f.b.x, f.b.y, f.b.z)], width: f.hit ? 2 : 1,
          material: f.jam ? dash(hex, a, 10) : solid(hex, a) });
      }
    }
    scene.requestRender();
  }

  function destroy() {
    clear();
    viewer.dataSources.remove(src, true);
    for (const p of [stat, dyn, dots]) scene.primitives.remove(p);
  }
  return { setGame, update, clear, destroy };
}

const TERMINAL_STATES = new Set(['KILLED', 'JAMMED', 'IMPACT', 'DECOY END', 'EXITED', 'SPENT']);
const HELD_TERMINAL_STATES = new Set(['KILLED', 'JAMMED', 'IMPACT', 'DECOY END', 'SPENT']);
const TERMINAL_HOLD_S = 2.5;
const COLLISION_FLASH_S = 2.2;
const MAX_TRACK_LABELS = 6;
const MAX_HP_LABELS = 6;
const finite = (v) => Number.isFinite(v) ? v : null;
const interp = (a, b, k) => a == null || b == null ? (a ?? b) : a + (b - a) * k;

// Recorded playback reads only game.world + game.record; it never mutates or consults a live sim.
// Fixed icons are opt-in because Eklavya's existing assets layer already draws dataset assets.
export function createRecordedLayer(globe, data, { showFixedIcons = false } = {}) {
  const { viewer, scene } = globe;
  const game = data?.game ?? {};
  const record = game.record ?? {};
  const world = Array.isArray(game.world) ? game.world : [];
  const rawTile = game.tile ?? record.tile ?? null;
  const tileLat = finite(rawTile?.lat);
  const tile = rawTile ? {
    ...rawTile,
    cosLat: finite(rawTile.cosLat) ?? (tileLat == null ? null : Math.cos(tileLat * Math.PI / 180)),
  } : null;
  const source = new C.CustomDataSource('recorded simulation');
  viewer.dataSources.add(source);
  const coverage = scene.primitives.add(new C.PolylineCollection());
  const links = scene.primitives.add(new C.PolylineCollection());
  const effects = scene.primitives.add(new C.PointPrimitiveCollection());
  const fixedById = new Map();
  const fixedIcons = [];
  const trackById = new Map();
  const trackEntities = new Map();
  const damageById = new Map();
  const coverageLines = [];
  let relief = scene.verticalExaggeration;
  let destroyed = false;

  const localLL = (x, y) => {
    if (!tile || finite(tile.lat) == null || finite(tile.lon) == null || finite(tile.cosLat) == null) return null;
    return toLL(tile, x, y);
  };
  const coordsOf = (e) => {
    if (finite(e?.lon) != null && finite(e?.lat) != null) return [e.lon, e.lat];
    if (finite(e?.x) != null && finite(e?.y) != null) return localLL(e.x, e.y);
    return null;
  };
  const positionAt = (lon, lat, alt = 0) => globe.position(lon, lat, finite(alt) ?? 0);
  const fixedPosition = (asset) => {
    const ll = asset.coords;
    return ll ? positionAt(ll[0], ll[1], asset.alt) : C.Cartesian3.ZERO;
  };

  for (const row of Array.isArray(record.damage) ? record.damage : []) {
    if (row?.target == null || finite(row.t) == null) continue;
    const list = damageById.get(row.target) ?? [];
    list.push(row);
    damageById.set(row.target, list);
  }
  for (const rows of damageById.values()) rows.sort((a, b) => a.t - b.t);
  const damageAt = (id, t) => {
    const rows = damageById.get(id);
    if (!rows?.length) return null;
    let lo = 0, hi = rows.length;
    while (lo < hi) {
      const mid = (lo + hi) >>> 1;
      if (rows[mid].t <= t) lo = mid + 1;
      else hi = mid;
    }
    return lo ? rows[lo - 1] : null;
  };

  const fixed = world.map((e) => {
    const coords = coordsOf(e);
    if (!coords) return null;
    const initialHp = finite(e.hp) ?? finite(e.hpMax) ?? finite(e.hp_max);
    const maxHp = finite(e.hpMax) ?? finite(e.hp_max) ?? initialHp;
    const asset = {
      id: e.id, type: e.type, cat: e.cat, side: e.side, coords,
      alt: finite(e.z) ?? finite(e.alt) ?? 0,
      initialHp, maxHp, initialAlive: e.alive !== false, raw: e,
    };
    fixedById.set(asset.id, asset);
    if (showFixedIcons) {
      const fallback = e.cat === 'sensors' ? 'rf_df' : e.cat === 'defenders' ? 'ad_team' : 'site';
      const image = iconUrl(e.type) ?? iconUrl(fallback);
      if (image) {
        const entity = source.entities.add({
          id: `recorded-fixed:${asset.id}`,
          position: fixedPosition(asset),
          billboard: {
            image, width: 30, height: 30, scaleByDistance: ICON_SCALE,
            disableDepthTestDistance: Number.POSITIVE_INFINITY,
          },
        });
        fixedIcons.push({ asset, entity });
      }
    }
    return asset;
  }).filter(Boolean);

  const fixedGroups = new Map();
  for (const asset of fixed) {
    if (asset.initialHp == null) continue;
    const key = finite(asset.raw.x) != null && finite(asset.raw.y) != null
      ? `${asset.raw.x}:${asset.raw.y}` : `${asset.coords[0].toFixed(6)}:${asset.coords[1].toFixed(6)}`;
    const group = fixedGroups.get(key) ?? { assets: [], entity: null, position: fixedPosition(asset) };
    group.assets.push(asset);
    fixedGroups.set(key, group);
  }
  for (const group of fixedGroups.values()) {
    group.entity = source.entities.add({
      position: group.position,
      label: {
        text: '', show: false, font: '10px "Geist Mono"',
        fillColor: color(palette.rf), outlineColor: color(palette.void), outlineWidth: 3,
        style: C.LabelStyle.FILL_AND_OUTLINE, pixelOffset: new C.Cartesian2(16, -12),
        horizontalOrigin: C.HorizontalOrigin.LEFT, scaleByDistance: new C.NearFarScalar(2e3, 1, 4e4, 0.65),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
    });
  }

  const droneMeta = new Map((Array.isArray(record.drones) ? record.drones : []).map((d) => [d.id, d]));
  for (const row of Array.isArray(record.tracks) ? record.tracks : []) {
    if (!row || row.id == null || finite(row.t) == null) continue;
    const rows = trackById.get(row.id) ?? [];
    rows.push(row);
    trackById.set(row.id, rows);
  }
  for (const [id, rows] of trackById) {
    rows.sort((a, b) => a.t - b.t);
    const meta = droneMeta.get(id) ?? {};
    const type = meta.type ?? (String(id).startsWith('INT-') ? 'interceptor' : 'dji_mavic3');
    const side = type === 'interceptor' || String(id).startsWith('INT-') ? 'friendly' : 'hostile';
    const image = iconUrl(type) ?? iconUrl('dji_mavic3');
    const entity = source.entities.add({
      id: `recorded-track:${id}`, show: false, position: C.Cartesian3.ZERO,
      billboard: {
        image, width: 28, height: 28, scaleByDistance: ICON_SCALE,
        color: color(palette[side]), heightReference: C.HeightReference.NONE,
        alignedAxis: C.Cartesian3.UNIT_Z, disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
      label: { text: '', show: false, ...label(palette[side]) },
    });
    trackEntities.set(id, { entity, side, type });
    trackById.set(id, {
      rows, meta, type,
      t0: finite(meta.t0) ?? rows[0].t,
      endT: finite(meta.end_t),
      maxHp: finite(meta.hp_max) ?? finite(STATS[type]?.hp),
      finalState: meta.state ?? rows[rows.length - 1].state,
    });
  }

  let latestTime = 0;
  for (const rows of trackById.values()) for (const row of rows.rows) latestTime = Math.max(latestTime, row.t);
  for (const list of [record.events, record.collisions, record.damage])
    for (const row of Array.isArray(list) ? list : []) latestTime = Math.max(latestTime, finite(row?.t) ?? 0);
  for (const drone of Array.isArray(record.drones) ? record.drones : []) latestTime = Math.max(latestTime, finite(drone.end_t) ?? 0);
  const runEnd = [
    finite(record.summary?.duration_s), finite(game.cfg?.durationS), finite(game.cfg?.duration_s),
    finite(record.cfg?.durationS), finite(record.cfg?.duration_s),
  ].find((v) => v != null) ?? latestTime;

  function interpolateTrack(track, t) {
    const rows = track.rows, first = rows[0], last = rows[rows.length - 1];
    if (t <= first.t) return { ...first, t };
    if (t >= last.t) return { ...last, t };
    let lo = 0, hi = rows.length - 1;
    while (lo + 1 < hi) {
      const mid = (lo + hi) >>> 1;
      if (rows[mid].t <= t) lo = mid;
      else hi = mid;
    }
    const a = rows[lo], b = rows[hi], k = (t - a.t) / (b.t - a.t);
    const aLL = coordsOf(a), bLL = coordsOf(b);
    if (!aLL || !bLL) return null;
    return {
      id: a.id, t,
      lon: interp(finite(a.lon) ?? aLL[0], finite(b.lon) ?? bLL[0], k),
      lat: interp(finite(a.lat) ?? aLL[1], finite(b.lat) ?? bLL[1], k),
      alt: interp(finite(a.alt) ?? finite(a.z), finite(b.alt) ?? finite(b.z), k),
      hp: finite(a.hp), state: a.state ?? b.state,
    };
  }
  function sampleTrack(track, t) {
    if (t < track.t0 || t > runEnd) return null;
    const last = track.rows[track.rows.length - 1];
    const finalState = track.finalState ?? last.state;
    if (track.endT != null && t > track.endT) {
      if (!HELD_TERMINAL_STATES.has(finalState) || t > track.endT + TERMINAL_HOLD_S) return null;
      const terminal = interpolateTrack(track, track.endT);
      return terminal ? { ...terminal, state: finalState } : null;
    }
    if (t > last.t) {
      if (!HELD_TERMINAL_STATES.has(last.state) || t > last.t + TERMINAL_HOLD_S) return null;
      return { ...last, t };
    }
    const sample = interpolateTrack(track, t);
    if (sample && track.endT != null && t >= track.endT && TERMINAL_STATES.has(finalState)) sample.state = finalState;
    return sample;
  }
  function altitudeAt(x, y, fallback = 0) {
    if (tile?.grid && finite(x) != null && finite(y) != null) {
      try { return heightAt(tile, x, y) + 4; } catch { /* fall through to the recorded globe position */ }
    }
    return fallback;
  }
  function collisionPosition(collision, t) {
    const ll = localLL(collision.x, collision.y);
    if (!ll) return null;
    const actor = trackById.get(collision.a) ?? trackById.get(collision.b);
    const linked = actor ? sampleTrack(actor, collision.t) : null;
    const alt = linked?.alt ?? altitudeAt(collision.x, collision.y, 3);
    return positionAt(ll[0], ll[1], alt);
  }

  // Catalog range circles are geometry only (default/max numeric range), never a terrain/LOS viewshed.
  function rangeRingPositions(asset, radius) {
    const [lon, lat] = asset.coords;
    const altitude = asset.alt;
    return Array.from({ length: 97 }, (_, i) => {
      const angle = i / 96 * Math.PI * 2;
      const dx = radius * Math.sin(angle), dy = radius * Math.cos(angle);
      const local = finite(asset.raw.x) != null && finite(asset.raw.y) != null
        ? localLL(asset.raw.x + dx, asset.raw.y + dy) : null;
      const ll = local ?? [lon + dx / (M_PER_DEG * Math.cos(lat * Math.PI / 180)), lat + dy / M_PER_DEG];
      return positionAt(ll[0], ll[1], altitude);
    });
  }
  function rebuildCoverage() {
    coverage.removeAll();
    coverageLines.length = 0;
    for (const asset of fixed) {
      if (asset.cat !== 'sensors') continue;
      const radius = range(STATS[asset.type]?.detect_range_m);
      if (!Number.isFinite(radius) || radius <= 0) continue;
      coverageLines.push(coverage.add({
        positions: rangeRingPositions(asset, radius), show: false, width: 1.2,
        material: solid(palette.system, 0.42),
      }));
    }
    relief = scene.verticalExaggeration;
  }
  rebuildCoverage();

  function update(t, opts = {}) {
    if (destroyed) return;
    const time = finite(t);
    const inRun = time != null && time >= 0 && time <= runEnd;
    const truthVisible = opts.truth !== false && opts.mode !== 'operator';
    const showCoverage = opts.coverage === true;
    const showLabels = opts.labels !== false;
    if (scene.verticalExaggeration !== relief) rebuildCoverage();
    for (const ring of coverageLines) ring.show = showCoverage;
    links.removeAll();
    effects.removeAll();

    for (const { asset, entity } of fixedIcons) {
      const hit = inRun ? damageAt(asset.id, time) : null;
      const hp = finite(hit?.hp_after) ?? asset.initialHp;
      const alive = asset.initialAlive && (hp == null || hp > 0);
      entity.position = fixedPosition(asset);
      entity.billboard.color = color(truthVisible && !alive ? palette.muted : (palette[asset.side] ?? palette.neutral), truthVisible && !alive ? 0.55 : 1);
      entity.show = true;
    }

    const hpGroups = [];
    for (const group of fixedGroups.values()) {
      group.entity.label.show = false;
      if (!inRun || !truthVisible || !showLabels) continue;
      const changed = group.assets.flatMap((asset) => {
        const hit = damageAt(asset.id, time);
        if (!hit) return [];
        const hp = finite(hit.hp_after) ?? asset.initialHp;
        const max = asset.maxHp ?? asset.initialHp ?? 1;
        const state = hp <= 0 ? 'DESTROYED' : `${Math.max(0, Math.round(hp))}/${Math.round(max)}`;
        return [{ asset, hit, hp, state }];
      });
      if (!changed.length) continue;
      changed.sort((a, b) => (b.hit.t - a.hit.t) || (a.hp - b.hp));
      const parts = changed.slice(0, 2).map(({ asset, hp, state }) => `${String(asset.id).toUpperCase()} ${hp <= 0 ? 'DESTROYED' : `${bar(hp, asset.maxHp ?? asset.initialHp ?? 1)} ${state}`}`);
      if (changed.length > 2) parts.push(`+${changed.length - 2}`);
      hpGroups.push({ group, changed, text: parts.join(' · '), t: changed[0].hit.t });
    }
    hpGroups.sort((a, b) => (b.t - a.t) || (Math.min(...a.changed.map((r) => r.hp)) - Math.min(...b.changed.map((r) => r.hp))));
    for (const { group, changed, text } of hpGroups.slice(0, MAX_HP_LABELS)) {
      group.entity.position = fixedPosition(changed[0].asset);
      group.entity.label.text = text;
      group.entity.label.fillColor = color(changed.some((row) => row.hp <= 0) ? palette.hostile : palette.rf);
      group.entity.label.show = true;
    }

    const activeTracks = [];
    for (const [id, track] of trackById) {
      const details = trackEntities.get(id), entity = details?.entity;
      if (!entity) continue;
      const sample = inRun && truthVisible ? sampleTrack(track, time) : null;
      if (!sample || sample.lon == null || sample.lat == null) {
        entity.show = false;
        entity.label.show = false;
        continue;
      }
      const p = positionAt(sample.lon, sample.lat, sample.alt ?? sample.z ?? 0);
      entity.position = p;
      entity.show = true;
      const hpRow = damageAt(id, time);
      const hp = finite(hpRow?.hp_after) ?? finite(sample.hp);
      entity.label.text = hp == null
        ? `${String(id).toUpperCase()} ${sample.state ?? details.type.toUpperCase()}`
        : `${String(id).toUpperCase()} ${bar(hp, track.maxHp ?? Math.max(hp, 1))} ${Math.max(0, Math.round(hp))}`;
      activeTracks.push({ id, entity, sample, hp, terminal: TERMINAL_STATES.has(sample.state) });
    }
    activeTracks.sort((a, b) => Number(a.terminal) - Number(b.terminal) || (a.hp ?? Infinity) - (b.hp ?? Infinity) || a.id.localeCompare(b.id));
    const shownLabels = new Set(activeTracks.slice(0, MAX_TRACK_LABELS).map((row) => row.id));
    for (const row of activeTracks) row.entity.label.show = showLabels && shownLabels.has(row.id);

    if (inRun && truthVisible && opts.links === true) {
      for (const detection of Array.isArray(record.detections) ? record.detections : []) {
        const start = finite(detection.t_start), end = finite(detection.t_end);
        if (start == null || time < start || (end != null && time >= end)) continue;
        const sensor = fixedById.get(detection.sensor);
        const targetTrack = trackById.get(detection.target);
        const target = targetTrack && sampleTrack(targetTrack, time);
        if (!sensor || !target || target.lon == null || target.lat == null) continue;
        links.add({
          positions: [fixedPosition(sensor), positionAt(target.lon, target.lat, target.alt ?? target.z ?? 0)],
          width: 1.4, material: solid(palette.system, 0.58),
        });
      }
    }

    if (inRun && truthVisible) {
      for (const collision of Array.isArray(record.collisions) ? record.collisions : []) {
        const at = finite(collision.t);
        if (at == null) continue;
        const age = time - at;
        if (age < 0 || age > COLLISION_FLASH_S) continue;
        const position = collisionPosition(collision, time);
        if (!position) continue;
        const alpha = 1 - age / COLLISION_FLASH_S;
        const hit = /hit|impact|crash|debris/.test(collision.kind ?? '');
        effects.add({
          position, pixelSize: 7 + 18 * (age / COLLISION_FLASH_S),
          color: color(palette.void, 0.03),
          outlineColor: color(hit ? palette.rf : palette.muted, alpha), outlineWidth: 2,
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
        });
      }
    }
    scene.requestRender();
  }

  function destroy() {
    if (destroyed) return;
    destroyed = true;
    source.entities.removeAll();
    viewer.dataSources.remove(source, true);
    for (const primitive of [coverage, links, effects]) scene.primitives.remove(primitive);
  }
  return { update, destroy };
}
