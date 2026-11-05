import { sample, timeLabel } from "./data.js";
export function createPresentation(state, globe, actions) {
  const data = state.data,
    duration = data.scenario.duration_s;
  const event = (pattern, fallback) =>
    data.events.find((e) => pattern.test(`${e.kind} ${e.label}`))?.t ??
    Math.min(fallback, duration);
  const object = (id) => data.objects.find((o) => o.id === id);
  const firstFix = (id) => {
    const oi = data.objects.findIndex((o) => o.id === id);
    return oi < 0
      ? null
      : data.fixes.t.find((t, i) => data.fixes.obj[i] === oi && t > 18000);
  };
  const rf = data.sensors.filter((s) => s.type === "rf_df"),
    gameRun = Boolean(data.game),
    hasRfData = Object.values(data.rf ?? {}).some((r) => r.t?.length),
    hasPositionFixes = data.fixes.t.length > 0,
    mediaSensor = { camera: "camera", iq: "rf_iq", satellite: "satellite", microphone: "microphone" },
    mediaKind = { camera: "image", iq: "iq", satellite: "image", microphone: "audio" },
    hasMedia = (type) =>
      data.media.some(
        (m) =>
          data.sensors.find((s) => s.id === m.sensor)?.type === mediaSensor[type] &&
          m.kind === mediaKind[type],
      );
  const defaultFeed = ["camera", "iq", "satellite", "microphone"].find(hasMedia) ?? state.feed;
  const satellite = data.media.find(
    (m) =>
      data.sensors.find((s) => s.id === m.sensor)?.type === "satellite" &&
      m.kind === "image",
  );
  const terrainLoss = data.audit?.checks.find(
    (c) => c.id === "terrain_shadow",
  )?.value;
  const fixError = (id, t) => {
    const oi = data.objects.findIndex((o) => o.id === id);
    const i =
      oi < 0
        ? -1
        : data.fixes.t.findLastIndex(
            (time, index) => time <= t && data.fixes.obj[index] === oi,
          );
    return i >= 0 && Number.isFinite(data.fixes.err[i])
      ? `${Math.round(data.fixes.err[i])} m`
      : "—";
  };
  const fiberIndex = data.objects.findIndex((o) => o.id === "fpv_fiber_1");
  const fiberRecords =
    fiberIndex < 0
      ? null
      : Object.values(data.rf).reduce(
          (total, r) => total + r.obj.filter((i) => i === fiberIndex).length,
          0,
        );
  const auditScore = (a) =>
    `${a.summary.pass}/${a.summary.pass + a.summary.fail + a.summary.skip}`;
  const beats = [
    {
      title: "One world. DEM terrain.",
      text: gameRun
        ? "DEM elevations anchor this browser simulation. Asset positions, routes and detections are generated, not observed operations."
        : "The same DEM supports the simulated truth tracks and sensor models. OASIS sensor observations are generated, not field measurements.",
      stat: [`${data.terrain.nx} × ${data.terrain.ny}`, "DEM GRID CELLS"],
      t: event(/occlusion/, 19180),
      mode: "god",
      wide: true,
    },
    {
      title: "The landscape decides what is visible.",
      text: gameRun
        ? "Browser detection intervals use a simplified range + terrain line-of-sight rule. They contain no RF bearing, SNR, received-power or uncertainty measurements."
        : Object.keys(data.shadow).length
          ? "Red cells require more than the selected 40 m AGL for modeled line of sight to the selected receiver. The shadow raster is DEM-derived, not a live coverage measurement."
          : "No terrain-shadow grid was supplied for this run; no coverage area is inferred.",
      stat: gameRun
        ? ["RANGE + LOS", "SIMULATED DETECTION RULE"]
        : Object.keys(data.shadow).length
          ? ["40 m AGL", `${Object.keys(data.shadow).length} SHADOW GRIDS`]
          : ["—", "SHADOW GRID / NOT SUPPLIED"],
      t: event(/occlusion/, 19180),
      mode: "delta",
      shadow: true,
      wide: true,
    },
    {
      title: "A different perspective from orbit.",
      text: hasMedia("satellite")
        ? "The chip uses a real Sentinel-2 background from a different acquisition day with modeled object stamps at the scenario pass time; it is not a contemporaneous satellite observation."
        : "No SAT1 image was supplied. The DEM or basemap is not a satellite capture of this scenario.",
      stat: satellite
        ? [timeLabel(data, satellite.t), "MODELED PASS STAMP / UTC"]
        : ["—", "SATELLITE MEDIA / NOT SUPPLIED"],
      t: event(/satellite|sentinel/i, 699),
      mode: "delta",
      feed: "satellite",
      object: "shahed_am",
    },
    {
      title: "An observation is not a position.",
      text: gameRun
        ? "The browser engine records simplified range + line-of-sight detection intervals. It generates no RF bearings or position fixes."
        : hasRfData && hasPositionFixes
          ? "Generated RF bearings with modeled error are crossed to form estimated fixes. The displayed error is computed against this run's simulated truth."
          : "No RF bearing or position-fix records were supplied; no estimate or error score is inferred.",
      stat: hasPositionFixes && !gameRun
        ? [fixError("mavic_1", Math.min(18427, duration)), "SYNTHETIC FIX ERROR VS TRUTH"]
        : ["—", gameRun ? "BEARING / FIX NOT GENERATED" : "POSITION FIX / NOT SUPPLIED"],
      t: Math.min(18427, duration),
      mode: "delta",
      object: "mavic_1",
      feed: "iq",
    },
    {
      title: "Behind the ridge.",
      text: gameRun
        ? "Browser detections use range + terrain line of sight only. No dBm/SNR readings or RF power audit are supplied."
        : hasRfData
          ? "Received power and LOS flags are generated by the RF model from the DEM, propagation, fading and noise; they are not hardware readings."
          : "No RF power or detection records were supplied for this run.",
      stat: [
        !gameRun && Number.isFinite(terrainLoss) ? `${terrainLoss.toFixed(1)} dB` : "—",
        !gameRun && Number.isFinite(terrainLoss)
          ? "AUDIT NLOS − LOS MEDIAN EXCESS"
          : "RF POWER AUDIT / NOT SUPPLIED",
      ],
      t: event(/occlusion.*RF2|RF2.*terrain/i, 19180) + 15,
      mode: "delta",
      object: "mavic_1",
      shadow: true,
      feed: "iq",
    },
    {
      title: "The controller has its own signal.",
      text:
        firstFix("pilot_1") != null
          ? "Generated bearing estimates on a modeled controller signal can be compared with the operator track in this run's answer key."
          : "No controller position fix was supplied. Ground truth alone does not establish a sensor detection.",
      stat: [
        fixError("pilot_1", firstFix("pilot_1") ?? 0),
        firstFix("pilot_1") != null
          ? "SYNTHETIC FIX ERROR VS TRUTH"
          : "CONTROLLER FIX / NOT SUPPLIED",
      ],
      t: firstFix("pilot_1") ?? Math.min(19400, duration),
      mode: "delta",
      object: "pilot_1",
    },
    {
      title: "The spectrum changes the picture.",
      text: object("jammer_1")
        ? gameRun
          ? "Jammer effects are simulated combat rules. This browser run supplies no IQ capture or RF bearing measurements."
          : hasMedia("iq")
            ? "IQ spectrograms are synthetic outputs from modeled emissions and noise, not SDR recordings. RF bearings are also model-generated."
            : "A jammer object is present, but no IQ media was supplied; no spectrum observation is available."
        : "This scenario does not include a jammer object. No jamming effect has been invented.",
      stat: object("jammer_1") && hasMedia("iq")
        ? [String(data.media.filter((m) => m.kind === "iq").length), "SYNTHETIC IQ SPECTROGRAMS"]
        : ["—", object("jammer_1") ? "IQ MEDIA / NOT SUPPLIED" : "JAMMER / NOT SUPPLIED"],
      t: event(/jammer/, 19900) + 50,
      mode: "delta",
      object: "jammer_1",
      feed: "iq",
    },
    {
      title: "Radio silence is not an empty sky.",
      text: hasMedia("microphone")
        ? "Audio is a synthetic acoustic rendering from the scenario's sound and propagation model, not a field microphone recording. The fiber platform has no modeled RF link."
        : "The fiber track is radio-silent in the model, but no microphone audio was exported. This run supplies no acoustic evidence.",
      stat: [
        gameRun || fiberRecords == null ? "—" : String(fiberRecords),
        gameRun ? "RF MEASUREMENTS / NOT SUPPLIED" : "SIMULATED RF ROWS / FIBER TRACK",
      ],
      t: event(/fiber/, 18900) + 30,
      mode: "delta",
      object: "fpv_fiber_1",
      feed: "microphone",
    },
    {
      title: "A receiver goes dark.",
      text: gameRun
        ? "Browser-game asset health comes from catalog HP and simulated damage rules; it is not live sensor health telemetry."
        : rf.some((s) => s.dead_t != null)
          ? "A configured scenario destruction event ends the receiver's modeled observation stream. This is not live sensor-health telemetry."
          : "No receiver failure time was supplied for this scenario.",
      stat: [
        gameRun ? "—" : rf.find((s) => s.dead_t != null)?.id ?? "—",
        gameRun
          ? "FIELD HEALTH / NOT SUPPLIED"
          : rf.some((s) => s.dead_t != null)
            ? "SIMULATED RECEIVER FAILURE"
            : "NO DESTRUCTION EVENT",
      ],
      t: event(/destroyed/, 20312) + 1,
      mode: "delta",
      wide: true,
    },
    {
      title: "Checks, not proof.",
      text: data.audit
        ? "The run audit checks generated records against this run's geometry, truth and model. It is not field validation. Expand each result for its evidence."
        : "No audit result was supplied; this run is not audited. No one-shot baseline score or measurement score is inferred.",
      stat: data.audit
        ? [
            auditScore(data.audit),
            data.audit.baseline
              ? `RUN CHECKS · BASELINE ${auditScore(data.audit.baseline)}`
              : "RUN CHECKS · NO BASELINE",
          ]
        : ["—", "NOT AUDITED"],
      t: Math.min(18427, duration),
      mode: "delta",
      audit: true,
      wide: true,
    },
  ];
  let startTime = 0,
    saved = null,
    narrate = false;
  const panel = document.querySelector("#presentation");
  const narration = document.createElement("button");
  narration.id = "present-narrate";
  narration.textContent = "VOICE OFF";
  narration.setAttribute("aria-label", "Toggle spoken narration");
  panel
    .querySelector(".presentation-top")
    .insertBefore(narration, document.querySelector("#present-exit"));
  function speak(beat) {
    if ("speechSynthesis" in window) {
      speechSynthesis.cancel();
      if (narrate) {
        const speech = new SpeechSynthesisUtterance(
          `${beat.title} ${beat.text}`,
        );
        speech.rate = 0.94;
        speech.onerror = (e) => {
          if (!["interrupted", "canceled"].includes(e.error))
            actions.notify(`Narration unavailable: ${e.error}`);
        };
        speechSynthesis.speak(speech);
      }
    }
  }
  narration.onclick = () => {
    if (!("speechSynthesis" in window)) {
      actions.notify(
        "Spoken narration is unavailable in this browser. Captions remain available.",
      );
      return;
    }
    narrate = !narrate;
    narration.textContent = narrate ? "VOICE ON" : "VOICE OFF";
    speak(beats[state.beat]);
  };
  function show(index) {
    state.beat = Math.max(0, Math.min(beats.length - 1, index));
    const beat = beats[state.beat];
    startTime = performance.now();
    state.shadow = !!beat.shadow;
    state.shadowHeight = 40;
    state.truth = true;
    state.rays = ![0, 1, 2, 7, 9].includes(state.beat);
    state.fixes = [3, 5, 6].includes(state.beat);
    state.follow = false;
    actions.setMode(beat.mode);
    actions.seek(Math.min(duration, beat.t));
    actions.setFeed(beat.feed ?? defaultFeed);
    actions.setTab(beat.audit ? "audit" : "feeds");
    if (beat.object && object(beat.object)) actions.select(beat.object);
    const p = beat.object ? sample(object(beat.object), state.t) : null;
    if (p && !beat.wide)
      globe.flyTo(
        p.lon,
        p.lat,
        p.alt,
        data.scenario.area.size_km * 650,
        -18 + state.beat * 5,
      );
    else
      globe.home(
        2.2,
        -22 + state.beat * 9,
        -46,
        data.scenario.area.size_km * 2150,
      );
    state.playing = state.beat !== 9;
    state.speed = 1;
    document.querySelector("#beat-number").innerHTML =
      `${String(state.beat + 1).padStart(2, "0")}<small>/ ${beats.length} CHAPTERS</small>`;
    document.querySelector("#beat-title").textContent = beat.title;
    document.querySelector("#beat-description").textContent = beat.text;
    const metric = document.createElement("span"),
      caption = document.createElement("small");
    metric.textContent = beat.stat[0];
    caption.textContent = beat.stat[1];
    document.querySelector("#beat-stat").replaceChildren(metric, caption);
    document.querySelector("#present-next").textContent =
      state.beat === 9 ? "FINISH BRIEFING →" : "NEXT MOMENT →";
    speak(beat);
    actions.changed();
  }
  function start() {
    if (state.presenting) return;
    saved = {
      t: state.t,
      mode: state.mode,
      shadow: state.shadow,
      shadowHeight: state.shadowHeight,
      truth: state.truth,
      rays: state.rays,
      fixes: state.fixes,
      playing: state.playing,
      speed: state.speed,
      selected: state.selected,
      feed: state.feed,
      tab: state.tab,
    };
    state.presenting = true;
    document.body.classList.add("presenting");
    panel.hidden = false;
    show(0);
  }
  function stop() {
    if (!state.presenting) return;
    state.presenting = false;
    document.body.classList.remove("presenting");
    panel.hidden = true;
    if ("speechSynthesis" in window) speechSynthesis.cancel();
    if (saved) {
      Object.assign(state, saved);
      actions.setMode(state.mode);
      actions.setFeed(state.feed);
      actions.setTab(state.tab);
      actions.seek(state.t);
    }
    globe.home();
    actions.changed();
    document.querySelector("#present-start").focus();
  }
  function next() {
    state.beat === 9 ? stop() : show(state.beat + 1);
  }
  document.querySelector("#present-exit").onclick = stop;
  document.querySelector("#present-next").onclick = next;
  document.querySelector("#present-previous").onclick = () =>
    show(state.beat - 1);
  return {
    start,
    stop,
    next,
    previous: () => show(state.beat - 1),
    tick(now) {
      if (!state.presenting) return;
      if (
        state.beat === 0 &&
        now - startTime > 2500 &&
        !matchMedia("(prefers-reduced-motion: reduce)").matches
      )
        globe.orbit(-22 + ((now - startTime - 2500) / 1000) * 0.35);
      document.querySelector("#beat-progress").style.width =
        `${Math.min(100, (now - startTime) / 200)}%`;
      if (now - startTime >= 20000 && state.beat < 9) show(state.beat + 1);
    },
    destroy() {
      document.body.classList.remove("presenting");
      if ("speechSynthesis" in window) speechSynthesis.cancel();
      narration.remove();
    },
  };
}
