"""C2: the command post's event log and status board, built from the other sensors' outputs.

Runs LAST (put the C2 sensor last in the scenario) and reads only what the other sensors
wrote: `fused/fixes.csv` (crossed-bearing RF fixes) and `sensors/*/tracks.csv` (radar track
updates) into C2 tracks, plus every detection/message stream for the SENSOR SILENT check.
Everything under `sensors/<c2>/` is computable from those files and what C2 knows about its
own side from the config: the positions of site/response assets, its own interceptors'
launch times and its own sensors' sites. Truth is consulted only to write answer_key/.

Design decisions the brief leaves open:
- Association is nearest-neighbour within 800 m of the constant-velocity prediction and
  20 s of the track's last update. A gap > 20 s therefore starts a fresh track: the state
  machine (TENTATIVE -> CONFIRMED -> LOST -> DROPPED) has no recovery path, so a re-acquired
  target becomes a new track and the answer key attributes both to the same object.
- The track state is a constant-velocity alpha-beta filter: position/velocity are corrected
  by the residual against the prediction, so the ~400 m scatter of crossed-bearing fixes
  does not fragment one emitter into a new track per fix.
- DROPPED fires 300 s after the last update in any state, so stale TENTATIVE garbage dies
  silently; LOST CONTACT is raised only for CONFIRMED tracks.
- SENSOR SILENT keys on a stream *stopping* (the brief's "a sensor that stops reporting"):
  its last detection follows >= 3 detections in its final 60 s, then 60 s of silence fit
  inside the window while another stream still reports after it stopped. Gap-based
  detection would fire on every traffic lull and drown the real dead sensor.
- "responding" for a ground response asset is its dispatch at the first warn/critical
  alert; for an interceptor it is its launch time (C2 launched it).
- Any response asset's outcome is "rendezvous reported" when a C2 track update lands within
  500 m of the asset's final position within 10 s of its end, else "no contact"; an asset
  without an end runs to the scenario end. Own-asset positions/times come from the config
  and the asset's own state (its telemetry), never from other sensors' outputs.
"""
import json
import math
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..catalog import CATALOG

GATE_M, GATE_S = 800.0, 20.0   # nearest-neighbour association gate (space, time)
CONFIRM_N = 3                  # updates to leave TENTATIVE
LOST_S, DROP_S = 60.0, 300.0   # silence that loses / drops a track
SITE_WARN_M, SITE_CRIT_M = 3000.0, 1000.0
SILENT_S = 60.0                # stream silence that flags a dead sensor
RENDEZVOUS_M, RENDEZVOUS_S = 500.0, 10.0
GRID_M = 1000.0
# alpha-beta gains for the constant-velocity state: fixes scatter ~400 m per axis, so the
# position is heavily smoothed and the velocity is only nudged by the residual (tuned on the
# hero fix stream: most remaining track breaks are single fixes > 800 m apart, i.e. the gate)
ALPHA, BETA = 0.25, 0.05


# --------------------------------------------------------------------------- grid

