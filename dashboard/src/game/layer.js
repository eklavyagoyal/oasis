// CesiumJS rendering layer for the game sim: static tile + assets built once in setGame, mutated in update.
import { color, palette } from '../globe.js';
import { toLL, heightAt, STATS } from './seed.js';
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
