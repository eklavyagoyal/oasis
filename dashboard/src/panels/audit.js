import { escapeHTML as esc, summarize } from "../data.js";
export function renderAudit(data) {
  const a = data.audit,
    summary = summarize(data),
    root = document.querySelector("#audit-panel");
  document.querySelector("#audit-count").textContent = a
    ? `${a.summary.pass}/${a.summary.pass + a.summary.fail + a.summary.skip}`
    : "—";
  function score(a, label, baseline = false) {
    const total = a ? a.summary.pass + a.summary.fail + a.summary.skip : 0;
    return `<div class="audit-score ${baseline ? "baseline" : ""}"><span>${label}</span><strong>${a ? a.summary.pass : "—"}${a ? `<small>/${total}</small>` : ""}</strong><em>${a ? `${a.summary.skip} SKIPPED · ${a.summary.fail} FAILED` : "NOT SUPPLIED"}</em></div>`;
  }
  root.innerHTML = `<div class="audit-kicker">INDEPENDENT VALIDATION</div><h2 class="audit-title">A world you can check.</h2><p class="audit-intro">Every observation has an answer key. These checks measure physical consistency; a comparison appears when a baseline is supplied.</p><div class="audit-scores">${score(a, "OASIS")}${score(a?.baseline, "ONE-SHOT LLM", true)}</div>${a ? a.checks.map((c) => `<details class="audit-check"><summary><span>${esc(c.name.replaceAll("_", " "))}</span><span class="check-value">${esc(c.value == null ? "—" : typeof c.value === "object" ? "DETAILS" : c.value)}</span><span class="check-status ${esc(c.status)}">${esc(c.status)}</span></summary><div class="audit-value">VALUE ${esc(typeof c.value === "object" ? JSON.stringify(c.value) : (c.value ?? "—"))} · THRESHOLD ${esc(typeof c.threshold === "object" ? JSON.stringify(c.threshold) : (c.threshold ?? "—"))}</div><p>${esc(c.detail ?? "No additional detail supplied.")}</p></details>`).join("") : '<div class="audit-empty"><strong>AUDIT NOT SUPPLIED</strong>This dataset has no audit results. Scores appear here when <code>MW.audit</code> is present.<br><br>No checks or baseline scores have been inferred.</div>'}<div class="audit-provenance">DATASET / ${esc(data.scenario.name.toUpperCase())}<br>${summary.objects} TRUTH OBJECTS · ${summary.sensors} SENSORS<br>${summary.detections.toLocaleString()} DETECTIONS · ${summary.fixes.toLocaleString()} FIXES<br>DEM ${summary.terrain} · SHARED VERTICAL DATUM<br>${summary.media} MEDIA RECORDS</div>`;
}
