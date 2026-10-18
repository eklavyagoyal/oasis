// Scenario engine: scenario seed -> movable assets (drones, routes, launch times) on a fixed world.
import { STATS, ALT_AGL, ONE_WAY, rng, heightAt } from './seed.js';

export const TARGET_WEIGHT = { substation: 4, fuel_depot: 3, comms_mast: 2, radar: 2, c2_post: 2, bridge: 1, village_house: 1 };

// ---- scenario: one match on this world. Only movable assets change; fixed assets stay put ----
export function makeScenario(T, world, cfg) {
  const r = rng(cfg.scenarioSeed, 'wave'), half = T.size / 2;
  const targets = world.filter((e) => TARGET_WEIGHT[e.type]).flatMap((e) => Array(TARGET_WEIGHT[e.type]).fill(e));
  const mix = cfg.mix?.length ? cfg.mix : ['shahed136'], counts = {};
  // Raids: drones split across waves; each wave starts at a seeded time in [0, duration - 600],
  // launches within ~4 min and mostly comes from one side.
  const dur = cfg.durationS || 3600, n = Math.min(30, Math.max(1, cfg.drones ?? 6));
  const nw = Math.min(6, n, Math.max(1, cfg.waves || Math.round(dur / 3600)));
  const waves = Array.from({ length: nw }, () => ({ start: Math.round(r.range(0, Math.max(0, dur - 600))), side: cfg.entry === 'random' || !cfg.entry ? r.pick('NESW') : cfg.entry }))
    .sort((a, b) => a.start - b.start);
  return Array.from({ length: n }, (_, i) => {
    const wave = i % nw, W = waves[wave];
    const type = r.pick(mix), s = STATS[type], [lo, hi] = ALT_AGL[type] || [100, 300];
    const side = cfg.entry === 'random' && r() < 0.2 ? r.pick('NESW') : W.side, along = r.range(-half * 0.9, half * 0.9);
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
      path, wp: 1, t0: W.start + Math.round(r.range(0, cfg.waveSpanS || 240)), wave, agl: r.range(lo, Math.min(hi, lo * 3)), speed: s.speed_mps,
      x: entry[0], y: entry[1], z: heightAt(T, entry[0], entry[1]), heading: 0, hp: s.hp, hpMax: s.hp, alive: true,
      state: 'PENDING', target: ONE_WAY.has(type) ? tgt.id : null, entrySide: side,
    };
  });
}
