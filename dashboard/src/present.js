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
    hasMedia = (type) =>
      data.media.some(
        (m) => data.sensors.find((s) => s.id === m.sensor)?.type === type,
      );
  const beats = [
    {
      title: "One world. Real terrain.",
      text: "The world comes first. Every sensor observes the same landscape, weather and moving objects.",
      stat: `${data.terrain.nx} × ${data.terrain.ny} DEM SAMPLES`,
      t: event(/occlusion/, 19180),
      mode: "god",
      wide: true,
    },
    {
      title: "The landscape decides what is visible.",
      text: "The red terrain is hidden from the selected receiver at 40 metres above ground. Visibility is computed from this exact elevation model.",
      stat: `${rf.length} DIRECTION FINDERS · 40 m AGL`,
      t: event(/occlusion/, 19180),
      mode: "delta",
      shadow: true,
      wide: true,
    },
    {
      title: "A different perspective from orbit.",
      text: hasMedia("satellite")
        ? "The recorded satellite chip shares the scenario clock. Compare the sensor image with the actual flight path."
        : "No satellite capture was supplied in this dataset. The morning truth track is available; the satellite feed remains NO SIGNAL.",
      stat: hasMedia("satellite")
        ? "TIME-SYNCHRONIZED SATELLITE CAPTURE"
        : "SATELLITE FEED / NOT SUPPLIED",
      t: event(/satellite|sentinel/i, 699),
      mode: "delta",
      feed: "satellite",
      object: "shahed_am",
    },
    {
      title: "An observation is not a position.",
      text: "Measured bearings cross to produce a fix. Delta mode connects that estimate to the object that actually produced the signal.",
      stat: "WHITE = TRUTH · AMBER = OBSERVATION",
      t: Math.min(18427, duration),
      mode: "delta",
      object: "mavic_1",
      feed: "iq",
    },
    {
      title: "Behind the ridge.",
      text: "The receiver’s terrain shadow intersects the flight path. Power and detection records show what the receiver could actually observe.",
      stat: "LINE OF SIGHT IS A PHYSICS RESULT",
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
          ? "Crossed bearings on a controller signal can be compared with the operator’s position in the answer key."
          : "No controller position fix was supplied. Ground truth alone cannot establish a sensor detection.",
      stat:
        firstFix("pilot_1") != null
          ? "CONTROLLER UPLINK / CROSS-BEARING FIX"
          : "CONTROLLER FIX / NOT SUPPLIED",
      t: firstFix("pilot_1") ?? Math.min(19400, duration),
      mode: "delta",
      object: "pilot_1",
    },
    {
      title: "The spectrum changes the picture.",
      text: object("jammer_1")
        ? "Replay the jammer interval and compare the recorded spectrum with the bearings that remain. Missing observations are part of the dataset."
        : "This scenario does not include a jammer object. No jamming effect has been invented.",
      stat: object("jammer_1")
        ? "RECORDED IQ · SHARED SCENARIO CLOCK"
        : "JAMMER / NOT SUPPLIED",
      t: event(/jammer/, 19900) + 50,
      mode: "delta",
      object: "jammer_1",
      feed: "iq",
    },
    {
      title: "Radio silence is not an empty sky.",
      text: hasMedia("microphone")
        ? "A fiber-optic platform can produce no radio observations while still producing an acoustic record. Compare both sensor channels."
        : "The fiber-optic truth track is visible. No microphone recording was supplied, so the acoustic channel remains NO SIGNAL.",
      stat: hasMedia("microphone")
        ? "ONE OBJECT · DIFFERENT SENSOR PICTURES"
        : "ACOUSTIC FEED / NOT SUPPLIED",
      t: event(/fiber/, 18900) + 30,
      mode: "delta",
      object: "fpv_fiber_1",
      feed: "microphone",
    },
    {
      title: "A receiver goes dark.",
      text: rf.some((s) => s.dead_t != null)
        ? "At the recorded destruction time the receiver stops observing. Its mast turns grey and its detection strip ends."
        : "No receiver destruction time was supplied for this scenario.",
      stat: rf.find((s) => s.dead_t != null)
        ? `${rf.find((s) => s.dead_t != null).id} / OFFLINE`
        : "NO DESTRUCTION EVENT",
      t: event(/destroyed/, 20312) + 1,
      mode: "delta",
      wide: true,
    },
    {
      title: "Proof, not plausibility.",
      text: data.audit
        ? "Independent checks test the observations against geometry, timing and provenance. Expand each result to inspect its evidence."
        : "The observations are ready to inspect. No audit or one-shot baseline was supplied; the scorecard reports that absence explicitly.",
      stat: data.audit
        ? `${data.audit.summary.pass} PASS · ${data.audit.summary.fail} FAIL · ${data.audit.summary.skip} SKIP`
        : "AUDIT / NOT SUPPLIED",
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
    state.rays = true;
    state.fixes = true;
    state.follow = false;
    actions.setMode(beat.mode);
    actions.seek(Math.min(duration, beat.t));
    actions.setFeed(beat.feed ?? (hasMedia("camera") ? "camera" : "iq"));
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
        data.scenario.area.size_km * 2050,
      );
    state.playing = state.beat !== 9;
    state.speed = 1;
    document.querySelector("#beat-number").textContent =
      `${String(state.beat + 1).padStart(2, "0")} / ${beats.length}`;
    document.querySelector("#beat-title").textContent = beat.title;
    document.querySelector("#beat-description").textContent = beat.text;
    document.querySelector("#beat-stat").textContent = beat.stat;
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
    panel.hidden = false;
    show(0);
  }
  function stop() {
    if (!state.presenting) return;
    state.presenting = false;
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
      if ("speechSynthesis" in window) speechSynthesis.cancel();
      narration.remove();
    },
  };
}