def grid_label(x_m, y_m, size_km):
    """1 km cell over the scenario square: columns A.. from west, rows 1.. from south."""
    n = max(1, int(round(size_km * 1000.0 / GRID_M)))
    col = min(max(int((x_m + size_km * 500.0) // GRID_M), 0), n - 1)
    row = min(max(int((y_m + size_km * 500.0) // GRID_M), 0), n - 1)
    s, i = "", col + 1
    while i:  # spreadsheet-style letters: A..Z, AA..
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return f"{s}{row + 1}"


# --------------------------------------------------------------------------- tracker

@dataclass
class Obs:
    """One position report from a source sensor output file."""
    t: float
    x: float
    y: float
    cls: str = ""
    source: str = ""           # "rf_fix" | "radar"
    recs: tuple = ()           # contributing source record ids (answer-key provenance)


@dataclass
class Track:
    id: str
    t: float
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    state: str = "TENTATIVE"
    n: int = 0
    cls: str = ""
    sources: set = field(default_factory=set)
    recs: list = field(default_factory=list)    # (t, recs) per update
    updates: list = field(default_factory=list)  # (t, x, y, state) per update
    dist: dict = field(default_factory=dict)    # site -> distance at previous update
    fired: set = field(default_factory=set)     # (site, "approach"|"close") already raised
    rows: list = field(default_factory=list)    # rows written for this track

    def predict(self, t):
        dt = t - self.t
        return self.x + self.vx * dt, self.y + self.vy * dt


def _alert(t, level, kind, track, message, sources, size_km, x, y, site=None, site_xy=None):
    return dict(t=t, level=level, kind=kind, track_id=track.id if track else "",
                grid=grid_label(x, y, size_km), message=message, sources=list(sources),
                x=x, y=y, site=site, site_xy=site_xy)


def track(obs, sites, size_km, duration):
    """Fuse observations into C2 tracks. Returns (rows, alerts, tracks).

    rows carry track_id, t, x, y, state (after the update / at the transition), cls and
    source; alerts carry t, level, kind, track_id, grid, message, sources and hidden
    x/y/site fields for the CoT and the answer key.
    """
    rows, alerts, tracks = [], [], []
    for o in sorted(obs, key=lambda o: o.t):
        best, best_d = None, GATE_M
        for tr in tracks:
            dt = o.t - tr.t
            if not 0.0 <= dt <= GATE_S:
                continue
            px, py = tr.predict(o.t)
            d = math.hypot(o.x - px, o.y - py)
            if d <= best_d:
                best, best_d = tr, d
        if best is None:
            best = Track(id=f"TRK-{len(tracks):06d}", t=o.t, x=o.x, y=o.y)
            tracks.append(best)
            alerts.append(_alert(o.t, "info", "NEW TRACK", best,
                                 f"NEW TRACK {best.id}: {o.cls or 'unclassified'} first seen at "
                                 f"{grid_label(o.x, o.y, size_km)}",
                                 [o.source], size_km, o.x, o.y))
        else:
            dt = o.t - best.t
            px, py = best.predict(o.t)          # constant-velocity prediction
            rx, ry = o.x - px, o.y - py         # residual against it
            best.x, best.y = px + ALPHA * rx, py + ALPHA * ry
            if dt > 0:
                best.vx += BETA * rx / dt
                best.vy += BETA * ry / dt
            best.t = o.t
        best.n += 1
        best.state = "CONFIRMED" if best.n >= CONFIRM_N else "TENTATIVE"
        if o.cls:
            best.cls = o.cls
        best.sources.add(o.source)
        best.recs.append((o.t, o.recs))
        best.updates.append((o.t, best.x, best.y, best.state))
        row = dict(track_id=best.id, t=o.t, x=best.x, y=best.y, state=best.state, cls=best.cls, source=o.source)
        rows.append(row)
        best.rows.append(row)
        for sid, sx, sy in sites:
            d = math.hypot(best.x - sx, best.y - sy)
            key_app, key_close = (sid, "approach"), (sid, "close")
            if d <= SITE_CRIT_M and key_close not in best.fired:
                if key_app not in best.fired:  # keep NEW -> APPROACHING -> CLOSE order
                    best.fired.add(key_app)
                    alerts.append(_alert(o.t, "warn", "APPROACHING", best,
                                         f"APPROACHING {sid}: {best.id} at {d:.0f} m",
                                         sorted(best.sources), size_km, best.x, best.y, sid, (sx, sy)))
                best.fired.add(key_close)
                alerts.append(_alert(o.t, "critical", "CLOSE", best,
                                     f"CLOSE TO {sid}: {best.id} at {d:.0f} m",
                                     sorted(best.sources), size_km, best.x, best.y, sid, (sx, sy)))
            elif (d <= SITE_WARN_M and key_app not in best.fired
                  and (best.dist.get(sid) is None or d < best.dist[sid])):
                best.fired.add(key_app)
                alerts.append(_alert(o.t, "warn", "APPROACHING", best,
                                     f"APPROACHING {sid}: {best.id} at {d:.0f} m",
                                     sorted(best.sources), size_km, best.x, best.y, sid, (sx, sy)))
            best.dist[sid] = d

    # silence transitions (last known position), only while they fit in the window
    for tr in tracks:
        if tr.state == "CONFIRMED" and tr.t + LOST_S <= duration:
            t = round(tr.t + LOST_S, 3)
            row = dict(track_id=tr.id, t=t, x=tr.x, y=tr.y, state="LOST", cls=tr.cls,
                       source=";".join(sorted(tr.sources)))
            rows.append(row)
            tr.rows.append(row)
            alerts.append(_alert(t, "warn", "LOST CONTACT", tr,
                                 f"LOST CONTACT {tr.id}: no update for {LOST_S:.0f} s",
                                 sorted(tr.sources), size_km, tr.x, tr.y))
        if tr.t + DROP_S <= duration:
            t = round(tr.t + DROP_S, 3)
            row = dict(track_id=tr.id, t=t, x=tr.x, y=tr.y, state="DROPPED", cls=tr.cls,
                       source=";".join(sorted(tr.sources)))
            rows.append(row)
            tr.rows.append(row)
    rows.sort(key=lambda r: r["t"])
    return rows, alerts, tracks


# --------------------------------------------------------------------------- dead sensors

def silent(streams, grids, size_km, duration, iso=repr):
    """SENSOR SILENT alerts for detection streams that stop while others keep reporting."""
    alerts = []
    for sid in sorted(streams):
        ts = np.asarray(streams[sid], dtype=float)
        if ts.size == 0:
            continue
        t_last = float(ts.max())
        if t_last + SILENT_S > duration:  # cannot confirm 60 s of silence in-window
            continue
        if int((ts >= t_last - SILENT_S).sum()) < 3:  # was not producing when it stopped
            continue
        others = sorted(s for s, ots in streams.items()
                        if s != sid and bool(((ots > t_last) & (ots <= t_last + SILENT_S)).any()))
        if not others:
            continue
        t = round(t_last + SILENT_S, 3)
        x, y = grids[sid]
        alerts.append(_alert(t, "warn", "SENSOR SILENT", None,
                             f"SENSOR SILENT {sid}: no detections since {iso(round(t_last, 3))} "
                             f"({', '.join(others)} still reporting)",
                             [sid], size_km, x, y))
    return alerts


# --------------------------------------------------------------------------- answer attribution

def vote(pairs):
    """(object_id, label) behind a set of source records: majority, 'mixed' on a tie."""
    if not pairs:
        return "", "false_alarm"
    counts = Counter(o for o, _ in pairs)
    top = max(counts.values())
    winners = [o for o, c in counts.items() if c == top]
    if len(winners) > 1:
        return "mixed", "mixed"
    obj = winners[0]
    labels = [lb for o, lb in pairs if o == obj]
    return obj, Counter(labels).most_common(1)[0][0]


# --------------------------------------------------------------------------- input readers

def _observations(ctx, skip_id):
    """Position reports to fuse: RF crossed-bearing fixes and radar track updates."""
    obs, used, notes = [], {}, []
    p = ctx.out / "fused" / "fixes.csv"
    if p.exists():
        fx = pd.read_csv(p)
        for r in fx.itertuples():
            x, y = ctx.world.to_xy(r.lat, r.lon)
            recs = tuple(v for v in str(r.record_ids).split(";") if v and v != "nan")
            obs.append(Obs(round(float(r.t), 3), float(x), float(y), str(r.sig_class), "rf_fix", recs))
        used["fused/fixes.csv"] = len(fx)
    else:
        notes.append("no fused/fixes.csv: RF lane produced no fixes")
    n_radar = 0
    for p in sorted((ctx.out / "sensors").glob("*/tracks.csv")):
        if p.parent.name == skip_id:
            continue  # our own track log, not a source
        df = pd.read_csv(p)
        if "t" not in df.columns or df.empty:
            continue
        if {"lat", "lon"} <= set(df.columns):
            x, y = ctx.world.to_xy(df["lat"].to_numpy(float), df["lon"].to_numpy(float))
        elif {"x_m", "y_m"} <= set(df.columns):
            x, y = df["x_m"].to_numpy(float), df["y_m"].to_numpy(float)
        else:
            notes.append(f"sensors/{p.parent.name}/tracks.csv: no lat/lon or x_m/y_m, skipped")
            continue
        cls = df["class"].astype(str).to_numpy() if "class" in df.columns else np.full(len(df), "")
        recs = (df["record_id"].astype(str).to_numpy() if "record_id" in df.columns
                else np.full(len(df), ""))
        for i in range(len(df)):
            obs.append(Obs(round(float(df["t"].iloc[i]), 3), float(x[i]), float(y[i]), cls[i],
                           "radar", tuple([recs[i]]) if recs[i] and recs[i] != "nan" else ()))
        used[f"sensors/{p.parent.name}/tracks.csv"] = len(df)
        n_radar += len(df)
    if not n_radar:
        notes.append("no radar tracks.csv: radar lane produced no track updates")
    return obs, used, notes


def _streams(ctx, skip_id):
    """Detection times per sensor from any stream file (data-driven SENSOR SILENT)."""
    streams = {}
    for s in ctx.cfg.sensors:
        if s.id == skip_id:
            continue
        folder = ctx.out / "sensors" / s.id
        if not folder.is_dir():
            continue
        ts = []
        for p in sorted(folder.glob("*.csv")):
            if p.name in ("media.csv", "status.csv"):
                continue
            df = pd.read_csv(p)
            if "t" in df.columns:
                ts.append(df["t"].to_numpy(float))
        for p in sorted(folder.glob("*.jsonl")):
            for line in p.read_text().splitlines():
                try:
                    ts.append([float(json.loads(line)["t"])])
                except (ValueError, KeyError, json.JSONDecodeError):
                    continue
        if ts:
            streams[s.id] = np.unique(np.concatenate(ts))
    return streams


# --------------------------------------------------------------------------- own-side assets

def _assets(ctx):
    """(id, kind, start_t, end_t, end_x, end_y) for our own site/response/interceptor assets."""
    out = []
    for o in ctx.objects.values():
        kind = CATALOG[o.type]["kind"]
        interceptor = o.type == "interceptor" and o.side == "friendly"
        if kind not in ("site", "response") and not interceptor:
            continue
        if o.end_s is not None:
            end_t = float(o.end_s)
        else:
            t = ctx.truth.loc[ctx.truth["object_id"] == o.id, "t"]
            end_t = float(t.max()) if len(t) else float(ctx.cfg.duration_s)
        if o.pos is not None:
            x, y = ctx.world.to_xy(o.pos[0], o.pos[1])
            end_x, end_y = float(x), float(y)
        else:
            st = ctx.state(o.id, end_t)  # our own asset's telemetry, not another sensor's output
            end_x, end_y = float(st["x"]), float(st["y"])
        out.append((o.id, "site" if kind == "site" else ("interceptor" if interceptor else "response"),
                    float(o.start_s), end_t, end_x, end_y))
    return out


def _status_rows(ctx, alerts, tracks, assets, duration):
    rows = []
    first = next((a for a in alerts if a["level"] in ("warn", "critical")), None)
    for aid, kind, start_t, end_t, ex, ey in assets:
        if kind == "site":
            best = None
            for tr in tracks:
                for t, x, y, st in tr.updates:
                    if st == "CONFIRMED" and math.hypot(x - ex, y - ey) <= SITE_CRIT_M:
                        if best is None or t < best[0]:
                            best = (t, tr.id, math.hypot(x - ex, y - ey))
            if best:
                rows.append(dict(asset_id=aid, t=round(best[0], 3), status="approached",
                                 note=f"confirmed track {best[1]} within {best[2]:.0f} m"))
            else:
                rows.append(dict(asset_id=aid, t=round(float(duration), 3), status="not reached",
                                 note="no confirmed track within 1 km"))
            continue
        rows.append(dict(asset_id=aid, t=round(start_t, 3), status="available", note="asset on hand"))
        if first is not None:
            rows.append(dict(asset_id=aid, t=first["t"], status="alerted",
                             note=f"first {first['level']} alert {first['alert_id']}"))
            if kind == "response":
                rows.append(dict(asset_id=aid, t=first["t"], status="responding",
                                 note=f"dispatched on {first['alert_id']}"))
        if kind == "interceptor":
            rows.append(dict(asset_id=aid, t=round(start_t, 3), status="responding",
                             note="launched by C2"))
        hit = next(((tr.id, math.hypot(x - ex, y - ey))
                    for tr in tracks for t, x, y, _ in tr.updates
                    if abs(t - end_t) <= RENDEZVOUS_S and math.hypot(x - ex, y - ey) <= RENDEZVOUS_M),
                   None)
        rows.append(dict(asset_id=aid, t=round(end_t, 3),
                         status="rendezvous reported" if hit else "no contact",
                         note=(f"C2 track {hit[0]} within {hit[1]:.0f} m at its end"
                               if hit else "no C2 track within 500 m at its end")))
    rows.sort(key=lambda r: r["t"])
    return rows


# --------------------------------------------------------------------------- answer key

def _true_min_dist(ctx, obj_id, sx, sy):
    tr = ctx.truth.loc[ctx.truth["object_id"] == obj_id]
    if tr.empty:
        return np.nan
    return float(np.hypot(tr["x_m"] - sx, tr["y_m"] - sy).min())


def _answers(ctx, console_id, alerts, tracks, assets):
    amap = {}
    for p in sorted((ctx.out / "answer_key").glob("*.csv")):
        df = pd.read_csv(p)
        if {"record_id", "object_id", "label"} <= set(df.columns):
            for r in df.itertuples():
                amap[str(r.record_id)] = ("" if pd.isna(r.object_id) else str(r.object_id), str(r.label))
    by_id = {tr.id: tr for tr in tracks}
    rows = []
    for a in alerts:
        recs = []
        tr = by_id.get(a["track_id"])
        if tr is not None:
            for t, rs in tr.recs:
                if t <= a["t"] + 1e-9:
                    recs += [amap[r] for r in rs if r in amap]
        obj, label = vote(recs)
        d = np.nan
        if a.get("site") and obj not in ("", "mixed"):
            d = _true_min_dist(ctx, obj, *a["site_xy"])
        rows.append(dict(alert_id=a["alert_id"], object_id=obj, label=label,
                         true_min_dist_site_m="" if np.isnan(d) else round(d, 1)))
    pd.DataFrame(rows, columns=["alert_id", "object_id", "label", "true_min_dist_site_m"]).to_csv(
        ctx.out / "answer_key" / f"{console_id}.csv", index=False)

    # truth site status per hostile drone
    int_ends = [end_t for _, kind, _, end_t, _, _ in assets if kind == "interceptor"]
    rows = []
    for o in ctx.objects.values():
        if o.side != "hostile" or CATALOG[o.type]["kind"] != "drone":
            continue
        t = ctx.truth.loc[ctx.truth["object_id"] == o.id, "t"]
        end = float(t.max()) if len(t) else np.nan
        for aid, kind, _, _, sx, sy in assets:
            if kind != "site":
                continue
            d = _true_min_dist(ctx, o.id, sx, sy)
            rows.append(dict(
                object_id=o.id, site_id=aid,
                true_min_dist_site_m=round(d, 1) if np.isfinite(d) else "",
                truth_status=("reached" if d < 100.0 else "approached" if d < 1000.0 else "not reached"),
                ended_at_rendezvous="yes" if any(abs(end - ie) <= 1.0 for ie in int_ends) else "no"))
    pd.DataFrame(rows, columns=["object_id", "site_id", "true_min_dist_site_m",
                                "truth_status", "ended_at_rendezvous"]).to_csv(
        ctx.out / "answer_key" / f"{console_id}_site.csv", index=False)


# --------------------------------------------------------------------------- writers

def _write_cot(alerts, ctx, path):
    root = ET.Element("events")
    for a in alerts:
        ts = ctx.iso(a["t"])
        lat, lon = ctx.world.to_ll(a["x"], a["y"])
        try:
            hae = float(ctx.world.height(a["x"], a["y"]))
        except ValueError:  # a prediction off the mapped area: hae unknown
            hae = 0.0
        ev = ET.SubElement(root, "event", version="2.0", uid=f"mw-{ctx.cfg.name}-{a['alert_id']}",
                           type="b-a", how="m-r", time=ts, start=ts, stale=ctx.iso(a["t"] + 300))
        ET.SubElement(ev, "point", lat=f"{float(lat):.6f}", lon=f"{float(lon):.6f}",
                      hae=f"{hae:.1f}", ce="9999999.0", le="9999999.0")
        d = ET.SubElement(ev, "detail")
        ET.SubElement(d, "contact", callsign=f"{a['kind']} {a['track_id']}".strip())
        ET.SubElement(d, "remarks").text = a["message"]
    ET.indent(root)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def run(sensors, ctx):
    console = sensors[0]  # one C2 console per scenario
    out = ctx.out / "sensors" / console.id
    out.mkdir(parents=True, exist_ok=True)
    (ctx.out / "answer_key").mkdir(parents=True, exist_ok=True)
    size, duration = ctx.cfg.area.size_km, ctx.cfg.duration_s

    assets = _assets(ctx)
    sites = [(aid, ex, ey) for aid, kind, _, _, ex, ey in assets if kind == "site"]
    obs, used, notes = _observations(ctx, console.id)
    streams = _streams(ctx, console.id)
    if len(sensors) > 1:
        notes.append(f"extra c2 sensors ignored: {[s.id for s in sensors[1:]]}")

    rows, alerts, tracks = track(obs, sites, size, duration)
    sensor_xy = {s.id: ctx.sensor_xyz(s)[:2] for s in ctx.cfg.sensors}
    alerts += silent(streams, {sid: sensor_xy[sid] for sid in streams}, size, duration, ctx.iso)

    alerts.sort(key=lambda a: a["t"])  # stable: emission order breaks ties
    for i, a in enumerate(alerts):
        a["alert_id"] = f"ALT-{i:06d}"
        a["t"] = round(a["t"], 3)
        a["time_utc"] = ctx.iso(a["t"])

    status = _status_rows(ctx, alerts, tracks, assets, duration)
    media = [dict(t=a["t"], kind="event", path=f"alerts.jsonl#{a['alert_id']}") for a in alerts
             if a["level"] == "critical" or a["kind"] in ("LOST CONTACT", "SENSOR SILENT")]
    media += [dict(t=r["t"], kind="event", path=f"status.csv#{r['asset_id']}") for r in status
              if r["status"] in ("rendezvous reported", "no contact")]
    media.sort(key=lambda r: r["t"])

    track_rows = []
    for r in rows:
        t = round(r["t"], 3)
        lat, lon = ctx.world.to_ll(r["x"], r["y"])
        track_rows.append({"track_id": r["track_id"], "time_utc": ctx.iso(t), "t": t,
                           "lat": round(float(lat), 6), "lon": round(float(lon), 6),
                           "state": r["state"], "class": r["cls"],
                           "grid": grid_label(r["x"], r["y"], size), "sources": r["source"]})
    pd.DataFrame(track_rows, columns=["track_id", "time_utc", "t", "lat", "lon", "state",
                                      "class", "grid", "sources"]).to_csv(out / "tracks.csv", index=False)
    with open(out / "alerts.jsonl", "w") as f:
        for a in alerts:
            f.write(json.dumps({k: a[k] for k in
                                ("alert_id", "time_utc", "t", "level", "track_id", "grid",
                                 "message", "sources")}) + "\n")
    pd.DataFrame([dict(asset_id=r["asset_id"], time_utc=ctx.iso(r["t"]), t=round(r["t"], 3),
                       status=r["status"], note=r["note"]) for r in status]).to_csv(
        out / "status.csv", index=False)
    pd.DataFrame([dict(t=round(r["t"], 3), time_utc=ctx.iso(round(r["t"], 3)),
                       kind=r["kind"], path=r["path"]) for r in media],
                 columns=["t", "time_utc", "kind", "path"]).to_csv(out / "media.csv", index=False)
    _write_cot(alerts, ctx, out / "alerts.cot.xml")
    (out / "status.json").write_text(json.dumps({
        "sensor_id": console.id,
        "inputs_found": used,
        "detection_streams": {sid: int(ts.size) for sid, ts in sorted(streams.items())},
        "notes": notes,
    }, indent=1))

    _answers(ctx, console.id, alerts, tracks, assets)
