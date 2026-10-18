// Real-time simulation: fixed 0.5 s ticks, every random outcome is a seeded dice roll you can replay.
import { STATS, ONE_WAY, SILENT, RULES, rng, heightAt, los, toLL } from './seed.js';

export const DT = 0.5;
const range = (sensor, type) => {
  const r = STATS[sensor].detect_range_m;
  return typeof r === 'number' ? r : r[type] ?? r.default;
};
const pk = (def, type) => def.p_kill[type] ?? def.p_kill.default;
const dist3 = (a, b) => Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);

export function createSim({ world, drones, tile: T, cfg }) {
  const fixed = world.map((e) => ({ ...e, hp: e.hpMax, ammo: STATS[e.type].ammo ?? 0, ready: 0, alive: true }));
  return {
    T, cfg, t: 0, dice: rng(cfg.scenarioSeed, 'dice'), fixed, drones: drones.map((d) => ({ ...d, seenBy: new Set() })),
    interceptors: [], events: [], fx: [], links: [], nextScan: 0, done: false, shots: 0, hits: 0, launches: 0,
    end: cfg.durationS || 3600,
    // Flat training records (see docs/DATA-PIPELINE.md). open: 'sensor|drone' -> live detection interval.
    rec: { tracks: [], detections: [], collisions: [], damage: [], open: new Map() },
  };
}

function log(S, kind, text, extra = {}) {
  S.events.push({ t: S.t, kind, text, ...extra });
}

function damage(S, e, hp, by) {
  if (!e.alive || hp <= 0) return;
  const before = e.hp;
  e.hp = Math.max(0, e.hp - hp * (1 - (STATS[e.type].armor || 0)));
  S.rec.damage.push({ t: S.t, target: e.id, by, hp_before: r1(before), hp_after: r1(e.hp), destroyed: e.hp === 0 });
  if (e.hp === 0) {
    e.alive = false;
    e.state = e.cat === 'attackers' ? 'KILLED' : 'DESTROYED';
    log(S, 'destroyed', `${e.id} ${e.state.toLowerCase()} by ${by}`, { id: e.id, by });
    S.fx.push({ kind: 'boom', x: e.x, y: e.y, z: e.z, r: e.cat === 'attackers' ? 60 : 150, t0: S.t });
    if (e.cat === 'attackers' && S.dice() < RULES.debris_p) {  // falling debris still hurts what is underneath
      collide(S, 'debris', e.id, null, e.x, e.y);
      blast(S, e.x, e.y, (STATS[e.type].damage?.payload_hp || 0) * RULES.debris_fraction, 40, `${e.id} debris`);
    }
  }
}

// Blast falloff: payload * max(0, 1 - d / r), d measured from the target's footprint edge.
function blast(S, x, y, payload, r, by) {
  if (payload <= 0 || r <= 0) return;
  for (const e of S.fixed) {
    const d = Math.max(0, Math.hypot(e.x - x, e.y - y) - (STATS[e.type].footprint_m || 0) / 2);
    if (d < r) damage(S, e, payload * (1 - d / r), by);
  }
}

function moveDrone(S, d) {
  const [tx, ty] = d.path[d.wp], dx = tx - d.x, dy = ty - d.y, gap = Math.hypot(dx, dy), stepM = d.speed * DT;
  d.heading = Math.atan2(dx, dy);
  if (gap <= stepM) {
    d.x = tx; d.y = ty; d.wp++;
    if (d.wp === d.path.length) {  // end of path
      d.alive = false;
      if (ONE_WAY.has(d.type)) {
        const dmg = STATS[d.type].damage;
        d.state = dmg.payload_hp > 0 ? 'IMPACT' : 'DECOY END';
        log(S, 'impact', `${d.id} reached ${d.target}${dmg.payload_hp ? '' : ' (decoy, no warhead)'}`, { id: d.id, target: d.target });
        S.fx.push({ kind: 'boom', x: d.x, y: d.y, z: heightAt(S.T, d.x, d.y), r: Math.max(40, dmg.blast_radius_m * 4), t0: S.t });
        collide(S, 'impact', d.id, d.target, d.x, d.y);
        blast(S, d.x, d.y, dmg.payload_hp, dmg.blast_radius_m, d.id);
      } else {
        d.state = 'EXITED';
        log(S, 'exit', `${d.id} left the area (recon complete)`, { id: d.id });
      }
    }
  } else {
    d.x += (dx / gap) * stepM; d.y += (dy / gap) * stepM;
  }
  // ponytail: terrain-following cruise, linear dive over the last 1.5 km of a one-way path.
  const last = d.path[d.path.length - 1], toEnd = Math.hypot(last[0] - d.x, last[1] - d.y);
  const agl = ONE_WAY.has(d.type) && d.wp === d.path.length - 1 ? d.agl * Math.min(1, toEnd / 1500) : d.agl;
  d.z = heightAt(S.T, d.x, d.y) + agl;
}

