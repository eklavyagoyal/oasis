// Game control panel (right rail "GAME" tab): seed engine, match controls, layers, order of battle, kill feed, after-action.
import A from './assets.json';
import { DEFAULTS } from './seed.js';

const MIX = ['shahed136', 'gerbera', 'lancet', 'fpv_analog', 'fpv_fiber', 'orlan10', 'zala', 'supercam', 'dji_mavic3'];
const LABEL = Object.fromEntries(A.categories.attackers.map((a) => [a.id, (a.label || a.id).split(' (')[0]]));
const KIND = { destroyed: 'bad', impact: 'bad', detect: 'det', jammed: 'jam', launch: 'dim', exit: 'dim', end: 'dim' };
const clock = (t) => `T+${String(Math.floor(t / 60)).padStart(2, '0')}:${String(Math.floor(t % 60)).padStart(2, '0')}`;
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => `&#${c.charCodeAt(0)};`);
const dice = () => Math.floor(Math.random() * 99999) + 1;

export function createGamePanel(root, h) {
  root.innerHTML = `
  <div class="rail-heading">SEED ENGINE <span class="section-number">01</span></div>
  <div class="gp-row"><label>World seed</label><input type="number" data-k="worldSeed" min="1"><button class="gp-dice" data-dice="worldSeed" title="Reroll">⚄</button></div>
  <div class="gp-row"><label>Scenario seed</label><input type="number" data-k="scenarioSeed" min="1"><button class="gp-dice" data-dice="scenarioSeed" title="Reroll">⚄</button></div>
  <div class="gp-row"><label>Tile size</label><div class="gp-seg" data-seg="tileKm"><button data-v="10">10 KM</button><button data-v="16">16 KM</button></div></div>
  <details class="gp-opts"><summary>Options before generating</summary>
    <div class="gp-row"><label>Drones <b class="gp-num" data-out="drones"></b></label><input type="range" min="1" max="30" data-k="drones"></div>
    <div class="gp-row"><label>Entry side</label><select data-k="entry">${['random', 'N', 'E', 'S', 'W'].map((v) => `<option>${v}</option>`).join('')}</select></div>
    <div class="gp-row"><label>Wave span (s)</label><input type="number" min="0" step="10" data-k="waveSpanS"></div>
    <div class="gp-sub">ATTACKER MIX</div>
    <div class="gp-mix">${MIX.map((id) => `<label><input type="checkbox" data-mix="${id}"> ${esc(LABEL[id] || id)}</label>`).join('')}</div>
    <div class="gp-sub">FORCES</div>
    <div class="gp-mix">${['defence', 'radar', 'acoustic'].map((k) => `<label><input type="checkbox" data-k="${k}"> ${k}</label>`).join('')}</div>
  </details>
  <div class="gp-btns"><button class="gp-btn primary" data-act="generate">GENERATE WORLD</button><button class="gp-btn" data-act="scenario">NEW SCENARIO · SAME WORLD</button></div>

  <div class="rail-heading">MATCH <span class="section-number">02</span></div>
  <div class="gp-btns three"><button class="gp-btn" data-act="start">START</button><button class="gp-btn" data-act="pause">PAUSE</button><button class="gp-btn" data-act="reset">RESET</button></div>
  <div class="gp-clock"><span data-out="clock">T+00:00</span><small data-out="status">NO MATCH LOADED</small></div>

  <div class="rail-heading">LAYERS <span class="section-number">03</span></div>
  <div class="gp-mix">${[['coverage', 'Coverage rings'], ['links', 'Sensor links'], ['labels', 'Labels']].map(([k, l]) => `<label><input type="checkbox" checked data-opt="${k}"> ${l}</label>`).join('')}</div>

  <div class="rail-heading">ORDER OF BATTLE <span class="section-number">04</span></div>
  <div class="gp-sub friendly">OUR SIDE</div><div class="gp-oob" data-list="fixed"><div class="no-observation">Generate a world.</div></div>
  <div class="gp-sub hostile">HOSTILE</div><div class="gp-oob" data-list="drones"><div class="no-observation">No scenario.</div></div>

  <div class="rail-heading">KILL FEED <span class="section-number">05</span></div>
  <div class="gp-feed" data-out="feed"><div class="no-observation">No events yet.</div></div>

  <section class="gp-aar" data-out="aar" hidden></section>`;

  const $ = (s) => root.querySelector(s), $$ = (s) => [...root.querySelectorAll(s)];
  let cfg = { ...DEFAULTS, mix: [...DEFAULTS.mix] }, lastEv = -1;
  const rows = { fixed: new Map(), drones: new Map() };

  function syncInputs() {
    $$('[data-k]').forEach((el) => { el.type === 'checkbox' ? (el.checked = !!cfg[el.dataset.k]) : (el.value = cfg[el.dataset.k]); });
    $$('[data-mix]').forEach((el) => { el.checked = cfg.mix.includes(el.dataset.mix); });
    $$('[data-seg] button').forEach((b) => b.classList.toggle('active', +b.dataset.v === cfg.tileKm));
    $('[data-out="drones"]').textContent = cfg.drones;
  }
  function readCfg() {
    $$('[data-k]').forEach((el) => {
      const k = el.dataset.k;
      cfg[k] = el.type === 'checkbox' ? el.checked : el.type === 'number' || el.type === 'range' ? Number(el.value) || DEFAULTS[k] : el.value;
    });
    const mix = $$('[data-mix]').filter((el) => el.checked).map((el) => el.dataset.mix);
    cfg.mix = mix.length ? mix : [...DEFAULTS.mix];
    return { ...cfg, mix: [...cfg.mix] };
  }

  root.addEventListener('input', (e) => { if (e.target.dataset.k === 'drones') $('[data-out="drones"]').textContent = e.target.value; });
  root.addEventListener('change', (e) => { if (e.target.dataset.opt) h.setOpt(e.target.dataset.opt, e.target.checked); });
  root.addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b) return;
    if (b.dataset.dice) { $(`[data-k="${b.dataset.dice}"]`).value = dice(); return; }
    if (b.dataset.v) { cfg.tileKm = +b.dataset.v; syncInputs(); return; }
    const act = b.dataset.act;
    if (act === 'generate') h.generateWorld(readCfg());
    else if (act === 'scenario') h.newScenario(readCfg());
    else if (act === 'start') h.start();
    else if (act === 'pause') h.pause();
    else if (act === 'reset') h.reset();
    else if (act === 'download') h.download();
  });

  function row(e, side) {
    const el = document.createElement('div');
    el.className = `gp-unit ${side}`;
    el.innerHTML = `<span class="id">${esc(e.id)}</span><span class="type">${esc(LABEL[e.type] || e.type)}</span><span class="badge"></span><div class="hp"><i></i></div>`;
    return { el, badge: el.querySelector('.badge'), bar: el.querySelector('.hp i'), key: '' };
  }
  function list(name, items, side) {
    const box = $(`[data-list="${name}"]`), map = rows[name];
    const ids = items.map((e) => e.id).join('|');
    if (box.dataset.ids !== ids) {
      box.dataset.ids = ids; map.clear(); box.innerHTML = items.length ? '' : '<div class="no-observation">None.</div>';
      for (const e of items) { const r = row(e, side); map.set(e.id, r); box.appendChild(r.el); }
    }
    for (const e of items) {
      const r = map.get(e.id), pct = e.hpMax ? Math.round((100 * e.hp) / e.hpMax) : 0, key = `${e.state}|${pct}|${e.alive}`;
      if (r.key === key) continue;
      r.key = key;
      r.badge.textContent = e.state || (e.alive ? 'IDLE' : 'DESTROYED');
      r.badge.dataset.s = r.badge.textContent;
      r.bar.style.width = `${pct}%`;
      r.el.classList.toggle('dead', !e.alive);
    }
  }
  function feed(S) {
    if (S.events.length === lastEv) return;
    lastEv = S.events.length;
    const ev = S.events.slice(-8).reverse();
    $('[data-out="feed"]').innerHTML = ev.length ? ev.map((v) => {
      const c = v.kind === 'engage' ? (v.hit ? 'hit' : 'miss') : KIND[v.kind] || '';
      return `<div class="gp-ev ${c}"><time>${clock(v.t)}</time><span>${esc(v.text)}</span></div>`;
    }).join('') : '<div class="no-observation">No events yet.</div>';
  }

  function update(S) {
    if (!S) return;
    const live = S.drones.filter((d) => d.alive && d.state !== 'PENDING').length;
    const det = S.drones.filter((d) => d.firstSeen != null || d.seenBy?.size).length;
    const imp = S.drones.filter((d) => d.state === 'IMPACT').length;
    $('[data-out="clock"]').textContent = clock(S.t);
    $('[data-out="status"]').textContent = `${live} HOSTILE · ${det} DETECTED · ${imp} IMPACTS${S.done ? ' · ENDED' : ''}`;
    list('fixed', S.fixed, 'friendly');
    list('drones', S.drones, 'hostile');
    feed(S);
  }

  function setGame(G) {
    if (G?.cfg) cfg = { ...cfg, ...G.cfg, mix: [...(G.cfg.mix || cfg.mix)] };
    syncInputs();
    lastEv = -1;
    $('[data-out="aar"]').hidden = true;
    if (G?.S) update(G.S);
  }

  function showSummary(R) {
    const H = R.hostile || {}, D = R.defence || {}, n = (v) => (Array.isArray(v) ? v.length : v ?? 0);
    const dmg = (R.fixed_assets || []).filter((a) => a.hp < a.hp_max);
    const big = [['LAUNCHED', H.launched], ['KILLED', H.killed], ['JAMMED', H.jammed], ['IMPACTS', H.impacts], ['NEVER DETECTED', H.never_detected]];
    const el = $('[data-out="aar"]');
    el.innerHTML = `<div class="rail-heading">AFTER-ACTION <span class="section-number">06</span></div>
      <div class="gp-big">${big.map(([l, v]) => `<div><b>${n(v)}</b><small>${l}</small></div>`).join('')}</div>
      <div class="gp-kv"><span>Shots / hits</span><b>${D.shots ?? 0} / ${D.hits ?? 0}</b></div>
      <div class="gp-kv"><span>Mean time to detect</span><b>${R.detection?.mean_time_to_detect_s ?? '—'}${R.detection?.mean_time_to_detect_s != null ? ' s' : ''}</b></div>
      <div class="gp-kv"><span>Duration</span><b>${clock(R.duration_s || 0)}</b></div>
      <div class="gp-sub">DAMAGED ASSETS</div>
      <div class="gp-dmg">${dmg.length ? dmg.map((a) => `<div class="${a.alive ? '' : 'dead'}"><span>${esc(a.id)}</span><b>${a.alive ? `${a.hp}/${a.hp_max} HP` : 'DESTROYED'}</b></div>`).join('') : '<div class="no-observation">None damaged.</div>'}</div>
      <button class="gp-btn primary wide" data-act="download">DOWNLOAD WORLD + REPORT JSON</button>`;
    el.hidden = false;
    el.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }

  syncInputs();
  return { setGame, update, showSummary };
}
