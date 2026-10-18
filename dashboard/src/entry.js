import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import './entry.css';
import './map-worker.js';
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
    <header class="oasis-topbar">
      <div class="oasis-brand">
        <svg viewBox="0 0 650 500" class="oasis-mark w-8 h-8 md:w-10 md:h-10 shrink-0 transition-colors duration-500 text-[#D4AF37] drop-shadow-[0_0_8px_rgba(255,215,0,0.5)]" fill="currentColor">
            <path d="m620.39,364.82c-0.53628-7.2677-1.7767-14.482-5.0286-21.276-9.4786-19.803-33.963-29.34-53.026-19.284-15.333,8.0885-22.563,29.331-13.578,45.149,6.873,12.099,23.072,18.235,35.622,10.228,4.4328-2.828,7.6343-7.2793,8.9938-12.286,1.3595-5.0063,0.68452-10.798-2.9392-15.401-2.2364-2.8407-5.4473-4.7654-9.1114-5.408-3.664-0.64263-8.1708,0.40388-10.875,3.9972-1.7829,2.3692-1.91,4.5449-1.4108,7.1127,0.24961,1.2839,0.78116,2.8399,2.3513,3.9972,1.5702,1.1573,4.2926,1.9424,5.5844,0.58783,1.1069-1.1607-0.67477-3.153-0.73029-4.7559-0.0388-0.83158-0.0772-1.7317,0.26004-2.4745,0.89679-1.1463,1.8493-1.342,3.4682-1.0581,1.6548,0.29023,3.6474,1.4542,4.5851,2.6452v0.0588c2.0224,2.5986,2.3717,5.5943,1.5284,8.6999-0.81645,3.0066-2.8568,5.919-5.4668,7.7006l-0.29391,0.23513c-8.5452,5.4516-18.484,0.70317-23.392-7.9366-6.7162-11.823-1.5113-26.282,10.285-32.505,15.078-7.9537,35.744,1.451,40.36,17.085,4.566,15.464,2.8715,30.938,0.27385,37.511l10.609,0.073c2.5579-12.089,1.9287-15.035,1.9287-22.696z" />
            <path d="m158.66,157a70.231,70.231,0,0,0,-14.44,42.81,70.235,70.235,0,1,0,140.47,0,70.231,70.231,0,0,0,-14.28,-42.81h-111.75z" />
            <path d="m140.86,465.53c-6.7333,0-8.7137-5.4462-12.181-25.899-2.4479-14.774-7.1068-28.463-10.502-43.043-3.0219-13.117-5.6425-20.332-9.6694-26.618-6.5526-10.229-6.3011-20.921,0.71691-30.481,6.33-8.6232,6.827-11.121,6.5471-32.901-0.13783-10.725-0.56403-21.286-0.94711-23.468-0.88077-5.0179-4.6148-7.6923-13.904-9.9586-8.4827-2.0695-16.525-2.2933-41.967-1.1681-18.144,0.80245-20.457,0.72323-22.75-0.77901-5.627-3.687-2.9527-8.8405,12.261-23.626,15.69-15.249,23.876-24.688,38.811-44.75,26.839-36.053,30.927-40.83,57.501-49.189,19.575-6.1582,26.691-9.0119,62.031-10.06,24.654-0.7309,38.767,2.5963,45.357,3.3466,25.219,2.8716,66.247,14.877,91.933,26.083,13.581,5.9249,14.042,6.1723,30.115,16.152,11.981,7.4391,18.733,10.459,35.44,15.034,34.886,9.553,56.753,7.7583,92,10.378,9.2579,0.68808,49.298,3.5149,74.5,4.4784,30.689,1.1732,35.835-2.0376,38.423,0.54994,2.0315,2.0315,0.5636,8.1815,0.6024,14.306,0.0237,3.7378-0.18399,7.6642-0.48569,11.602-8.1923-1.424-8.0353-1.3676-26.54-2.9165-1.6808-0.14069-16.718-1.6695-44.5-4.1726-11.867-1.0692-70.326-2.8448-105.5-3.9248-16.997-0.52189-34.357-4.7228-51-1.2347-5.7624,1.2076,2.387-1.1161-16,7.4812-36.313,14.051-55.853,23.79-104.5,32.83-30.774,4.5201-33.208,4.9745-36.376,7.2909-1.7456,1.2764-1.662,1.6171,1.6767,6.8363,3.5642,5.5717,14.275,15.81,29.699,28.389,51.619,43.564,115.05,77.431,162.89,98.598,22.221,9.5122,37.55,14.655,50.108,16.811,61.892,13.654,134.26-9.4938,136.11-56.959,0.0489-1.256,0.49928-6.001-0.1398-12.079-0.44539-4.2357-0.89625-7.3216-2.2932-11.095-3.9795-10.75-12.413-20.407-28.672-21.755-11.746,0.022-20.375,6.1561-23.95,16.17-4.5622,12.78,1.3185,27.071,14.023,29.565,6.6403,1.3038,11.222-0.5256,14.271-4.4679,3.3424-4.3221,3.72-12.026,1.3559-15.634-2.2757-3.4732-7.2459-5.2754-10.824-3.9248-3.6125,1.3636-4.9933,0.36555-0.6538-3.1839,0.38036-0.24867,0.77844-0.4586,1.191-0.63136,6.6675-2.7918,17.127,4.1226,17.913,14.135,0.7119,11.495-7.7045,20.279-19.249,20.94-6.5659,0.37574-14.594-1.9665-20.026-7.8035-13.425-14.428-9.1712-34.885,2.9586-45.762,4.6131-4.1366,7.7535-6.0583,14.065-7.4773,19.37-4.3554,37.69,4.5134,45.528,24.301,3.5645,8.9992,3.7675,16.201,3.8515,23.221,0.70438,58.895-65.742,87.202-131.95,82.517-28.009-2.4123-46.229-6.8095-80.495-20.915-36.58-12.09-143.44-68.32-207.96-120.33-18.846-15.317-30.511-22.813-33.055-21.24-0.61585,0.38062-0.98989,11.992-0.99221,30.802-0.004,28.758-0.1019,30.352-2.0717,33.583-3.2793,5.3791-4.935,17.725-5.9822,44.608-1.6327,41.914-2.675,60.915-3.4439,62.778-1.3963,3.383-7.0306,4.6642-13.289,4.6642zm221.62-252.27c0.41803-2.1707-4.6044-8.6243-11.231-13.08-10.396-6.9893-22.385-11.512-34.092-15.96-71.934-23.518-145.08-20.065-174.03-4.962-10.593,5.1512-14.126,7.777-22.813,15.582-4.1291,3.7102-9.5939,9.7305-12.144,13.379-5.133,7.3428-10.014,13.339-19.014,23.362-9.3026,10.359-14.5,16.774-14.5,17.897,0,1.5721,7.8962,3.1488,17.5,3.5809,81.15,10.292,230.44,14.198,270.32-39.799zm224.18-69.351c-16.558-0.50003-42.467-2.0158-63.5-4.8954-19.525-2.6732-39.047-6.067-58-11.467-17.982-5.123-35.124-12.85-52.5-19.754-7.7243-3.0694-15.32-6.4533-23-9.6318-8.319-3.4429-16.53-7.1723-25-10.224-15.523-5.5928-30.986-11.946-47.239-14.789-41.988-7.3464-85.261-8.7793-127.76-5.4986-23.554,1.8182-46.695,7.7124-69.5,13.878-17.863,4.8293-35.019,11.972-52.5,18.041-5.069,1.761-10.039,6.841-15.177,5.321-5.396-1.6-10.73-7.749-10.317-13.361,0.434-5.884,7.835-9.014,12.753-12.272,16.823-11.146,36.498-17.485,55.661-23.803,19.219-6.3349,38.923-12.127,59.072-14.001,54.326-5.0532,110.09-3.4301,163.5,7.7269,28.29,5.9098,53.945,20.759,81,30.92,31.437,11.806,61.76,27.444,94.5,34.909,33.045,7.534,83.745,9.6292,101.22,9.5911,6.5425-0.0143,6.7685,0.0708,8.3595,3.1475,1.8515,3.5805,3.1256,14.296,1.7926,15.077-1.3395,0.78418-21.593,1.4453-33.376,1.0894z" />
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

    <div class="oasis-sector-entry">
      <span class="oasis-sector-name">UKRAINE</span>
      <button class="oasis-button oasis-button-primary" id="enter-simulation" type="button">ENTER SIMULATION ↗</button>
      <button class="oasis-button oasis-button-secondary" id="replay-hero" type="button">REPLAY HERO</button>
      <p class="oasis-action-status" id="oasis-action-status" role="status" aria-live="polite" hidden></p>
    </div>

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
        center: [31.2, 25],
        zoom: 2.0,
        minZoom: 1.4,
        projection: { type: 'globe' },
        maxZoom: 17,
        maxPitch: 65,
        dragRotate: true,
        attributionControl: { compact: true, customAttribution: '© OpenStreetMap contributors · © CARTO' },
      });
      map.addControl(new maplibregl.NavigationControl({ showCompass: true }), 'top-right');
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