// Which sensors can see which drone right now: range + terrain line of sight (+ radio emission for RF).
function scan(S) {
  S.links = [];
  for (const s of S.fixed) {
    if (!s.alive || s.cat !== 'sensors') continue;
    for (const d of S.drones) {
      if (!d.alive || S.t < d.t0) continue;
      if (s.type === 'rf_df' && SILENT.has(d.type)) continue;
      if (s.type === 'remote_id' && d.type !== 'dji_mavic3') continue;
      if (dist3(s, d) > range(s.type, d.type)) continue;
      if (s.type !== 'acoustic' && !los(S.T, s, d)) continue;  // ponytail: sound ignores terrain screening here
      S.links.push([s, d]);
      if (!d.seenBy.size) {
        d.firstSeen = S.t;
        log(S, 'detect', `${s.id} detects ${d.id}`, { id: d.id, by: s.id });
      }
      d.seenBy.add(s.id);
    }
  }
}

// Open / close per-(sensor, drone) detection intervals as S.links changes.
function trackLinks(S) {
  const now = new Set(), open = S.rec.open;
  for (const [s, d] of S.links) {
    const k = `${s.id}|${d.id}`;
    now.add(k);
    if (!open.has(k)) open.set(k, { sensor: s.id, target: d.id, t_start: S.t, t_end: null });
  }
  for (const [k, row] of open) if (!now.has(k)) { row.t_end = S.t; S.rec.detections.push(row); open.delete(k); }
}

function detected(S) {
  const live = new Set(S.links.map(([, d]) => d));
  return S.drones.filter((d) => d.alive && live.has(d));
}

function defend(S) {
  const seen = detected(S), w = RULES.window_s;
  for (const e of S.fixed) {
    if (!e.alive || e.cat !== 'defenders' || S.t < e.ready || e.ammo === 0) continue;
    const st = STATS[e.type];
    const inRange = seen.filter((d) => Math.hypot(d.x - e.x, d.y - e.y) <= st.engage_range_m && d.z - heightAt(S.T, d.x, d.y) <= (st.max_target_alt_m ?? 1e9));
    if (!inRange.length) continue;
    if (e.type === 'interceptor') {  // launch a physical interceptor that has to fly and collide
      const busy = new Set(S.interceptors.filter((i) => i.alive).map((i) => i.target));
      const tgt = inRange.find((d) => !busy.has(d)) ;
      if (!tgt) continue;
      S.interceptors.push({ id: `INT-${++S.launches}`, type: 'interceptor', x: e.x, y: e.y, z: e.z + 20, target: tgt, alive: true, t0: S.t, speed: st.speed_mps });
      e.ammo--; e.ready = S.t + st.reload_s;
      log(S, 'launch', `${e.id} launches INT-${S.launches} at ${tgt.id}`, { id: e.id, target: tgt.id });
      continue;
    }
    const targets = e.type === 'jammer' ? inRange.slice(0, st.max_concurrent_targets) : [inRange.sort((a, b) => dist3(a, e) - dist3(b, e))[0]];
    for (const d of targets) {
      const p = pk(st, d.type), roll = S.dice(), hit = roll < p;
      S.shots++; if (hit) S.hits++;
      S.fx.push({ kind: 'tracer', a: { x: e.x, y: e.y, z: e.z }, b: { x: d.x, y: d.y, z: d.z }, hit, t0: S.t, jam: e.type === 'jammer' });
      if (e.type === 'jammer') {
        if (hit) {  // link lost: the drone falls and its warhead goes off where it lands
          d.alive = false; d.state = 'JAMMED';
          log(S, 'jammed', `${e.id} jams ${d.id} (p=${p} roll ${roll.toFixed(2)}): link lost`, { id: d.id, by: e.id, p, roll });
          collide(S, 'jam_crash', d.id, e.id, d.x, d.y);
          blast(S, d.x, d.y, STATS[d.type].damage?.payload_hp || 0, STATS[d.type].damage?.blast_radius_m || 0, `${d.id} crash`);
        }
      } else {
        log(S, 'engage', `${e.id} ${hit ? 'hits' : 'misses'} ${d.id} (p=${p} roll ${roll.toFixed(2)})`, { id: d.id, by: e.id, p, roll, hit });
        if (hit) damage(S, d, st.damage_on_hit, e.id);
        if (e.ammo > 0) e.ammo--;
      }
    }
    e.ready = S.t + Math.max(w, st.reload_s);
  }
}

