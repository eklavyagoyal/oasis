"""Log book: one readable, time-ordered account of a finished run.

    uv run python -m mirrorworld.logbook out/<name> [out/<other> ...]   # writes out/<name>/logbook.md

Every line says whose voice it is. TRUTH is what really happened (truth/ and the answer keys). SENSOR is
the first time each sensor recorded each object, joined through that sensor's answer key. C2 is what the
command post concluded from sensor data alone. The book ends with the outcome per hostile (truth next to
what C2 knew, and when) and the audit verdict.
"""
import json
import sys
from datetime import timedelta
from pathlib import Path

import pandas as pd

from .config import coord_label, load


def first_detections(out: Path) -> pd.DataFrame:
    """(sensor, object_id, t, n): first record time and record count per object, for every sensor whose
    answer key maps record_id -> object_id. False alarms and unattributed records are left out."""
    rows = []
    for key in sorted((out / "answer_key").glob("*.csv")):
        folder = out / "sensors" / key.stem
        if not folder.is_dir():  # _frames, _tracks, _site and fused keys describe other files
            continue
        ak = pd.read_csv(key, keep_default_na=False)
        if not {"record_id", "object_id"} <= set(ak.columns):
            continue
        recs = [pd.read_csv(f, usecols=["record_id", "t"]) for f in sorted(folder.glob("*.csv"))
                if {"record_id", "t"} <= set(pd.read_csv(f, nrows=0).columns)]
        if not recs:
            continue
        m = ak.merge(pd.concat(recs), on="record_id")
        m = m[m["object_id"] != ""]
        if "label" in m:
            m = m[m["label"] != "false_alarm"]
        for oid, g in m.groupby("object_id"):
            rows.append({"sensor": key.stem, "object_id": oid, "t": float(g["t"].min()), "n": len(g)})
    return pd.DataFrame(rows, columns=["sensor", "object_id", "t", "n"])


