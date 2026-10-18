import { escapeHTML as esc, summarize } from "../data.js";
export function renderAudit(data) {
  const a = data.audit,
    summary = summarize(data),
    intervals = data.game?.record?.detections?.length,
    root = document.querySelector("#audit-panel");
  document.querySelector("#audit-count").textContent = a
    ? `${a.summary.pass}/${a.summary.pass + a.summary.fail + a.summary.skip}`
    : "—";
  function score(a, label, baseline = false) {
    const total = a ? a.summary.pass + a.summary.fail + a.summary.skip : 0;
    return `<div class="audit-score ${baseline ? "baseline" : ""}"><span>${label}</span><strong>${a ? a.summary.pass : "—"}${a ? `<small>/${total}</small>` : ""}</strong><em>${a ? `${a.summary.skip} SKIPPED · ${a.summary.fail} FAILED` : "NOT SUPPLIED"}</em></div>`;
  }
  const intro = a
    ? `These checks describe internal consistency of this run's generated records and model. They are not field validation.${a.baseline ? " A supplied baseline is shown alongside." : " No one-shot baseline was supplied; no baseline score is shown."}`
    : data.game
      ? "Browser-generated detections are simplified range + terrain line-of-sight intervals. No RF measurements or audit results are supplied; this run is not audited."
      : "No audit results were supplied. This dataset is not audited; missing results are not a pass.";
  const observations = data.game
    ? `${Number.isInteger(intervals) ? intervals.toLocaleString() : "—"} SIMULATED DETECTION INTERVALS · NO RF MEASUREMENTS`
    : `${summary.detections.toLocaleString()} RF DETECTION RECORDS · ${summary.fixes.toLocaleString()} POSITION FIXES`;
  root.innerHTML = `<div class="audit-kicker">RUN DATA AUDIT</div><h2 class="audit-title">What the supplied checks mean.</h2><p class="audit-intro">${esc(intro)}</p><div class="audit-scores">${a ? score(a, "OASIS RUN") : ""}${a?.baseline ? score(a.baseline, "ONE-SHOT LLM", true) : ""}</div>${a ? a.checks.map((c) => `<details class="audit-check"><summary><span>${esc(c.name.replaceAll("_", " "))}</span><span class="check-value">${esc(c.value == null ? "—" : typeof c.value === "object" ? "DETAILS" : c.value)}</span><span class="check-status ${esc(c.status)}">${esc(c.status)}</span></summary><div class="audit-value">VALUE ${esc(typeof c.value === "object" ? JSON.stringify(c.value) : (c.value ?? "—"))} · THRESHOLD ${esc(typeof c.threshold === "object" ? JSON.stringify(c.threshold) : (c.threshold ?? "—"))}</div><p>${esc(c.detail ?? "No additional detail supplied.")}</p></details>`).join("") : `<div class="audit-empty"><strong>NOT AUDITED</strong>${data.game ? "No check results were supplied for this browser-generated run. No score has been inferred." : "No audit results were supplied. Missing results are not a pass."}</div>`}<div class="audit-provenance">DATASET / ${esc(data.scenario.name.toUpperCase())}<br>${summary.objects} TRUTH OBJECTS · ${summary.sensors} CONFIGURED SENSORS<br>${observations}<br>DEM GRID ${summary.terrain} CELLS<br>${summary.media} MEDIA RECORDS</div>`;
}