// Interceptors chase their target (pure pursuit) and roll p_kill on contact; either way the interceptor is spent.
function chase(S) {
  const st = STATS.interceptor;
  for (const i of S.interceptors) {
    if (!i.alive) continue;
    const d = i.target;
    if (!d.alive || S.t - i.t0 > 600) { i.alive = false; continue; }  // target gone or out of battery
    const gap = dist3(i, d), stepM = i.speed * DT;
    if (gap <= Math.max(15, stepM)) {
      const p = pk(st, d.type), roll = S.dice(), hit = roll < p;
      i.alive = false; S.shots++; if (hit) S.hits++;
      S.rec.collisions.push({ t: S.t, a: i.id, b: d.id, kind: hit ? 'interceptor_hit' : 'interceptor_miss', x: r1(d.x), y: r1(d.y) });
      log(S, 'engage', `${i.id} ${hit ? 'collides with' : 'misses'} ${d.id} (p=${p} roll ${roll.toFixed(2)})`, { id: d.id, by: i.id, p, roll, hit });
      S.fx.push({ kind: 'boom', x: d.x, y: d.y, z: d.z, r: hit ? 50 : 20, t0: S.t, small: !hit });
      if (hit) damage(S, d, st.damage_on_hit, i.id);
      continue;
    }
    i.x += ((d.x - i.x) / gap) * stepM; i.y += ((d.y - i.y) / gap) * stepM; i.z += ((d.z - i.z) / gap) * stepM;
  }
}

export function step(S) {
  if (S.done) return;
  S.t += DT;
  for (const d of S.drones) if (d.alive && S.t >= d.t0) {
    if (d.state === 'PENDING') { d.state = 'INBOUND'; log(S, 'launch', `${d.id} enters from ${d.entrySide}`, { id: d.id }); }
    moveDrone(S, d);
  }
  if (S.t >= S.nextScan) { scan(S); trackLinks(S); S.nextScan = S.t + 1; }
  defend(S);
  chase(S);
  S.fx = S.fx.filter((f) => S.t - f.t0 < 6);
  for (const d of S.drones) if (!d.alive && d.endT == null) d.endT = S.t;
  if (Number.isInteger(S.t)) recordTracks(S);
  if (S.t >= S.end) {
    S.done = true;
    S.links = []; trackLinks(S);  // close every open detection interval at END
    log(S, 'end', `Run complete at t=${S.t}s`);
  }
}

const active = (S) => S.drones.some((d) => d.alive && S.t >= d.t0) || S.interceptors.some((i) => i.alive);

// Fast-forward to END: simulate while something flies, jump straight over the quiet gaps between waves.
export function runToEnd(S) {
  while (!S.done) {
    if (!active(S)) {
      const next = Math.min(S.end, ...S.drones.filter((d) => d.alive && d.t0 > S.t).map((d) => d.t0));
      const to = Math.floor(next / DT) * DT - DT;
      if (to > S.t) { S.t = to; S.nextScan = Math.min(S.nextScan, S.t + DT); }
    }
    step(S);
  }
  return S;
}

