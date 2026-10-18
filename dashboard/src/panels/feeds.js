import { theme } from "../theme.js";
import { timeLabel } from "../data.js";
const $ = (s) => document.querySelector(s);
const names = {
  camera: "ELECTRO-OPTICAL",
  iq: "RF SPECTROGRAM",
  satellite: "SATELLITE CHIP",
  microphone: "ACOUSTIC MONITOR",
};
const mediaKinds = {
  camera: "image",
  iq: "iq",
  satellite: "image",
  microphone: "audio",
};
export function createFeeds(state, notify) {
  const data = state.data,
    byType = {};
  for (const type of Object.keys(names)) {
    const sensorType = type === "iq" ? "rf_iq" : type;
    byType[type] = data.media.filter(
      (m) =>
        data.sensors.find((s) => s.id === m.sensor)?.type === sensorType &&
        m.kind === mediaKinds[type] &&
        (type !== "satellite" || !/_zoom\.[^/]+$/.test(m.src)),
    );
    const tab = $(`[data-feed="${type}"]`);
    if (tab) tab.hidden = byType[type].length === 0;
  }
  const firstAvailable = Object.keys(names).find((type) => byType[type].length);
  if (!byType[state.feed]?.length && firstAvailable) state.feed = firstAvailable;
  document.querySelectorAll("[data-feed]").forEach((tab) => {
    const selected = tab.dataset.feed === state.feed;
    tab.classList.toggle("active", selected);
    tab.setAttribute("aria-selected", String(selected));
  });
  const selectedTab = $(`[data-feed="${state.feed}"]`);
  if (selectedTab)
    $("#feed-panel").setAttribute("aria-labelledby", selectedTab.id || "tab-feeds");
  let signature = "",
    current = null,
    audioContext,
    analyser,
    sourceNode,
    audioBuffer,
    audioMedia = null,
    audioEnabled = false,
    startedAt = 0,
    offset = 0,
    sourceRate = 1,
    mediaFailure = "",
    loadingToken = 0,
    disposed = false;
  let abortController = null,
    imageTimeout;
  const buffers = new Map();
  const image = $("#feed-image");
  function empty(message) {
    image.hidden = true;
    $("#satellite-inset").hidden = true;
    $("#feed-empty").hidden = false;
    $("#feed-empty-message").textContent = message;
    $("#feed-hud").hidden = true;
    $("#feed-zoom").hidden = true;
    $("#iq-cursor").hidden = true;
  }
  $("#satellite-zoom").onerror = () => {
    $("#satellite-inset").hidden = true;
    notify(
      "Satellite detail image unavailable; the full chip remains visible.",
    );
  };
  image.onerror = () => {
    clearTimeout(imageTimeout);
    if (
      !disposed &&
      current &&
      state.mode !== "god" &&
      state.feed !== "microphone"
    ) {
      empty("Referenced capture could not be loaded");
      mediaFailure = "MISSING MEDIA";
      $("#feed-state").textContent = mediaFailure;
      notify(`Cannot load media: ${current?.src ?? "unknown path"}`);
    }
  };
  image.onload = () => {
    clearTimeout(imageTimeout);
    if (
      !disposed &&
      current &&
      state.mode !== "god" &&
      state.feed !== "microphone"
    ) {
      mediaFailure = "";
      image.hidden = false;
      $("#iq-cursor").hidden = state.feed !== "iq";
      $("#feed-empty").hidden = true;
      $("#feed-zoom").hidden = false;
      $("#feed-hud").hidden = state.feed === "iq";
      const caption = $("#feed-hud .feed-hud-bottom");
      if (caption)
        caption.textContent = data.game
          ? "BROWSER SIMULATION MEDIA"
          : state.feed === "camera"
            ? "SYNTHETIC EO RENDER"
            : state.feed === "satellite"
              ? "SENTINEL BACKGROUND · MODELED OBJECTS"
              : "SYNTHETIC IQ SPECTROGRAM";
      const zoom =
        state.feed === "satellite"
          ? data.media.find(
              (m) =>
                m.sensor === current.sensor &&
                m.t === current.t &&
                /_zoom\.[^/]+$/.test(m.src),
            )
          : null;
      $("#satellite-inset").hidden = !zoom;
      if (zoom) $("#satellite-zoom").src = zoom.src;
    }
  };
  $("#feed-zoom").onclick = () => {
    $("#expanded-image").src = image.src;
    $("#image-dialog").showModal();
  };
  function stopAudio() {
    if (sourceNode) {
      sourceNode.onended = null;
      sourceNode.stop();
      sourceNode.disconnect();
      sourceNode = null;
    }
  }
  async function loadAudio(media) {
    const token = ++loadingToken;
    abortController?.abort();
    abortController = new AbortController();
    stopAudio();
    audioBuffer = null;
    audioMedia = media;
    if (!audioEnabled || !media) return;
    try {
      if (!audioContext) {
        audioContext = new AudioContext();
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        analyser.connect(audioContext.destination);
      }
      await audioContext.resume();
      let buffer = buffers.get(media.src);
      if (!buffer) {
        const response = await fetch(media.src, {
          signal: AbortSignal.any([
            abortController.signal,
            AbortSignal.timeout(15000),
          ]),
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const bytes = await response.arrayBuffer();
        if (bytes.byteLength > 100_000_000)
          throw new Error("Audio file exceeds 100 MB");
        buffer = await audioContext.decodeAudioData(bytes);
        if (buffers.size >= 3) buffers.delete(buffers.keys().next().value);
        buffers.set(media.src, buffer);
      }
      if (token !== loadingToken || disposed) return;
      audioBuffer = buffer;
      syncAudio();
    } catch (error) {
      if (token === loadingToken && !disposed && error.name !== "AbortError") {
        notify(`Audio unavailable: ${error.message}`);
        mediaFailure = "AUDIO UNAVAILABLE";
        $("#feed-state").textContent = mediaFailure;
      }
    }
  }
  function syncAudio() {
    if (
      !audioEnabled ||
      !audioBuffer ||
      !audioMedia ||
      state.feed !== "microphone" ||
      state.mode === "god" ||
      !state.playing
    ) {
      stopAudio();
      return;
    }
    const target = state.t - audioMedia.t;
    if (target < 0 || target >= audioBuffer.duration) {
      stopAudio();
      return;
    }
    const elapsed = sourceNode
      ? offset + (audioContext.currentTime - startedAt) * sourceRate
      : Infinity;
    if (
      sourceRate !== state.speed ||
      Math.abs(elapsed - target) > Math.max(0.35, state.speed * 0.15)
    ) {
      stopAudio();
      sourceNode = audioContext.createBufferSource();
      sourceNode.buffer = audioBuffer;
      sourceRate = state.speed;
      sourceNode.playbackRate.value = sourceRate;
      sourceNode.connect(analyser);
      offset = target;
      startedAt = audioContext.currentTime;
      sourceNode.start(0, target);
      sourceNode.onended = () => {
        sourceNode = null;
      };
    }
  }
  $("#audio-play").onclick = async () => {
    const audioLabel =
      data.game || data.provenance?.dem_sources?.length
        ? "SYNTHETIC AUDIO"
        : "AUDIO";
    audioEnabled = !audioEnabled;
    $("#audio-play").textContent = audioEnabled
      ? `Ⅱ STOP ${audioLabel}`
      : `▷ PLAY ${audioLabel}`;
    if (audioEnabled) await loadAudio(current);
    else stopAudio();
  };
  function update() {
    const options = byType[state.feed] ?? [];
    current =
      state.mode === "god"
        ? null
        : (options.findLast((m) => m.t <= state.t) ?? null);
    const key = `${state.feed}/${state.mode}/${current?.src ?? ""}`;
    if (key !== signature) {
      signature = key;
      ++loadingToken;
      abortController?.abort();
      mediaFailure = "";
      clearTimeout(imageTimeout);
      $("#satellite-inset").hidden = true;
      $("#feed-name").textContent = names[state.feed];
      $("#feed-state").textContent = current
        ? "MEDIA AVAILABLE"
        : state.mode === "god"
          ? "HIDDEN"
          : options.length
            ? "NO CAPTURE AT PLAYHEAD"
            : "UNAVAILABLE";
      $("#feed-state").className = current ? "cyan" : "muted";
      $("#audio-canvas").hidden = state.feed !== "microphone" || !current;
      $("#audio-play").hidden = state.feed !== "microphone" || !current;
      $("#iq-cursor").hidden = state.feed !== "iq" || !current;
      $("#feed-source").textContent = current
        ? `${current.sensor} / ${current.kind.toUpperCase()}`
        : "SOURCE UNAVAILABLE";
      if (!current) {
        empty(
          state.mode === "god"
            ? "Sensor feeds hidden in God mode"
            : options.length
              ? "No supplied media at or before this time"
              : `No ${names[state.feed].toLowerCase()} media supplied in this dataset`,
        );
        stopAudio();
      } else if (state.feed === "microphone") {
        image.hidden = true;
        $("#feed-hud").hidden = true;
        $("#feed-zoom").hidden = true;
        $("#feed-empty").hidden = true;
        loadAudio(current);
      } else {
        stopAudio();
        image.hidden = true;
        $("#feed-empty").hidden = false;
        $("#feed-empty-message").textContent = "Loading supplied media";
        image.loading = "eager";
        image.alt = `${names[state.feed]} media from ${current.sensor} at ${timeLabel(data, current.t)} UTC`;
        image.src = current.src;
        imageTimeout = setTimeout(() => {
          empty("Capture request timed out");
          mediaFailure = "MEDIA TIMEOUT";
          $("#feed-state").textContent = mediaFailure;
          notify(
            "Media request exceeded 15 seconds. Try selecting the feed again.",
          );
        }, 15000);
        $("#feed-timestamp").textContent =
          `${current.sensor} ${timeLabel(data, current.t)}Z`;
      }
    }
    if (current) {
      const age = state.t - current.t;
      $("#feed-age").textContent =
        age < 1
          ? "AT PLAYHEAD"
          : `AGE ${age < 60 ? `${Math.floor(age)} s` : `${Math.floor(age / 60)} min`}`;
      $("#feed-state").textContent =
        mediaFailure ||
        (state.feed === "microphone" && audioEnabled
          ? !audioBuffer
            ? "LOADING AUDIO"
            : state.t - current.t >= audioBuffer.duration
              ? "RECORDING ENDED"
              : state.playing
                ? `PLAYING / ${state.speed}×`
                : "PAUSED"
          : age < 2
            ? "MEDIA AT PLAYHEAD"
            : "MEDIA / HELD");
      if (
        state.feed === "iq" &&
        !matchMedia("(prefers-reduced-motion: reduce)").matches
      )
        $("#iq-cursor").style.left = `${((state.t % 8) / 8) * 100}%`;
      if (state.feed === "microphone") {
        syncAudio();
        drawAudio();
      }
    } else $("#feed-age").textContent = "—";
  }
  function drawAudio() {
    const canvas = $("#audio-canvas"),
      w = canvas.clientWidth,
      h = canvas.clientHeight;
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, w, h);
    if (!analyser || !sourceNode) {
      ctx.strokeStyle = theme("text-3");
      ctx.beginPath();
      ctx.moveTo(12, h / 2);
      ctx.lineTo(w - 12, h / 2);
      ctx.stroke();
      return;
    }
    const values = new Uint8Array(analyser.frequencyBinCount);
    analyser.getByteFrequencyData(values);
    const bw = (w - 24) / values.length;
    ctx.fillStyle = theme("signal");
    values.forEach((value, i) => {
      const bh = (value / 255) * (h - 45);
      ctx.fillRect(12 + i * bw, h - 30 - bh, Math.max(1, bw - 1), bh);
    });
  }
  return {
    update,
    has: (type) => byType[type]?.length > 0,
    destroy() {
      disposed = true;
      clearTimeout(imageTimeout);
      ++loadingToken;
      abortController?.abort();
      stopAudio();
      audioContext
        ?.close()
        .catch((e) => notify(`Audio shutdown failed: ${e.message}`));
      $("#satellite-zoom").onerror = null;
      image.onload = null;
      image.onerror = null;
    },
  };
}