def write(out: Path) -> Path:
    cfg = load(out / "scenario.yaml")
    start = cfg.start
    hms = lambda t: (start + timedelta(seconds=float(t))).strftime("%H:%M:%S")
    objs = {o.id: o for o in cfg.objects}
    tracks = pd.read_csv(out / "truth" / "tracks.csv", usecols=["object_id", "t"])
    span = tracks.groupby("object_id")["t"].agg(["min", "max"])
    c2 = next((s.id for s in cfg.sensors if s.type == "c2"), None)
    site_key = out / "answer_key" / f"{c2}_site.csv"
    site = pd.read_csv(site_key, keep_default_na=False) if c2 and site_key.exists() else pd.DataFrame()
    fate = {r["object_id"]: r for r in site.to_dict("records")}
    events = []  # (t, voice, text)

    for oid, o in objs.items():
        if not o.path or oid not in span.index:
            continue
        t0, t1 = span.loc[oid]
        events.append((t0, "TRUTH", f"**{oid}** ({o.type}, {o.side}) airborne"))
        f = fate.get(oid)
        if f and f.get("ended_at_rendezvous") == "yes":
            end = f"**{oid}** intercepted (closest approach to {f['site_id']}: {f['true_min_dist_site_m']} m)"
        elif f and f.get("truth_status") == "reached":
            end = f"**{oid}** reaches {f['site_id']} ({f['true_min_dist_site_m']} m)"
        elif o.type == "interceptor":
            end = f"**{oid}** at the rendezvous point"
        else:
            end = f"**{oid}** track ends"
        if t1 < cfg.duration_s - 1:
            events.append((t1, "TRUTH", end))
    for o in cfg.objects:
        if o.path is None and o.start_s is not None and o.type in ("jammer",):
            events.append((o.start_s, "TRUTH", f"**{o.id}** on"))
            if o.end_s is not None:
                events.append((o.end_s, "TRUTH", f"**{o.id}** off"))
    for s in cfg.sensors:
        if s.destroyed_by and s.destroyed_by in span.index:
            events.append((span.loc[s.destroyed_by, "max"], "TRUTH", f"**{s.id}** destroyed by {s.destroyed_by}"))

    det = first_detections(out)
    for r in det.sort_values("t").to_dict("records"):
        events.append((r["t"], "SENSOR", f"{r['sensor']} first records **{r['object_id']}** ({r['n']:,} records in all)"))

    alerts, n_info = [], 0
    if c2 and (out / "sensors" / c2 / "alerts.jsonl").exists():
        for line in (out / "sensors" / c2 / "alerts.jsonl").read_text().splitlines():
            a = json.loads(line)
            alerts.append(a)
            if a.get("level") == "info":
                n_info += 1
            else:
                events.append((a["t"], "C2", f"{a['level'].upper()}: {a['message']}"))
    if c2 and (out / "sensors" / c2 / "status.csv").exists():
        for r in pd.read_csv(out / "sensors" / c2 / "status.csv", keep_default_na=False).to_dict("records"):
            if r["t"] > 0:
                events.append((r["t"], "C2", f"{r['asset_id']} → {r['status']} ({r['note']})"))

    hostile = [oid for oid, o in objs.items() if o.side == "hostile" and o.path]
    first_seen = det.groupby("object_id")["t"].min() if len(det) else pd.Series(dtype=float)
    c2_key = out / "answer_key" / f"{c2}.csv"
    c2_first = {}
    if c2 and c2_key.exists() and alerts:
        ak = pd.read_csv(c2_key, keep_default_na=False).merge(
            pd.DataFrame(alerts)[["alert_id", "t"]], on="alert_id")
        c2_first = ak[ak["object_id"] != ""].groupby("object_id")["t"].min().to_dict()

    lines = [f"# Log book: {cfg.name}", "",
             f"{coord_label(cfg.area.lat, cfg.area.lon)} · {cfg.area.size_km:g} km square · "
             f"{start:%d %b %Y %H:%M:%S} UTC · {cfg.duration_s / 60:.0f} min · seed {cfg.seed}", "",
             f"Weather: wind from {cfg.weather.wind_from_deg:.0f}° at {cfg.weather.wind_mps:.1f} m/s, "
             f"{cfg.weather.temp_c:.0f} °C, visibility {cfg.weather.visibility_km:g} km.", "",
             "## Cast", "", "| id | type | side | where |", "|---|---|---|---|"]
    for o in cfg.objects:
        where = (coord_label(*o.pos[:2]) if o.pos else
                 f"moves: {len(o.path)} waypoints" if o.path else "")
        lines.append(f"| {o.id} | {o.type} | {o.side} | {where} |")
    lines += ["", "**Sensors:** " + ", ".join(f"{s.id} ({s.type})" for s in cfg.sensors), "",
              "## Timeline", "",
              "TRUTH is what happened. SENSOR is the first record each sensor made of each object. "
              f"C2 is what the command post concluded from sensor data alone ({n_info:,} routine "
              "new-track notices are left out).", "",
              "| UTC | T+ | voice | event |", "|---|---|---|---|"]
    for t, voice, text in sorted(events, key=lambda e: (e[0], e[1])):
        lines.append(f"| {hms(t)} | {t:7.1f} s | {voice} | {text} |")
    lines += ["", "## Outcome per hostile", "",
              "| hostile | airborne | first sensor record | first C2 alert | truth outcome |",
              "|---|---|---|---|---|"]
    for oid in hostile:
        f = fate.get(oid, {})
        fs, ca = first_seen.get(oid), c2_first.get(oid)
        lines.append(f"| {oid} | {hms(span.loc[oid, 'min'])} | "
                     f"{f'{hms(fs)} (+{fs - span.loc[oid, "min"]:.0f} s)' if fs is not None else 'never'} | "
                     f"{f'{hms(ca)} (+{ca - span.loc[oid, "min"]:.0f} s)' if ca is not None else 'none'} | "
                     f"{'intercepted' if f.get('ended_at_rendezvous') == 'yes' else f.get('truth_status', '—')} |")
    audit_p = out / "audit.json"
    if audit_p.exists():
        audit = json.loads(audit_p.read_text())
        s = audit["summary"]
        lines += ["", "## Audit (independent physics checks)", "",
                  f"**{s['pass']} pass · {s['fail']} fail · {s['skip']} skip**", "",
                  "| check | status | value |", "|---|---|---|"]
        lines += [f"| {c['name']} | {c['status']} | {c['value'] if c['value'] is not None else '—'} |"
                  for c in audit["checks"]]
    path = out / "logbook.md"
    path.write_text("\n".join(lines) + "\n")
    return path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    for arg in sys.argv[1:]:
        print(write(Path(arg)))