// 1 Hz truth tracks for every flying drone (plus its final position) and interceptor.
const r1 = (v) => Math.round(v * 10) / 10, r6 = (v) => Math.round(v * 1e6) / 1e6;
function row(S, e, hp, state) {
  const [lon, lat] = toLL(S.T, e.x, e.y);
  return { t: S.t, id: e.id, x: r1(e.x), y: r1(e.y), z: r1(e.z), lat: r6(lat), lon: r6(lon), alt: r1(e.z), agl: r1(e.z - heightAt(S.T, e.x, e.y)), hp, state };
}
function recordTracks(S) {
  for (const d of S.drones) {
    if (S.t < d.t0 || d.tracked) continue;
    if (!d.alive) d.tracked = true;  // one last row at the point it ended
    S.rec.tracks.push(row(S, d, r1(d.hp), d.state));
  }
  for (const i of S.interceptors) {
    if (i.tracked) continue;
    if (!i.alive) i.tracked = true;
    S.rec.tracks.push(row(S, i, null, i.alive ? 'CHASE' : 'SPENT'));
  }
}

function collide(S, kind, a, b, x, y) {
  S.rec.collisions.push({ t: S.t, a, b, kind, x: r1(x), y: r1(y) });
}

// Full run object: everything needed to rebuild training samples (schema in docs/DATA-PIPELINE.md).
export function record(S, meta = {}) {
  const ll = (e) => { const [lon, lat] = toLL(S.T, e.x, e.y); return { lat: r6(lat), lon: r6(lon) }; };
  const { tracks, detections, collisions, damage: dmg } = S.rec;
  return {
    id: meta.id, worldId: meta.worldId, schema: 'oasis.run/1', meta, cfg: S.cfg,
    tile: { lat: S.T.lat, lon: S.T.lon, size_m: S.T.size, west: S.T.west, south: S.T.south, east: S.T.east, north: S.T.north },
    world: S.fixed.map((e) => ({ id: e.id, type: e.type, cat: e.cat, side: e.side, name: e.name, real: !!e.real, x: r1(e.x), y: r1(e.y), z: r1(e.z), ...ll(e), hp: r1(e.hp), hp_max: e.hpMax, alive: e.alive, state: e.state, ammo: e.ammo })),
    drones: S.drones.map((d) => ({
      id: d.id, type: d.type, wave: d.wave, entry: d.entrySide, target: d.target, t0: d.t0, state: d.state,
      first_detected_t: d.firstSeen ?? null, detected_by: [...d.seenBy], end_t: d.endT ?? null,
      agl_cruise: r1(d.agl), speed: d.speed, path: d.path.map(([x, y]) => [r1(x), r1(y)]),
    })),
    tracks, detections, collisions, damage: dmg, events: S.events,
    summary: summary(S, meta, false),
  };
}

// After-action report: the "points" an LLM (or a judge) reads.
export function summary(S, meta, withEvents = true) {
  const by = (st) => S.drones.filter((d) => d.state === st).map((d) => d.id);
  const seen = S.drones.filter((d) => d.firstSeen != null);
  return {
    ...meta,
    duration_s: S.t,
    hostile: {
      launched: S.drones.length, killed: by('KILLED'), jammed: by('JAMMED'), impacts: by('IMPACT'),
      decoys_reached_target: by('DECOY END'), recon_exited: by('EXITED'),
      never_detected: S.drones.filter((d) => d.firstSeen == null).map((d) => d.id),
    },
    defence: { shots: S.shots, hits: S.hits, interceptors_launched: S.launches },
    counts: { tracks: S.rec.tracks.length, detections: S.rec.detections.length, collisions: S.rec.collisions.length, damage: S.rec.damage.length },
    detection: {
      mean_time_to_detect_s: seen.length ? Math.round(seen.reduce((a, d) => a + d.firstSeen - d.t0, 0) / seen.length) : null,
    },
    fixed_assets: S.fixed.map((e) => ({ id: e.id, type: e.type, hp: Math.round(e.hp), hp_max: e.hpMax, alive: e.alive })),
    ...(withEvents ? { events: S.events } : {}),
  };
}
