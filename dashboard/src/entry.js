import * as maplibregl from 'maplibre-gl';
import mapWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
maplibregl.setWorkerUrl(mapWorkerUrl);  // the library ships its worker separately; bundle it and point at it
import 'maplibre-gl/dist/maplibre-gl.css';
import './entry.css';
import UKRAINE from './game/ukraine.json';
import ASSETS from './game/assets.json';
import { DEFAULTS } from './game/seed.js';

const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';
const UKRAINE_CENTER = [31.1656, 48.3794];
const SEED_MAX = 4294967295;
const DURATIONS = [3600, 21600, 86400];

function countFrom(data, keys) {
  for (const key of keys) {
    let value = data?.[key];
    if (Array.isArray(value)) return value.length;
    if (value && typeof value === 'object') value = value.count;
    if (value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value))) return Number(value);
  }
  return null;
}

function errorMessage(error) {
  if (error instanceof Error) return error.message || error.name;
  if (typeof error === 'string') return error;
  try { return JSON.stringify(error) || 'Unknown error'; } catch { return 'Unknown error'; }
}

export function createEntry({ onGenerate, onReplay, onExport, getCounts, onBakedDemo } = {}) {
  const root = document.createElement('section');
  root.id = 'oasis-entry';
  root.setAttribute('aria-label', 'OASIS simulation entry');
  root.innerHTML = `
    <div class="oasis-map" id="oasis-map" role="region" aria-label="Interactive globe with Ukraine highlighted"></div>
    <div class="oasis-shade" aria-hidden="true"></div>
    <header class="oasis-topbar">
      <div class="oasis-brand">
        <svg class="oasis-mark" viewBox="0 0 48 48" aria-hidden="true">
          <circle cx="24" cy="24" r="20"/><circle cx="24" cy="24" r="13"/>
          <path d="M4 24h10m20 0h10M24 4v10m0 20v10M17 24h14M24 17v14"/>
          <circle class="oasis-mark-core" cx="24" cy="24" r="3"/>
        </svg>
        <div><div class="oasis-wordmark">OASIS</div><div class="oasis-submark">AIRSPACE DEFENCE SIMULATOR</div></div>
      </div>
      <div class="oasis-status-strip" aria-label="Local simulation status">
        <div class="oasis-metric"><span>UTC</span><time id="oasis-utc" datetime="">--:--:--Z</time></div>
        <div class="oasis-metric"><span>LOCAL WORLDS</span><strong id="oasis-world-count">—</strong></div>
        <div class="oasis-metric"><span>LOCAL RUNS</span><strong id="oasis-run-count">—</strong></div>
        <button class="oasis-button oasis-export" id="oasis-export" type="button" hidden>EXPORT DATA</button>
      </div>
    </header>

    <main class="oasis-hero">
      <div class="oasis-kicker"><span class="oasis-kicker-dot"></span>UKRAINE SECTOR <i></i> SEED-DRIVEN EXERCISE</div>
      <h1>OASIS</h1>
      <p class="oasis-intro">SYNTHETIC SCENARIO GENERATOR / UKRAINE</p>
      <div class="oasis-hero-actions">
        <button class="oasis-button oasis-button-primary" id="enter-simulation" type="button">ENTER SIMULATION <span aria-hidden="true">↗</span></button>
        <button class="oasis-button oasis-button-secondary" id="replay-hero" type="button">REPLAY HERO</button>
      </div>
      <div class="oasis-provenance"><span class="oasis-provenance-line"></span><span>Physics-engine scenarios over real terrain · every record traceable to its cause · synthetic data, not operational guidance.</span></div>
      <p class="oasis-action-status" id="oasis-action-status" role="status" aria-live="polite" hidden></p>
    </main>

    <nav class="oasis-map-controls" aria-label="Map view controls">
      <button class="oasis-control is-active" type="button" data-projection="globe" aria-pressed="true">3D GLOBE</button>
      <button class="oasis-control" type="button" data-projection="mercator" aria-pressed="false">2D MAP</button>
      <span class="oasis-control-divider" aria-hidden="true"></span>
      <button class="oasis-control oasis-focus-sector" type="button" id="oasis-focus-sector">FOCUS UKRAINE</button>
    </nav>
    <aside class="oasis-map-readout" aria-live="polite">
      <div class="oasis-map-state"><span class="oasis-state-dot"></span><span id="oasis-map-status">BASEMAP INITIALIZING</span></div>
      <p id="oasis-map-warning" hidden></p>
      <div class="oasis-map-credit">BASE MAP © OPENSTREETMAP CONTRIBUTORS · © CARTO</div>
    </aside>

    <div class="oasis-modal" id="seed-dialog-wrap" hidden>
      <div class="oasis-modal-backdrop"></div>
      <section class="oasis-dialog" id="seed-dialog" role="dialog" aria-modal="true" aria-labelledby="seed-title" aria-describedby="seed-description" tabindex="-1">
        <header class="oasis-dialog-head">
          <div><span class="oasis-kicker">SCENARIO CONFIGURATION</span><h2 id="seed-title">Seed the exercise</h2></div>
          <button class="oasis-close" type="button" id="seed-close" aria-label="Close scenario configuration">×</button>
        </header>
        <p class="oasis-dialog-description" id="seed-description">Seeds make runs reproducible. Keep the world seed to reuse terrain and fixed assets; change the scenario seed to generate a new run.</p>
        <form id="seed-form" novalidate>
          <div class="oasis-seed-grid">
            <label class="oasis-field" for="world-seed"><span>WORLD SEED</span><input id="world-seed" name="worldSeed" type="number" inputmode="numeric" min="0" max="4294967295" step="1" required></label>
            <label class="oasis-field" for="scenario-seed"><span>SCENARIO SEED</span><input id="scenario-seed" name="scenarioSeed" type="number" inputmode="numeric" min="0" max="4294967295" step="1" required></label>
          </div>
          <div class="oasis-seed-grid oasis-seed-grid-three">
            <label class="oasis-field" for="tile-size"><span>TILE SIZE</span><select id="tile-size" name="tileKm"><option value="10">10 km</option><option value="16">16 km</option><option value="20">20 km</option></select></label>
            <label class="oasis-field" for="run-duration"><span>RUN DURATION</span><select id="run-duration" name="durationS"><option value="3600">1 hour</option><option value="21600">6 hours</option><option value="86400">24 hours</option></select></label>
            <label class="oasis-field" for="drone-count"><span>ATTACKER COUNT <output id="drone-count-value" for="drone-count">6</output></span><input id="drone-count" name="drones" type="range" min="1" max="30" step="1"></label>
          </div>
          <fieldset class="oasis-fieldset">
            <legend>ATTACKER MIX <small>Choose one or more asset types</small></legend>
            <div class="oasis-attacker-options" id="attacker-options"></div>
          </fieldset>
          <div class="oasis-seed-grid oasis-seed-grid-two">
            <label class="oasis-field" for="entry-direction"><span>ENTRY DIRECTION</span><select id="entry-direction" name="entry"><option value="random">Random</option><option value="N">North</option><option value="E">East</option><option value="S">South</option><option value="W">West</option></select></label>
            <fieldset class="oasis-fieldset oasis-toggle-fieldset"><legend>SIMULATION OPTIONS</legend>
              <label class="oasis-check"><input type="checkbox" name="defence"><span>Defence assets</span></label>
              <label class="oasis-check"><input type="checkbox" name="radar"><span>Radar</span></label>
              <label class="oasis-check"><input type="checkbox" name="acoustic"><span>Acoustic sensors</span></label>
            </fieldset>
          </div>
          <p class="oasis-seed-note">This browser run is a simplified model. Tracked objects and outcomes are synthetic; sensor data and real recordings are not supplied.</p>
          <div class="oasis-generation-status" id="seed-status" role="status" aria-live="polite" hidden></div>
          <button class="oasis-button oasis-button-primary oasis-generate" id="generate-world" type="submit">GENERATE WORLD <span aria-hidden="true">↗</span></button>
          <button class="oasis-button oasis-button-baked" id="use-baked-demo" type="button" hidden>USE BAKED DEMO SECTOR</button>
        </form>
      </section>
    </div>`;

  document.body.append(root);
  const $ = (selector) => root.querySelector(selector);
  const modal = $('#seed-dialog-wrap');
  const dialog = $('#seed-dialog');
  const form = $('#seed-form');
  const enterButton = $('#enter-simulation');
  const replayButton = $('#replay-hero');
  const closeButton = $('#seed-close');
  const submitButton = $('#generate-world');
  const bakedButton = $('#use-baked-demo');
  const seedStatus = $('#seed-status');
  const actionStatus = $('#oasis-action-status');
  const mapStatus = $('#oasis-map-status');
  const mapWarning = $('#oasis-map-warning');
  let map = null;
  let destroyed = false;
  let busy = false;
  let previousFocus = null;
  let lastConfig = null;
  let mapReady = false;
  let mapTimeout = 0;

  function setActionStatus(message, isError = false) {
    actionStatus.textContent = message;
    actionStatus.hidden = !message;
    actionStatus.classList.toggle('is-error', isError);
  }

  function setSeedStatus(message, isError = false) {
    seedStatus.textContent = message;
    seedStatus.hidden = !message;
    seedStatus.classList.toggle('is-error', isError);
  }

  function setBusy(value) {
    busy = value;
    submitButton.disabled = value;
    closeButton.disabled = value;
    bakedButton.disabled = value;
    submitButton.setAttribute('aria-busy', String(value));
  }

  function updateTime() {
    const now = new Date();
    const stamp = now.toISOString();
    $('#oasis-utc').dateTime = stamp;
    $('#oasis-utc').textContent = `${stamp.slice(11, 19)}Z`;
  }

  async function refreshCounts() {
    if (typeof getCounts !== 'function') return;
    try {
      const counts = await getCounts();
      if (destroyed || !root.isConnected) return;
      const worlds = countFrom(counts, ['worlds', 'worldCount', 'worldsCount']);
      const runs = countFrom(counts, ['runs', 'runCount', 'runsCount']);
      $('#oasis-world-count').textContent = worlds === null ? '—' : new Intl.NumberFormat().format(worlds);
      $('#oasis-run-count').textContent = runs === null ? '—' : new Intl.NumberFormat().format(runs);
      $('#oasis-world-count').title = worlds === null ? 'Saved world count unavailable' : 'Saved worlds in local storage';
      $('#oasis-run-count').title = runs === null ? 'Saved run count unavailable' : 'Saved runs in local storage';
    } catch {
      $('#oasis-world-count').textContent = '—';
      $('#oasis-run-count').textContent = '—';
    }
  }

  function buildAttackerOptions() {
    const host = $('#attacker-options');
    const attackers = ASSETS?.categories?.attackers || [];
    for (const [index, attacker] of attackers.entries()) {
      const label = document.createElement('label');
      label.className = 'oasis-check oasis-attacker';
      const input = document.createElement('input');
      input.type = 'checkbox';
      input.name = 'mix';
      input.value = attacker.id;
      input.checked = (DEFAULTS.mix || []).includes(attacker.id) || (!DEFAULTS.mix?.length && index === 0);
      const text = document.createElement('span');
      text.textContent = attacker.label || attacker.id;
      label.append(input, text);
      host.append(label);
    }
  }

  function openDialog() {
    if (destroyed) return;
    previousFocus = document.activeElement;
    modal.hidden = false;
    $('#world-seed').focus();
    setSeedStatus('');
    bakedButton.hidden = true;
  }

  function closeDialog(restoreFocus = true) {
    if (busy) return;
    modal.hidden = true;
    if (restoreFocus && previousFocus?.isConnected) previousFocus.focus();
  }

  function readSeed(id, label) {
    const field = $(`#${id}`);
    const value = Number(field.value);
    if (field.value.trim() === '' || !Number.isInteger(value) || value < 0 || value > SEED_MAX) {
      field.focus();
      throw new Error(`${label} must be an integer from 0 to ${SEED_MAX}.`);
    }
    return value;
  }

  function readConfig() {
    const worldSeed = readSeed('world-seed', 'World seed');
    const scenarioSeed = readSeed('scenario-seed', 'Scenario seed');
    const drones = Number($('#drone-count').value);
    const tileKm = Number($('#tile-size').value);
    const durationS = Number($('#run-duration').value);
    const mix = [...form.querySelectorAll('input[name="mix"]:checked')].map((input) => input.value);
    if (!Number.isInteger(drones) || drones < 1 || drones > 30) throw new Error('Attacker count must be from 1 to 30.');
    if (![10, 16, 20].includes(tileKm)) throw new Error('Choose a tile size of 10, 16 or 20 km.');
    if (!DURATIONS.includes(durationS)) throw new Error('Choose a run duration of 1, 6 or 24 hours.');
    if (!mix.length) throw new Error('Select at least one attacker type.');
    return {
      worldSeed, scenarioSeed, tileKm, durationS, drones, mix,
      entry: form.elements.entry.value,
      defence: form.elements.defence.checked,
      radar: form.elements.radar.checked,
      acoustic: form.elements.acoustic.checked,
    };
  }

  function setMapFailure(error) {
    const detail = errorMessage(error);
    mapStatus.textContent = 'MAP UNAVAILABLE';
    mapWarning.textContent = `WebGL map unavailable${detail ? `: ${detail}` : ''}. Seed generation and replay are still available.`;
    mapWarning.hidden = false;
    root.classList.add('map-unavailable');
    root.querySelectorAll('[data-projection], #oasis-focus-sector').forEach((button) => { button.disabled = true; });
  }

  function initMap() {
    try {
      map = new maplibregl.Map({
        container: $('#oasis-map'),
        style: MAP_STYLE,
        center: [29, 44],
        zoom: 2.15,
        minZoom: 1.4,
        maxZoom: 17,
        maxPitch: 65,
        dragRotate: true,
        attributionControl: { compact: true, customAttribution: '© OpenStreetMap contributors · © CARTO' },
      });
      map.on('error', (event) => {
        if (!mapReady && event?.error) setMapFailure(event.error);
      });
      map.once('load', () => {
        if (destroyed || !map) return;
        mapReady = true;
        window.clearTimeout(mapTimeout);
        mapWarning.hidden = true;
        root.classList.remove('map-unavailable');
        root.querySelectorAll('[data-projection], #oasis-focus-sector').forEach((button) => { button.disabled = false; });
        try {
          if (typeof map.setProjection === 'function') map.setProjection({ type: 'globe' });
          else root.querySelectorAll('[data-projection]').forEach((button) => { button.disabled = true; });
          map.addSource('oasis-ukraine', { type: 'geojson', data: { type: 'FeatureCollection', features: [UKRAINE] } });
          map.addLayer({
            id: 'oasis-ukraine-fill', type: 'fill', source: 'oasis-ukraine',
            paint: { 'fill-color': '#d4af37', 'fill-opacity': 0.12 },
          });
          map.addLayer({
            id: 'oasis-ukraine-outline', type: 'line', source: 'oasis-ukraine',
            paint: { 'line-color': '#f0d060', 'line-width': 2, 'line-opacity': 0.95 },
          });
          map.addSource('oasis-sector-label', {
            type: 'geojson', data: {
              type: 'FeatureCollection', features: [{
                type: 'Feature', properties: { label: 'UKRAINE' },
                geometry: { type: 'Point', coordinates: UKRAINE_CENTER },
              }],
            },
          });
          map.addLayer({
            id: 'oasis-sector-label', type: 'symbol', source: 'oasis-sector-label',
            layout: { 'text-field': ['get', 'label'], 'text-font': ['Open Sans Bold'], 'text-size': 12, 'text-letter-spacing': 0.22 },
            paint: { 'text-color': '#f0d060', 'text-halo-color': '#05070b', 'text-halo-width': 2 },
          });
          mapStatus.textContent = typeof map.setProjection === 'function'
            ? 'GLOBE READY · UKRAINE HIGHLIGHTED'
            : 'MAP READY · GLOBE PROJECTION UNAVAILABLE';
          map.resize();
        } catch (error) {
          setMapFailure(error);
        }
      });
      mapTimeout = window.setTimeout(() => {
        if (!mapReady && !destroyed) setMapFailure('the basemap did not finish loading');
      }, 18000);
    } catch (error) {
      setMapFailure(error);
    }
  }

  async function generate(cfg, isBaked = false) {
    if (typeof onGenerate !== 'function') {
      setSeedStatus('Generation is unavailable until the simulation engine is connected.', true);
      return;
    }
    lastConfig = cfg;
    bakedButton.hidden = true;
    setBusy(true);
    setSeedStatus(isBaked ? 'Opening the baked demo sector…' : 'Preparing the seeded world…');
    const progress = (message) => setSeedStatus(String(message || 'Generating…'));
    try {
      await onGenerate(cfg, progress);
      if (isBaked && typeof onBakedDemo === 'function') {
        try { await onBakedDemo(cfg, progress); } catch { /* generation remains authoritative */ }
      }
      setBusy(false);
      hide();
    } catch (error) {
      setBusy(false);
      const message = errorMessage(error);
      setSeedStatus(message || 'World generation failed.', true);
      if (!isBaked && /terrain|terrarium|elevation|\bdem\b/i.test(message)) bakedButton.hidden = false;
    }
  }

  function setProjection(type) {
    if (!map) return;
    if (typeof map.setProjection !== 'function') {
      setActionStatus('Projection controls require a newer MapLibre build.', true);
      return;
    }
    try {
      map.setProjection?.({ type });
      root.querySelectorAll('[data-projection]').forEach((button) => {
        const active = button.dataset.projection === type;
        button.classList.toggle('is-active', active);
        button.setAttribute('aria-pressed', String(active));
      });
      mapStatus.textContent = type === 'globe' ? '3D GLOBE · UKRAINE HIGHLIGHTED' : '2D MAP · UKRAINE HIGHLIGHTED';
    } catch (error) {
      setActionStatus(`Map view could not be changed: ${errorMessage(error)}`, true);
    }
  }

  function show() {
    if (destroyed) return;
    root.hidden = false;
    modal.hidden = true;
    refreshCounts();
    requestAnimationFrame(() => { if (map && !destroyed) map.resize(); });
  }

  function hide() {
    root.hidden = true;
    modal.hidden = true;
  }

  buildAttackerOptions();
  $('#world-seed').value = String(DEFAULTS.worldSeed);
  $('#scenario-seed').value = String(DEFAULTS.scenarioSeed);
  $('#tile-size').value = String(DEFAULTS.tileKm);
  $('#run-duration').value = '21600';
  $('#drone-count').value = String(DEFAULTS.drones);
  form.elements.entry.value = DEFAULTS.entry;
  form.elements.defence.checked = DEFAULTS.defence;
  form.elements.radar.checked = DEFAULTS.radar;
  form.elements.acoustic.checked = DEFAULTS.acoustic;
  $('#drone-count').addEventListener('input', (event) => { $('#drone-count-value').value = event.target.value; });
  enterButton.disabled = typeof onGenerate !== 'function';
  replayButton.disabled = typeof onReplay !== 'function';
  if (typeof onExport === 'function') $('#oasis-export').hidden = false;

  enterButton.addEventListener('click', openDialog);
  closeButton.addEventListener('click', () => closeDialog());
  replayButton.addEventListener('click', async () => {
    if (typeof onReplay !== 'function') return;
    replayButton.disabled = true;
    setActionStatus('Opening the original replay…');
    try {
      await onReplay();
      replayButton.disabled = false;
      hide();
    } catch (error) {
      setActionStatus(errorMessage(error), true);
      replayButton.disabled = false;
    }
  });
  $('#oasis-export').addEventListener('click', async () => {
    if (typeof onExport !== 'function') return;
    try {
      await onExport();
      setActionStatus('Export requested.');
    } catch (error) {
      setActionStatus(errorMessage(error), true);
    }
  });
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    setSeedStatus('');
    try {
      const cfg = readConfig();
      if (!form.checkValidity()) { form.reportValidity(); return; }
      void generate(cfg);
    } catch (error) {
      setSeedStatus(errorMessage(error), true);
    }
  });
  bakedButton.addEventListener('click', () => {
    if (!lastConfig || typeof onGenerate !== 'function') return;
    void generate({ ...lastConfig, terrainMode: 'baked' }, true);
  });
  root.querySelectorAll('[data-projection]').forEach((button) => {
    button.addEventListener('click', () => setProjection(button.dataset.projection));
  });
  $('#oasis-focus-sector').addEventListener('click', () => {
    if (map) map.flyTo({ center: UKRAINE_CENTER, zoom: 4.2, speed: 0.75, curve: 1.3 });
  });
  modal.addEventListener('click', (event) => {
    if (event.target === modal.querySelector('.oasis-modal-backdrop')) closeDialog();
  });
  dialog.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') { event.preventDefault(); closeDialog(); return; }
    if (event.key !== 'Tab') return;
    const focusable = [...dialog.querySelectorAll('button:not(:disabled), input:not(:disabled), select:not(:disabled), [tabindex="0"]')]
      .filter((element) => !element.closest('[hidden]'));
    if (!focusable.length) { event.preventDefault(); dialog.focus(); return; }
    const first = focusable[0], last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  });

  updateTime();
  const clockTimer = window.setInterval(updateTime, 1000);
  const countTimer = window.setInterval(refreshCounts, 60000);
  initMap();
  show();

  return {
    show,
    hide,
    destroy() {
      if (destroyed) return;
      destroyed = true;
      window.clearInterval(clockTimer);
      window.clearInterval(countTimer);
      window.clearTimeout(mapTimeout);
      try { map?.remove(); } catch { /* already disposed */ }
      root.remove();
    },
  };
}
