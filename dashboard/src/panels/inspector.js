import { countTo } from "../motion.js";
import { theme } from "../theme.js";
import { sample, heightAt, upperBound, escapeHTML as esc } from "../data.js";
const $ = (s) => document.querySelector(s);
export function createInspector(state, onSelect) {
  const data = state.data,
    container = $("#inspector"),
    hasRfMeasurements =
      !data.game && Object.values(data.rf ?? {}).some((r) => r.t?.length),
    hasPositionFixes = !data.game && data.fixes?.t?.length > 0,
    gameIntervals = data.game?.record?.detections?.length,
    rfUnavailable = data.game
      ? `Browser simulation supplies ${Number.isInteger(gameIntervals) ? `${gameIntervals} simplified detection intervals` : "simplified detection intervals"} from range + terrain line-of-sight only; no RF bearing, SNR, received-power, or uncertainty measurements are supplied.`
      : "No RF measurement records were supplied. Bearing, power, SNR, and uncertainty are unavailable.",
    byObject = new Map();
  for (const object of data.objects) {
    const index = data.objects.indexOf(object),
      receivers = {};
    for (const [id, r] of Object.entries(data.rf)) {
      receivers[id] = r.t.flatMap((t, i) =>
        r.obj[i] === index ? [{ t, p: r.pwr[i], los: r.los[i] }] : [],
      );
    }
    byObject.set(object.id, receivers);
  }
  let signature = "",
    chart;
  function render() {
    const key = `${state.mode}/${state.selected}/${state.selectedFix}`;
    if (key === signature) return;
    signature = key;
    $("#inspector-status").textContent =
      state.mode === "operator"
        ? data.game
          ? "SIM INTERVALS ONLY"
          : "SYNTHETIC OBSERVATIONS"
        : state.mode === "god"
          ? data.game
            ? "SIMULATED TRUTH"
            : "GROUND TRUTH"
          : data.game
            ? "SIMULATION"
            : "TRUTH LINKED";
    if (state.mode === "operator") {
      const f = data.fixes,
        index = state.selectedFix;
      if (index != null && index >= 0 && index < f.t.length)
        container.innerHTML = `<div class="no-observation"><strong>POSITION FIX / ${index + 1}</strong>${esc(data.classes[f.cls[index]])}<br><span class="cyan">${f.lat[index].toFixed(5)}° N · ${f.lon[index].toFixed(5)}° E</span><br>CEP50 ${Math.round(f.cep50[index])} m<br>Semi-axes ${Math.round(f.smaj[index])} × ${Math.round(f.smin[index])} m<br>No truth association in Operator mode.</div>`;
      else {
        const message = data.game
          ? rfUnavailable
          : hasPositionFixes
            ? "Select an amber fix on the map to inspect its generated position and uncertainty. Ground-truth associations are hidden in Operator mode."
            : "No position fixes were supplied. There is no reported position or uncertainty to inspect.";
        container.innerHTML = `<div class="no-observation"><strong>${data.game ? "SIMULATED DETECTIONS ONLY." : "NO POSITION FIXES."}</strong>${esc(message)}</div>`;
      }
      return;
    }
    const o = data.objects.find((o) => o.id === state.selected);
    if (!o) {
      container.innerHTML =
        '<div class="no-observation">No truth objects supplied.</div>';
      return;
    }
    container.innerHTML = `<select class="object-picker" aria-label="Inspect truth object">${data.objects.map((obj) => `<option value="${esc(obj.id)}" ${obj.id === o.id ? "selected" : ""}>${esc(obj.id.toUpperCase())}</option>`).join("")}</select><div class="object-class"><span>${esc(o.type.replaceAll("_", " ").toUpperCase())}</span><span class="side-tag ${esc(o.side)}">${esc(o.side.toUpperCase())}</span></div><div class="telemetry-values"><div><strong id="stat-agl">—</strong><span>${data.game ? "SIMULATED AGL" : "TRUTH ALTITUDE AGL"}</span></div><div><strong id="stat-speed">—</strong><span>${data.game ? "SIMULATED SPEED" : "TRUTH GROUND SPEED"}</span></div><div><strong id="stat-masl">—</strong><span>${data.game ? "SIM ALTITUDE / DEM" : "TRUTH ALTITUDE / DEM"}</span></div></div><div id="power-region" ${state.mode === "god" ? "hidden" : ""}><div class="power-heading"><span>MODELED RECEIVED POWER / dBm</span><span>10 MIN WINDOW</span></div>${hasRfMeasurements ? "" : `<div class="no-observation" id="rf-unavailable">${esc(rfUnavailable)}</div>`}<canvas class="power-chart" aria-label="Modeled received power by receiver; dim segments indicate terrain non-line-of-sight" ${hasRfMeasurements ? "" : "hidden"}></canvas><div class="receiver-status" id="receiver-status" ${hasRfMeasurements ? "" : "hidden"}></div><div class="error-summary" ${hasPositionFixes ? "" : "hidden"}><span class="label">FIX ERROR VS SIMULATED TRUTH<small id="fix-error-label">LATEST SCORED FIX</small></span><strong id="stat-error">—</strong></div></div><div id="object-inactive" class="no-observation" hidden>Object inactive at the current time.</div>`;
    container.querySelector("select").onchange = (e) =>
      onSelect(e.target.value);
    chart = container.querySelector("canvas");
  }
  function update() {
    render();
    if (state.mode === "operator") return;
    const object = data.objects.find((o) => o.id === state.selected);
    if (!object) return;
    const p = sample(object, state.t),
      prev = sample(object, state.t - 1);
    $("#object-inactive").hidden = !!p;
    if (p) {
      countTo(
        $("#stat-agl"),
        p.alt - heightAt(data.terrain, p.lon, p.lat),
        0,
        "m",
      );
      countTo($("#stat-masl"), p.alt, 0, "m");
      const speed = prev
        ? Math.hypot(
            (p.lat - prev.lat) * 111320,
            (p.lon - prev.lon) * 111320 * Math.cos((p.lat * Math.PI) / 180),
          )
        : 0;
      countTo($("#stat-speed"), speed, 1, "m/s");
    } else
      for (const id of ["#stat-agl", "#stat-speed", "#stat-masl"])
        $(id).textContent = "—";
    if (state.mode === "god") return;
    if (!hasRfMeasurements) return;
    const entries = byObject.get(object.id),
      width = chart.clientWidth,
      height = chart.clientHeight,
      ratio = Math.min(devicePixelRatio, 2);
    chart.width = width * ratio;
    chart.height = height * ratio;
    const ctx = chart.getContext("2d");
    ctx.scale(ratio, ratio);
    const t0 = state.t - 300,
      t1 = state.t + 300,
      y0 = -125,
      y1 = -40,
      pad = 5;
    const X = (t) => ((t - t0) / (t1 - t0)) * (width - 2 * pad) + pad,
      Y = (p) => height - 8 - ((p - y0) / (y1 - y0)) * (height - 17);
    ctx.lineWidth = 1;
    ctx.strokeStyle = theme("hairline");
    ctx.setLineDash([2, 4]);
    for (const val of [-110, -80, -50]) {
      ctx.beginPath();
      ctx.moveTo(0, Y(val));
      ctx.lineTo(width, Y(val));
      ctx.stroke();
    }
    ctx.setLineDash([]);
    let ri = 0;
    const statuses = [];
    for (const [id, rows] of Object.entries(entries)) {
      const c = ri++ === 0 ? theme("signal") : theme("text-2");
      const times = rows.map((r) => r.t),
        start = Math.max(0, upperBound(times, t0) - 1),
        end = upperBound(times, Math.min(t1, state.t));
      for (let i = start + 1; i < end; i++) {
        const a = rows[i - 1],
          b = rows[i];
        if (b.t - a.t > 8) continue;
        ctx.globalAlpha = b.los ? 0.85 : 0.2;
        ctx.strokeStyle = c;
        ctx.beginPath();
        ctx.moveTo(X(a.t), Y(a.p));
        ctx.lineTo(X(b.t), Y(b.p));
        ctx.stroke();
      }
      ctx.globalAlpha = 1;
      const sensor = data.sensors.find((s) => s.id === id),
        dead = sensor.dead_t != null && state.t > sensor.dead_t;
      const shadow = data.shadow[id],
        visible =
          p && shadow
            ? heightAt(shadow, p.lon, p.lat, "agl") <=
              p.alt - heightAt(data.terrain, p.lon, p.lat)
            : null;
      const last = rows[upperBound(times, state.t) - 1],
        recent = last && state.t - last.t < 5;
      const status = dead
        ? "DOWN"
        : !p
          ? "INACTIVE"
          : visible === false
            ? "TERRAIN NLOS"
            : recent
              ? "DETECTED"
              : visible === true
                ? "LOS / NO RF"
                : "NO RECORD";
      statuses.push(
        `<span class="${dead ? "down" : visible === false ? "nlos" : ""}"><i></i>${esc(id)} ${status}</span>`,
      );
    }
    ctx.strokeStyle = theme("text-3");
    ctx.beginPath();
    ctx.moveTo(X(state.t), 0);
    ctx.lineTo(X(state.t), height);
    ctx.stroke();
    $("#receiver-status").innerHTML = statuses.join("");
    const oi = data.objects.indexOf(object),
      f = data.fixes,
      errors = [];
    for (
      let i = upperBound(f.t, state.t) - 1;
      i >= 0 && f.t[i] >= state.t - 300;
      i--
    )
      if (f.obj[i] === oi && f.err[i] != null) errors.push(f.err[i]);
    $("#stat-error").innerHTML = errors.length
      ? `${Math.round(errors[0])}<small> m</small>`
      : "—";
    $("#fix-error-label").textContent = errors.length
      ? `MEDIAN VS TRUTH ${Math.round([...errors].sort((a, b) => a - b)[Math.floor(errors.length / 2)])} m / ${errors.length} FIXES`
      : "NO SCORED FIX IN LAST 5 MIN";
  }
  return { update };
}
