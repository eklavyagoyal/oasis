import "./flow.css";
import { createEntry } from "./entry.js";
import { generateWorld } from "./game/generate.js";
import { createRecordedLayer } from "./game/layer.js";
import { counts, exportAll } from "./game/store.js";
import { validateData, escapeHTML as esc } from "./data.js";

// Navigation only: the console's existing start(), timeline, panels and map stay the simulation UI.
export function createFlow({ start, getActive, notify, heroData }) {
  let world = null, busy = false, endShown = false, entry;
  const app = document.querySelector("#app");
  const controls = document.createElement("nav");
  controls.className = "oasis-flow-controls";
  controls.setAttribute("aria-label", "World and run actions");
  controls.innerHTML = `<button id="new-world">NEW WORLD</button><button id="same-world" hidden>RUN AGAIN</button><button id="run-summary" hidden>SUMMARY</button><button id="export-runs">EXPORT DATA</button><button id="data-notes">DATA NOTES</button>`;
  document.querySelector(".top-actions").prepend(controls);
  const result = document.createElement("dialog");
  result.className = "oasis-run-result";
  result.setAttribute("aria-labelledby", "run-result-title");
  result.innerHTML = `<form method="dialog"><button aria-label="Close summary">CLOSE ×</button></form><span class="eyebrow">RECORDED BROWSER SIMULATION</span><h2 id="run-result-title">Run summary</h2><p id="run-result-context"></p><dl id="run-result-numbers"></dl><p>Tracks and detections are synthetic. HP and combat outcomes are a simplified model, not operational predictions.</p><div class="oasis-result-actions"><button id="result-rerun">RUN AGAIN · SAME WORLD</button><button id="result-new">NEW WORLD</button><button id="result-export">EXPORT DATA</button><button id="result-globe">BACK TO GLOBE</button></div>`;
  const notes = document.createElement("dialog");
  notes.className = "oasis-run-result";
  notes.setAttribute("aria-labelledby", "data-notes-title");
  notes.innerHTML = `<form method="dialog"><button aria-label="Close data notes">CLOSE ×</button></form><h2 id="data-notes-title">What these readings mean</h2><div id="data-notes-context"></div><dl><dt>Bearing / heading</dt><dd>Degrees clockwise from true north. A bearing is the direction from a receiver to a transmitter. It is not a measured GPS position.</dd><dt>Sun elevation</dt><dd>Calculated angle above the horizon for the scenario time and location. Not a live sensor reading.</dd><dt>SNR / power</dt><dd>Model-generated signal-to-noise ratio (dB) and received power (dBm), available only in the Python replay. The browser engine does not generate these measurements.</dd><dt>Terrain relief</dt><dd>The display's vertical exaggeration. It does not change exported physical altitudes.</dd><dt>Position error / uncertainty</dt><dd>Python replay comparisons against synthetic ground truth, not verified field accuracy.</dd></dl>`;
  document.body.append(result, notes);
  const button = (id) => controls.querySelector(`#${id}`);
  function updateButtons() {
    button("same-world").hidden = !world || !getActive()?.state.data.game;
    button("run-summary").hidden = !getActive()?.state.data.game;
    for (const b of controls.querySelectorAll("button")) b.disabled = busy;
  }
  async function download() {
    try {
      const blob = await exportAll();
      const url = URL.createObjectURL(blob), a = document.createElement("a");
      a.href = url; a.download = "oasis-export.json"; a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) { notify(`Export failed: ${error.message}`, 10000); }
  }
  function showEntry() {
    if (busy) return;
    getActive()?.pause();
    result.close(); notes.close();
    document.body.classList.remove("cinema");
    document.querySelector("#cinema-exit").hidden = true;
    app.inert = true;
    entry.show();
  }
  async function generate(cfg, progress = () => {}, existingWorld = null) {
    if (busy) throw new Error("A world is already being generated.");
    busy = true; updateButtons();
    try {
      const generated = await generateWorld(cfg, { world: existingWorld, onProgress: progress, bakedData: heroData });
      const dataset = validateData(generated.dataset);
      const next = start(dataset, { skipOpening: true, onFrame: tick, createOverlay: (globe, data) => createRecordedLayer(globe, data, { showFixedIcons: true }) });
      world = generated.world; endShown = false;
      app.inert = false;
      next.state.t = 0;
      next.state.speed = 300;
      next.resume();
      entry.hide();
      const warnings = generated.warnings || generated.run?.meta?.warnings || [];
      if (warnings.length) notify(warnings.join(" · "), 12000);
      else notify("World loaded. Synthetic simulation replay; data saved locally.");
      return generated;
    } finally { busy = false; updateButtons(); }
  }
  async function rerun() {
    if (!world || busy) return;
    result.close();
    const cfg = { ...getActive().state.data.game.cfg };
    cfg.scenarioSeed = ((cfg.scenarioSeed || 0) + 1) >>> 0;
    try { await generate(cfg, (message) => notify(message), world); }
    catch (error) { notify(`Rerun failed: ${error.message}`, 12000); }
  }
  function summary() {
    const data = getActive()?.state.data;
    if (!data?.game) return;
    const r = data.game.record, s = r.summary, h = s.hostile || {}, d = s.defence || {};
    const length = (value) => Array.isArray(value) ? value.length : value ?? 0;
    result.querySelector("#run-result-title").textContent = getActive().state.t >= data.scenario.duration_s ? "Run complete" : "Recorded run totals";
    result.querySelector("#run-result-context").textContent = `World ${r.worldId || world?.id || ""} · Scenario seed ${data.game.cfg.scenarioSeed} · ${s.duration_s} seconds`;
    const values = [["Launched", h.launched], ["Intercepted", length(h.killed)], ["Jammed", length(h.jammed)], ["Impacts", length(h.impacts)], ["Never detected", length(h.never_detected)], ["Defence attempts", d.shots], ["Truth track rows", r.tracks.length], ["Detection intervals", r.detections.length], ["Collision events", r.collisions.length], ["HP changes", r.damage.length]];
    result.querySelector("#run-result-numbers").innerHTML = values.map(([label,value]) => `<div><dt>${esc(label)}</dt><dd>${esc(String(value ?? 0))}</dd></div>`).join("");
    if (!result.open) result.showModal();
  }
  function tick(state) {
    if (!state.data.game) return;
    if (state.t < state.data.scenario.duration_s) endShown = false;
    else if (!endShown) { endShown = true; summary(); }
  }
  function replay() {
    if (!heroData) throw new Error("No baked Python replay is available. Generate a new world instead.");
    start(heroData, { skipOpening: true });
    app.inert = false; updateButtons();
  }
  entry = createEntry({ onGenerate: generate, onReplay: replay, onExport: download, getCounts: counts });
  button("new-world").onclick = showEntry;
  button("same-world").onclick = rerun;
  button("run-summary").onclick = summary;
  button("export-runs").onclick = download;
  button("data-notes").onclick = () => {
    const data = getActive()?.state.data;
    notes.querySelector("#data-notes-context").textContent = data?.game
      ? "This run uses real elevation terrain and synthetic assets, trajectories, range/line-of-sight detections and HP. Coverage rings are configured ranges, not measured radar coverage. Weather is not simulated. No RF angles, SNR, camera frames or physics audit were generated for this browser run."
      : "This replay contains model-generated sensor recordings over real terrain. Aircraft, events and weather are scenario inputs, not live observations. An empty feed means the loaded bundle supplies no recording, not proof that no aircraft was present.";
    notes.showModal();
  };
  result.querySelector("#result-rerun").onclick = rerun;
  result.querySelector("#result-new").onclick = showEntry;
  result.querySelector("#result-export").onclick = download;
  result.querySelector("#result-globe").onclick = showEntry;
  document.querySelector(".brand").onclick = (e) => { e.preventDefault(); showEntry(); };
  updateButtons();
  showEntry();
  return { tick, show: showEntry, loaded() { updateButtons(); }, destroy() { entry.destroy(); controls.remove(); result.remove(); notes.remove(); app.inert = false; } };
}
