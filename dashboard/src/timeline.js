import { theme } from "./theme.js";
import { upperBound, timeLabel } from "./data.js";
const $ = (s) => document.querySelector(s);
export function createTimeline(state, seek) {
  const canvas = $("#timeline-canvas"),
    track = $("#timeline-chart"),
    scrubber = $("#time-scrubber"),
    data = state.data,
    duration = data.scenario.duration_s;
  let focus = !data.game && duration > 18000,
    min = focus ? 18000 : 0,
    max = duration;
  let boundsKey = "",
    lastWidth = 0,
    lastScope = "";
  const receivers = Object.keys(data.rf);
  $("#density-labels").replaceChildren();
  for (const label of ["EVENTS", ...(data.game ? ["MODEL DETECTIONS"] : receivers)]) {
    const span = document.createElement("span");
    span.textContent = label;
    $("#density-labels").append(span);
  }
  function range() {
    min = focus ? Math.min(18000, duration * 0.9) : 0;
    max = duration;
    scrubber.min = min;
    scrubber.max = max;
    $("#timeline-focus").hidden = !!data.game;
    $("#timeline-focus").textContent = focus ? "FULL SCENARIO" : "DUSK SEGMENT";
    boundsKey = "";
    draw();
  }
  function draw() {
    const width = track.clientWidth,
      height = track.clientHeight,
      ratio = Math.min(devicePixelRatio, 2);
    lastWidth = width;
    canvas.width = width * ratio;
    canvas.height = height * ratio;
    const ctx = canvas.getContext("2d");
    ctx.scale(ratio, ratio);
    const X = (t) => ((t - min) / (max - min)) * width;
    ctx.fillStyle = theme("text");
    ctx.font = '9px "Geist Mono"';
    const morningEnd = Math.min(1500, duration),
      duskStart = Math.min(18000, duration * 0.85);
    for (const [a, b, label, c] of data.game ? [] : [
      [0, morningEnd, "ACT I / MORNING", theme("hairline")],
      [duskStart, duration, "ACT II / DUSK", theme("hairline")],
    ]) {
      if (b < min || a > max) continue;
      const x = Math.max(0, X(a)),
        right = Math.min(width, X(b));
      ctx.fillStyle = c;
      ctx.fillRect(x, 0, right - x, 2);
      ctx.fillStyle = theme("text-2");
    }
    if (data.game && state.mode !== "god") {
      ctx.fillStyle = theme("signal");
      for (const detection of data.game.record.detections) {
        if (detection.t_end < min || detection.t_start > max) continue;
        ctx.globalAlpha = 0.25;
        const left = Math.max(0, X(detection.t_start)), right = Math.min(width, X(detection.t_end));
        ctx.fillRect(left, 19, Math.max(1, right - left), 3);
      }
      ctx.globalAlpha = 1;
    }
    const bins = Math.max(1, Math.floor(width / 3));
    const filtered = state.densityFiltered && state.mode !== "operator",
      oi = data.objects.findIndex((o) => o.id === state.selected);
    $("#density-scope").textContent = filtered
      ? `DENSITY / ${state.selected?.toUpperCase() ?? "NO TRACK"}`
      : "DENSITY / ALL SIGNALS";
    $("#density-scope").hidden = !!data.game;
    $("#density-scope").disabled = state.mode !== "delta";
    if (state.mode === "god")
      $("#density-scope").textContent = "TRUTH MODE / RF HIDDEN";
    receivers.forEach((id, row) => {
      const rf = data.rf[id],
        counts = new Uint16Array(bins);
      if (state.mode === "god") {
        ctx.fillStyle = theme("hairline");
        ctx.fillRect(0, 19 + row * 6, width, 1);
        return;
      }
      for (
        let i = upperBound(rf.t, min - 0.01);
        i < rf.t.length && rf.t[i] <= max;
        i++
      ) {
        if (filtered && rf.obj[i] !== oi) continue;
        const b = Math.min(
          bins - 1,
          Math.floor(((rf.t[i] - min) / (max - min)) * bins),
        );
        counts[b]++;
      }
      const highest = Math.max(1, ...counts),
        y = 19 + row * 6;
      ctx.fillStyle = theme("hairline");
      ctx.fillRect(0, y, width, 2);
      for (let i = 0; i < bins; i++)
        if (counts[i]) {
          ctx.fillStyle = theme("signal");
          ctx.globalAlpha = 0.18 + (0.65 * counts[i]) / highest;
          ctx.fillRect((i * width) / bins, y, Math.max(1, width / bins - 1), 2);
        }
      ctx.globalAlpha = 1;
      const s = data.sensors.find((s) => s.id === id);
      if (s?.dead_t != null && s.dead_t >= min && s.dead_t <= max) {
        ctx.fillStyle = theme("surface");
        ctx.fillRect(X(s.dead_t), y, width - X(s.dead_t), 2);
        ctx.fillStyle = theme("text-2");
        ctx.fillText("×", X(s.dead_t) + 2, y + 6);
      }
    });
    ctx.font = '9px "Geist Mono"';
    ctx.fillStyle = theme("text-2");
    for (let i = 0; i <= 8; i++) {
      const t = min + ((max - min) * i) / 8,
        x = X(t),
        label = timeLabel(data, t).slice(0, 5);
      ctx.textAlign = i === 0 ? "left" : i === 8 ? "right" : "center";
      ctx.fillText(label, x, height - 1);
      ctx.strokeStyle = theme("hairline");
      ctx.beginPath();
      ctx.moveTo(x, 12);
      ctx.lineTo(x, height - 12);
      ctx.stroke();
    }
    const key = `${min}/${max}/${state.mode}`;
    if (key !== boundsKey) {
      boundsKey = key;
      $("#timeline-events").replaceChildren();
      data.events.forEach((e) => {
        if (e.t < min || e.t > max) return;
        const button = document.createElement("button");
        button.className = "timeline-event";
        button.style.left = `${((e.t - min) / (max - min)) * 100}%`;
        button.title = `${timeLabel(data, e.t)} UTC / ${state.mode === "operator" ? "Scenario time marker" : e.label}`;
        button.setAttribute("aria-label", button.title);
        button.onclick = () => seek(e.t);
        $("#timeline-events").append(button);
      });
    }
  }
  scrubber.oninput = () => seek(Number(scrubber.value));
  $("#density-scope").onclick = () => {
    state.densityFiltered = !state.densityFiltered;
    draw();
  };
  $("#timeline-focus").onclick = () => {
    focus = !focus;
    range();
  };
  const observer = new ResizeObserver(() => draw());
  observer.observe(track);
  function update() {
    if (state.t < min || state.t > max) {
      focus = false;
      range();
    }
    const scope = `${state.densityFiltered}/${state.mode}/${state.selected}`;
    if (lastWidth !== track.clientWidth || scope !== lastScope) {
      lastScope = scope;
      draw();
    }
    scrubber.value = state.t;
    scrubber.setAttribute("aria-valuetext", `${timeLabel(data, state.t)} UTC`);
    $("#playhead").style.left = `${((state.t - min) / (max - min)) * 100}%`;
    $("#playhead-label").textContent = timeLabel(data, state.t);
    $("#timeline-range").textContent =
      `${timeLabel(data, min).slice(0, 5)}–${timeLabel(data, max).slice(0, 5)} UTC`;
  }
  range();
  return {
    update,
    destroy() {
      observer.disconnect();
    },
  };
}
