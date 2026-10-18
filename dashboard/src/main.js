import "./styles.css";
import {
  validateData,
  parseDataFile,
  summarize,
  timeLabel,
  upperBound,
  sample,
  escapeHTML as esc,
} from "./data.js";
import { createState, MODES, SPEEDS } from "./state.js";
import { createGlobe, sunElevation } from "./globe.js";
import { createTruth, createSensors } from "./layers/truth.js";
import { createRF } from "./layers/rf.js";
import { createShadow } from "./layers/shadow.js";
import { createInspector } from "./panels/inspector.js";
import { createFeeds } from "./panels/feeds.js";
import { renderAudit } from "./panels/audit.js";
import { createTimeline } from "./timeline.js";
import { createPresentation } from "./present.js";
import { createCommands } from "./commands.js";
const $ = (s) => document.querySelector(s),
  C = window.Cesium;
let active = null,
  toastTimer;
function notify(message, ms = 5000) {
  $("#toast").textContent = message;
  $("#toast").hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    $("#toast").hidden = true;
  }, ms);
}
function start(data) {
  active?.destroy();
  const summary = summarize(data);
  console.info("MIRROR WORLD dataset", summary);
  const state = createState(data),
    listeners = new AbortController(),
    signal = listeners.signal;
  let globe;
  try {
    globe = createGlobe(data, notify);
  } catch (error) {
    throw new Error(
      `3D renderer could not start. Enable WebGL2 / hardware acceleration. ${error.message}`,
    );
  }
  let dirty = true,
    frameId,
    last = performance.now(),
    lastLayers = 0,
    lastUI = 0,
    disposed = false;
  const changed = () => {
    dirty = true;
    state.revision++;
    syncControls();
  };
  const seek = (t) => {
    state.t = Math.max(0, Math.min(data.scenario.duration_s, t));
    if (state.selectedFix != null && data.fixes.t[state.selectedFix] > state.t)
      state.selectedFix = null;
    globe.time(state.t);
    changed();
  };
  const truth = createTruth(globe, state),
    sensors = createSensors(globe, state),
    rf = createRF(globe, state),
    shadow = createShadow(globe, state, notify);
  const select = (id) => {
    state.selected = id;
    state.selectedFix = null;
    if (state.follow) follow(true);
    changed();
  };
  const inspector = createInspector(state, select),
    feeds = createFeeds(state, notify),
    timeline = createTimeline(state, seek);
  const togglePlay = () => {
    if (state.t >= data.scenario.duration_s) state.t = 0;
    state.playing = !state.playing;
    changed();
  };
  function setMode(mode) {
    state.mode = mode;
    if (mode === "operator") {
      state.follow = false;
      globe.viewer.trackedEntity = undefined;
    }
    const wipe = $("#scan-wipe");
    wipe.classList.remove("scanning");
    void wipe.offsetWidth;
    wipe.classList.add("scanning");
    $("#view-badge-text").textContent = {
      operator: "OPERATOR / SENSOR OBSERVATIONS",
      god: "GOD MODE / GROUND TRUTH",
      delta: "DELTA / OBSERVATION + TRUTH",
    }[mode];
    $("#mode-description").textContent = {
      operator: "What the sensors recorded. Nothing more.",
      god: "One true world, before it becomes a signal.",
      delta: "The distance between observation and truth.",
    }[mode];
    changed();
  }
  function setFeed(type) {
    state.feed = type;
    document
      .querySelectorAll("[data-feed]")
      .forEach((b) => b.classList.toggle("active", b.dataset.feed === type));
    changed();
  }
  function setTab(tab) {
    state.tab = tab;
    $("#feed-panel").hidden = tab !== "feeds";
    $("#audit-panel").hidden = tab !== "audit";
    document.querySelectorAll("[data-tab]").forEach((b) => {
      b.classList.toggle("active", b.dataset.tab === tab);
      b.setAttribute("aria-selected", String(b.dataset.tab === tab));
    });
    changed();
  }
  function follow(force = false) {
    if (state.mode === "operator") {
      notify("Switch to God or Delta mode to follow a truth object.");
      return;
    }
    const entity = truth.entities.get(state.selected);
    if (!entity || !entity.position.getValue(globe.viewer.clock.currentTime)) {
      notify("Selected object is inactive at this time.");
      return;
    }
    state.follow = force || !state.follow;
    globe.viewer.trackedEntity = state.follow ? entity : undefined;
    changed();
  }
  const actions = {
    seek,
    setMode,
    setFeed,
    setTab,
    select,
    changed,
    notify,
    togglePlay,
    follow,
    home: () => globe.home(),
    present: () => presentation.start(),
  };
  const presentation = createPresentation(state, globe, actions),
    commands = createCommands(state, actions);
  renderAudit(data);
  $("#scenario-name").textContent = data.scenario.name
    .toUpperCase()
    .replaceAll("-", " ");
  $("#scenario-region").textContent = "SYNTHETIC WORLD / REPLAY";
  $("#world-location").textContent =
    `${data.scenario.area.lat.toFixed(4)}° N  ${data.scenario.area.lon.toFixed(4)}° E`;
  $("#area-title").innerHTML =
    data.scenario.name === "ros-valley"
      ? "ROS RIVER VALLEY.<br><span>ONE WORLD. EVERY SIGNAL.</span>"
      : `${esc(data.scenario.name.toUpperCase().replaceAll("-", " "))}.<br><span>ONE WORLD. EVERY SIGNAL.</span>`;
  $("#area-size").textContent =
    `${data.scenario.area.size_km} × ${data.scenario.area.size_km} km`;
  $("#weather").textContent =
    `WIND ${data.scenario.weather.wind_from_deg.toFixed(0)}° ↦ ${data.scenario.weather.wind_mps.toFixed(1)} m/s · ${data.scenario.weather.temp_c.toFixed(0)}°C`;
  $("#date-label").textContent = new Date(data.scenario.start)
    .toLocaleDateString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      timeZone: "UTC",
    })
    .toUpperCase();
  $("#map-coordinates").textContent =
    `${data.scenario.area.lat.toFixed(4)}° N / ${data.scenario.area.lon.toFixed(4)}° E`;
  $("#data-count").textContent =
    `${summary.detections.toLocaleString()} RECORDS · SEED-REPLAY`;
  $("#system-state").textContent = "WORLD LOADED · PHYSICS REPLAY";
  const receiverRoot = $("#receiver-controls");
  receiverRoot.replaceChildren();
  for (const id of Object.keys(data.rf)) {
    const label = document.createElement("label"),
      input = document.createElement("input");
    input.type = "checkbox";
    input.checked = true;
    input.setAttribute("aria-label", `${id} bearing rays`);
    input.onchange = () => {
      input.checked ? state.receivers.add(id) : state.receivers.delete(id);
      changed();
    };
    label.append(input, document.createTextNode(id));
    receiverRoot.append(label);
  }
  $("#shadow-sensor").replaceChildren();
  for (const id of Object.keys(data.shadow)) {
    const option = document.createElement("option");
    option.value = id;
    option.textContent = id;
    $("#shadow-sensor").append(option);
  }
  $("#shadow-sensor").value = state.shadowSensor ?? "";
  const moments = data.events;
  $("#moments").replaceChildren();
  moments.forEach((event, i) => {
    const button = document.createElement("button");
    button.className = "moment";
    button.dataset.time = event.t;
    button.innerHTML = `<span class="moment-index">${String(i + 1).padStart(2, "0")}</span><span class="moment-content"><strong>${esc(event.label)}</strong><time>${timeLabel(data, event.t)} UTC</time></span>`;
    button.onclick = () => {
      seek(event.t);
      if (event.kind === "occlusion") {
        state.shadow = true;
        changed();
      }
    };
    $("#moments").append(button);
  });
  if (!moments.length)
    $("#moments").innerHTML =
      '<div class="no-observation">No key moments supplied.</div>';
  function syncControls() {
    document.querySelectorAll("[data-mode]").forEach((b) => {
      b.classList.toggle("active", b.dataset.mode === state.mode);
      b.setAttribute("aria-pressed", String(b.dataset.mode === state.mode));
    });
    for (const name of ["truth", "rays", "fixes", "shadow", "contours"]) {
      const input = $(`#layer-${name}`);
      input.checked = state[name];
      input.disabled =
        (state.mode === "operator" && ["truth", "shadow"].includes(name)) ||
        (state.mode === "god" && ["rays", "fixes"].includes(name)) ||
        (name === "shadow" && !Object.keys(data.shadow).length);
    }
    document.querySelector(".shadow-settings").hidden =
      !state.shadow || state.mode === "operator";
    $("#shadow-height").value = state.shadowHeight;
    $("#shadow-value").textContent = `${state.shadowHeight} m AGL`;
    $("#shadow-sensor").value = state.shadowSensor ?? "";
    $("#exaggeration-value").textContent =
      `RELIEF ×${state.exaggeration.toFixed(1)}`;
    $("#exaggeration").value = state.exaggeration;
    $("#terrain-note").textContent =
      state.exaggeration === 1
        ? "COPERNICUS GLO-30 · EXACT SIMULATION DEM"
        : `TERRAIN EXAGGERATED ${state.exaggeration.toFixed(1)}× · READOUTS AT TRUE SCALE`;
    $("#imagery-style").textContent = state.natural ? "NATURAL" : "NIGHT OPS";
    $("#basemap").textContent = state.osm ? "OSM" : data.terrain.texture ? "SENTINEL-2" : "ESRI";
    $("#world-mode").textContent = state.island ? "ISLAND ◇" : "GLOBE ◉";
    $("#play").textContent = state.playing ? "Ⅱ" : "▷";
    $("#play").setAttribute(
      "aria-label",
      state.playing ? "Pause scenario" : "Play scenario",
    );
    document.querySelectorAll("[data-speed]").forEach((b) => {
      b.classList.toggle("active", Number(b.dataset.speed) === state.speed);
      b.setAttribute(
        "aria-pressed",
        String(Number(b.dataset.speed) === state.speed),
      );
    });
  }
  for (const name of ["truth", "rays", "fixes", "shadow"])
    $(`#layer-${name}`).onchange = (e) => {
      state[name] = e.target.checked;
      changed();
    };
  $("#layer-contours").onchange = (e) => {
    state.contours = e.target.checked;
    globe.setContours(state.contours);
    changed();
  };
  $("#shadow-height").oninput = (e) => {
    state.shadowHeight = Number(e.target.value);
    changed();
  };
  $("#shadow-sensor").onchange = (e) => {
    state.shadowSensor = e.target.value;
    changed();
  };
  $("#exaggeration").oninput = (e) => {
    state.exaggeration = Number(e.target.value);
    globe.setRelief(state.exaggeration);
    changed();
  };
  $("#imagery-style").onclick = () => {
    state.natural = !state.natural;
    globe.styleImagery(state.natural);
    changed();
  };
  $("#basemap").onclick = () => {
    state.osm = !state.osm;
    globe.setImagery(state.osm, state.natural);
    shadow.invalidate();
    changed();
  };
  $("#world-mode").onclick = () => {
    state.island = !state.island;
    globe.setIsland(state.island);
    changed();
  };
  $("#home-view").onclick = () => {
    state.follow = false;
    globe.home();
  };
  $("#zoom-in").onclick = () => {
    globe.viewer.camera.zoomIn(
      globe.viewer.camera.positionCartographic.height * 0.25,
    );
    globe.scene.requestRender();
  };
  $("#zoom-out").onclick = () => {
    globe.viewer.camera.zoomOut(
      globe.viewer.camera.positionCartographic.height * 0.3,
    );
    globe.scene.requestRender();
  };
  $("#orbit-view").onclick = () => {
    state.follow = false;
    globe.home(1.4, C.Math.toDegrees(globe.viewer.camera.heading) + 45);
  };
  $("#tilt-view").onclick = () => globe.tilt();
  $("#play").onclick = togglePlay;
  $("#present-start").onclick = () => presentation.start();
  document
    .querySelectorAll("[data-mode]")
    .forEach((b) => (b.onclick = () => setMode(b.dataset.mode)));
  document.querySelectorAll("[data-speed]").forEach(
    (b) =>
      (b.onclick = () => {
        state.speed = Number(b.dataset.speed);
        changed();
      }),
  );
  document
    .querySelectorAll("[data-feed]")
    .forEach((b) => (b.onclick = () => setFeed(b.dataset.feed)));
  document
    .querySelectorAll("[data-tab]")
    .forEach((b) => (b.onclick = () => setTab(b.dataset.tab)));
  const handler = new C.ScreenSpaceEventHandler(globe.scene.canvas);
  handler.setInputAction((e) => {
    const picked = globe.scene.pick(e.position),
      id = picked?.id;
    if (
      typeof id?.id === "string" &&
      id.id.startsWith("truth:") &&
      state.mode !== "operator"
    )
      select(id.id.slice(6));
    else if (id?.type === "fix") {
      state.selectedFix = id.index;
      if (state.mode !== "operator" && data.fixes.obj[id.index] >= 0)
        state.selected = data.objects[data.fixes.obj[id.index]].id;
      changed();
    }
  }, C.ScreenSpaceEventType.LEFT_CLICK);
  document.addEventListener(
    "keydown",
    (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        commands.open();
        return;
      }
      if (
        document.querySelector("dialog[open]") ||
        ["INPUT", "SELECT", "TEXTAREA"].includes(e.target.tagName) ||
        e.metaKey ||
        e.ctrlKey ||
        e.altKey
      )
        return;
      const key = e.key.toLowerCase();
      if (key === " ") {
        e.preventDefault();
        togglePlay();
      } else if (key === "arrowright") {
        e.preventDefault();
        state.presenting ? presentation.next() : seek(state.t + 10);
      } else if (key === "arrowleft") {
        e.preventDefault();
        state.presenting ? presentation.previous() : seek(state.t - 10);
      } else if (key === "g")
        setMode(MODES[(MODES.indexOf(state.mode) + 1) % 3]);
      else if (key === "p")
        state.presenting ? presentation.stop() : presentation.start();
      else if (key === "escape" && state.presenting) presentation.stop();
      else if (key === "f") follow();
      else if (key === "[" || key === "]") {
        state.speed =
          SPEEDS[
            Math.max(
              0,
              Math.min(
                SPEEDS.length - 1,
                SPEEDS.indexOf(state.speed) + (key === "]" ? 1 : -1),
              ),
            )
          ];
        changed();
      } else if (/^[1-9]$/.test(key) && moments[Number(key) - 1])
        seek(moments[Number(key) - 1].t);
    },
    { signal },
  );
  document.addEventListener(
    "visibilitychange",
    () => {
      last = performance.now();
    },
    { signal },
  );
  function updateUI() {
    const stamp = timeLabel(data, state.t, true);
    $("#clock").innerHTML =
      `${stamp.slice(0, 8)}<span>${stamp.slice(8)}</span>`;
    $("#top-clock").innerHTML = $("#clock").innerHTML;
    const date = new Date(Date.parse(data.scenario.start) + state.t * 1000);
    $("#local-clock").textContent = date.toLocaleTimeString("en-GB", {
      timeZone: "Europe/Kyiv",
      hour: "2-digit",
      minute: "2-digit",
    });
    $("#sun").textContent =
      `SUN ${sunElevation(date, data.scenario.area.lat, data.scenario.area.lon).toFixed(1)}°`;
    $("#active-count").textContent =
      state.mode === "operator"
        ? `${Object.keys(data.rf).length} RF RECEIVERS`
        : `${data.objects.filter((o) => sample(o, state.t)).length} ACTIVE OBJECTS`;
    const currentMoment = moments.findLast((e) => e.t <= state.t);
    document.querySelectorAll(".moment").forEach((b, i) => {
      b.classList.toggle("active", Number(b.dataset.time) === currentMoment?.t);
      b.querySelector("strong").textContent =
        state.mode === "operator"
          ? `Scenario marker ${i + 1}`
          : moments[i].label;
    });
    inspector.update();
    feeds.update();
    timeline.update();
    if (state.mode === "god") {
      $("#event-ticker").innerHTML =
        '<div class="no-observation">Sensor observations hidden in God mode.</div>';
      $("#detection-rate").textContent = "TRUTH ONLY";
      return;
    }
    const detections = [];
    let rate = 0;
    for (const [id, r] of Object.entries(data.rf)) {
      const end = upperBound(r.t, state.t),
        start = upperBound(r.t, state.t - 10);
      rate += end - upperBound(r.t, state.t - 1);
      for (let i = end - 1; i >= Math.max(start, end - 6); i--)
        detections.push({ id, t: r.t[i], cls: r.cls[i], brg: r.brg[i] });
    }
    detections.sort((a, b) => b.t - a.t);
    $("#detection-rate").textContent = `${rate} DET / s`;
    $("#event-ticker").innerHTML = detections.length
      ? detections
          .slice(0, 6)
          .map(
            (d) =>
              `<div class="detection"><time>${timeLabel(data, d.t).slice(3)}</time><span class="sensor-tag">${esc(d.id)}</span><span class="signal-class">${esc(data.classes[d.cls])}</span><span class="bearing">${Math.round(d.brg)}°</span></div>`,
          )
          .join("")
      : '<div class="no-observation">No recent RF detections.</div>';
  }
  function frame(now) {
    if (disposed) return;
    const dt = Math.min((now - last) / 1000, 0.2);
    last = now;
    if (state.playing && !document.hidden) {
      state.t = Math.min(data.scenario.duration_s, state.t + dt * state.speed);
      if (state.t >= data.scenario.duration_s) {
        state.playing = false;
        changed();
      }
      globe.time(state.t);
    }
    presentation.tick(now);
    if (dirty || (state.playing && now - lastLayers > 50)) {
      truth.update();
      sensors.update();
      rf.update();
      shadow.update();
      globe.scene.requestRender();
      lastLayers = now;
    }
    if (dirty || (state.playing && now - lastUI > 120)) {
      updateUI();
      lastUI = now;
      dirty = false;
    }
    frameId = requestAnimationFrame(frame);
  }
  const removePostRender = globe.scene.postRender.addEventListener(() =>
    truth.updateReticle(),
  );
  globe.scene.renderError.addEventListener((scene, error) => {
    state.playing = false;
    $("#globe-error").hidden = false;
    $("#globe-error").textContent =
      `3D rendering stopped: ${error.message}. Reload after checking WebGL support.`;
    notify("The 3D renderer stopped. Playback has been paused.", 10000);
  });
  seek(state.t);
  setMode("delta");
  setTab("feeds");
  setFeed(feeds.has("camera") ? "camera" : feeds.has("iq") ? "iq" : "camera");
  $("#globe-error").hidden = true;
  $("#loading").hidden = true;
  updateUI();
  frameId = requestAnimationFrame(frame);
  active = {
    state,
    destroy() {
      disposed = true;
      cancelAnimationFrame(frameId);
      listeners.abort();
      removePostRender();
      presentation.destroy();
      feeds.destroy();
      timeline.destroy();
      shadow.destroy();
      handler.destroy();
      globe.destroy();
    },
  };
}
async function loadFile(file) {
  if (!file) return;
  if (file.size > 100_000_000) {
    notify("Scenario file exceeds the 100 MB limit.");
    return;
  }
  try {
    const data = parseDataFile(await file.text());
    start(data);
    notify(
      `Loaded ${data.scenario.name}. Media resolves relative to this page.`,
    );
  } catch (error) {
    notify(error.message, 10000);
  }
}
$("#import-button").onclick = () => $("#file-input").click();
$("#file-input").onchange = async (e) => {
  await loadFile(e.target.files[0]);
  e.target.value = "";
};
let dragDepth = 0;
window.addEventListener("dragenter", (e) => {
  if (e.dataTransfer?.types.includes("Files")) {
    e.preventDefault();
    dragDepth++;
    $("#drop-overlay").hidden = false;
  }
});
window.addEventListener("dragover", (e) => {
  e.preventDefault();
});
window.addEventListener("dragleave", () => {
  dragDepth = Math.max(0, dragDepth - 1);
  if (!dragDepth) $("#drop-overlay").hidden = true;
});
window.addEventListener("drop", async (e) => {
  e.preventDefault();
  dragDepth = 0;
  $("#drop-overlay").hidden = true;
  await loadFile(e.dataTransfer?.files[0]);
});
try {
  if (!C)
    throw new Error(
      "Cesium assets are missing. Run npm install and npm run build.",
    );
  start(validateData(window.MW));
} catch (error) {
  console.warn("MIRROR WORLD initialization:", error.message);
  $("#loading").hidden = true;
  $("#globe-error").hidden = false;
  $("#globe-error").textContent =
    `${error.message} Drop a valid data.js anywhere on this page, or use Load scenario.`;
  $("#system-state").textContent = "AWAITING VALID SCENARIO";
  notify(error.message, 12000);
}
