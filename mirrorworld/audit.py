"""Independent audit of a run directory: the jury's "why not just ask an LLM?" proof.

Reads out/<name>/ like an outside observer: the data under sensors/ and fused/, then
truth/ and answer_key/ only to attribute records to objects. Every number is recomputed
from geometry, the real DEM line of sight, causality and statistics — the answer key's
derived columns (true_*, los, path_loss_db, error_m, ...) are never trusted, and nothing
from our propagation model is reused.

    python -m mirrorworld audit out/<name> [--baseline <dir>]
"""
import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from . import config, itu
from .catalog import CATALOG
from .world import World

FORBIDDEN_COLS = {"object_id", "los", "label"}
FORBIDDEN_PREFIXES = ("true_", "error_")

CHECKS = [
    ("provenance", "Provenance"),
    ("clock", "Clock sync"),
    ("bearing_geometry", "Bearing geometry"),
    ("terrain_shadow", "Terrain shadow"),
    ("occlusion_gaps", "Occlusion gaps"),
    ("fix_calibration", "Fix calibration"),
    ("range_law", "Range law"),
    ("acoustic_delay", "Acoustic delay"),
    ("spoof_visible", "Spoof visibility"),
    ("cross_sensor_time", "Cross-sensor time"),
]


MIN_N, MIN_LOG_SPAN = 20, 0.15  # smallest samples a check will judge; below that it SKIPs


def _result(cid, name, status, value, threshold, detail):
    return {"id": cid, "name": name, "status": status, "value": value,
            "threshold": threshold, "detail": detail}


def _wrap180(a):
    return (np.asarray(a, float) + 180.0) % 360.0 - 180.0


def _iso_epoch(s):
    return pd.Timestamp(s).timestamp()


@dataclass
class Scene:
    """One run directory, loaded the way an auditor would: files first, no engine state."""

    root: Path
    cfg: config.Scenario
    world: World
    tracks: pd.DataFrame
    types: dict  # object id -> catalog type
    sides: dict  # object id -> side
    window: tuple | None = None  # (t0, t1): audit only this slice, same for every dataset compared

    def __post_init__(self):
        self._recs = {}

    @classmethod
    def load(cls, root, window=None):
        root = Path(root)
        yml = root / "scenario.yaml"
        if not yml.exists():
            raise FileNotFoundError(
                f"{yml} not found — audit needs the scenario (terrain + clock); "
                "run `python -m mirrorworld run <yaml>` first")
        cfg = config.load(yml)
        world = World(cfg)
        tracks = pd.read_csv(root / "truth" / "tracks.csv")
        tracks["x"], tracks["y"] = world.to_xy(tracks["lat"].to_numpy(), tracks["lon"].to_numpy())
        types, sides = {}, {}
        objp = root / "truth" / "objects.csv"
        if objp.exists():
            o = pd.read_csv(objp)
            types = dict(zip(o["id"].astype(str), o["type"].astype(str)))
            if "side" in o.columns:
                sides = dict(zip(o["id"].astype(str), o["side"].astype(str)))
        return cls(root, cfg, world, tracks, types, sides, window)

    # --- truth -----------------------------------------------------------
    def state(self, obj, t):
        """x, y, z MSL at times t ((..., 3) out, NaN where the object is inactive)."""
        tt = np.asarray(t, float)
        r = self.tracks[self.tracks["object_id"] == obj].sort_values("t")
        if r.empty:
            return np.full(tt.shape + (3,), np.nan)
        ts = r["t"].to_numpy()
        vals = [np.interp(tt, ts, r[c].to_numpy(), left=np.nan, right=np.nan)
                for c in ("x", "y", "alt_msl_m")]
        return np.stack(vals, -1)

    def span(self, obj):
        r = self.tracks.loc[self.tracks["object_id"] == obj, "t"]
        return (float(r.min()), float(r.max())) if len(r) else None

    # --- sensors ---------------------------------------------------------
    def sensors(self):
        d = self.root / "sensors"
        return sorted(p.name for p in d.iterdir() if p.is_dir()) if d.exists() else []

    def site(self, sid):
        p = self.root / "sensors" / sid / "site.json"
        if not p.exists():
            return None
        s = json.loads(p.read_text())
        x, y = self.world.to_xy(s["lat"], s["lon"])
        return np.array([float(x), float(y), float(s["alt_msl_m"])])

    def recs(self, sid):
        """Sensor records joined with answer-key *provenance* (object_id/link/label) only,
        plus recomputed geometry from truth + site. Cached: one DEM pass per sensor."""
        if sid in self._recs:
            return self._recs[sid]
        folder = self.root / "sensors" / sid
        site = self.site(sid)
        key = self.root / "answer_key" / f"{sid}.csv"
        key = pd.read_csv(key) if key.exists() else None
        frames = []
        for p in sorted(folder.glob("*.csv")):
            df = pd.read_csv(p)
            if "record_id" in df.columns and "t" in df.columns:
                frames.append(df)
        out = None
        if frames:
            df = pd.concat(frames, ignore_index=True)
            if self.window:
                df = df[df["t"].between(*self.window)].reset_index(drop=True)
            if key is not None:
                prov = [c for c in ("record_id", "object_id", "link", "label") if c in key.columns]
                df = df.merge(key[prov], on="record_id", how="left")
            for c in ("object_id", "link", "label"):
                if c not in df.columns:
                    df[c] = ""
            t = df["t"].to_numpy(float)
            obj = df["object_id"].fillna("").astype(str).to_numpy()
            xyz = np.full((len(df), 3), np.nan)
            for o in pd.unique(obj):
                if o:
                    xyz[obj == o] = self.state(o, t[obj == o])
            ok = np.isfinite(xyz).all(1)
            if site is None:
                rng = brg = np.full(len(df), np.nan)
                los = np.zeros(len(df), bool)
            else:
                d = xyz - site
                rng = np.linalg.norm(d, axis=1)
                brg = np.degrees(np.arctan2(d[:, 0], d[:, 1])) % 360.0
                los = np.zeros(len(df), bool)
                los[ok] = self.world.los(np.broadcast_to(site, (int(ok.sum()), 3)), xyz[ok])
            out = dict(df=df, site=site, xyz=xyz, ok=ok, rng=rng, brg=brg, los=los,
                       eirp=_eirp(self, df))
        self._recs[sid] = out
        return out


def _eirp(sc, df):
    """Catalog EIRP per record from the answer-key link ('<owner>:<link name>')."""
    out = np.full(len(df), np.nan)
    if "link" not in df.columns:
        return out
    cache, links = {}, df["link"].fillna("").astype(str).to_numpy()
    for i, lk in enumerate(links):
        if ":" not in lk:
            continue
        owner, name = lk.split(":", 1)
        typ = sc.types.get(owner)
        if typ is None:
            continue
        if (typ, name) not in cache:
            cache[(typ, name)] = next(
                (float(L["eirp_dbm"]) for L in CATALOG.get(typ, {}).get("links", [])
                 if L["name"] == name), np.nan)
        out[i] = cache[(typ, name)]
    return out


# --------------------------------------------------------------------------- checks

def check_provenance(sc):
    """Every sensor record has exactly one answer-key row; sensor files carry no truth columns."""
    issues, seen = [], set()
    for sid in sc.sensors():
        folder = sc.root / "sensors" / sid
        key = sc.root / "answer_key" / f"{sid}.csv"
        key = pd.read_csv(key) if key.exists() else None
        kcount = (key["record_id"].astype(str).value_counts()
                  if key is not None and "record_id" in key.columns else None)
        for p in sorted(folder.glob("*.csv")):
            df = pd.read_csv(p)
            rel = p.relative_to(sc.root)
            bad = [c for c in df.columns
                   if c in FORBIDDEN_COLS or c.startswith(FORBIDDEN_PREFIXES)]
            if bad:
                issues.append(f"{rel}: truth columns {sorted(bad)}")
            leaked = [c for c in df.columns if df[c].dtype == object and df[c].isin(set(sc.types)).any()]
            if leaked:
                issues.append(f"{rel}: truth object ids as values in {sorted(leaked)}")
            if "record_id" not in df.columns:
                continue
            ids = df["record_id"].fillna("").astype(str)
            if ids.duplicated().any():
                issues.append(f"{rel}: {int(ids.duplicated().sum())} duplicate record ids")
            dupes = seen & set(ids)
            if dupes:
                issues.append(f"{rel}: {len(dupes)} record ids reused across files")
            seen |= set(ids)
            if kcount is None:
                issues.append(f"{rel}: no answer_key/{sid}.csv to attribute {len(ids)} records")
                continue
            missing = multi = 0
            for i in ids.unique():
                c = int(kcount.get(i, 0))
                missing += c == 0
                multi += c > 1
            if missing:
                issues.append(f"{rel}: {missing} record ids with no answer-key row")
            if multi:
                issues.append(f"{rel}: {multi} record ids with multiple answer-key rows")
    n = len(issues)
    return _result("provenance", "Provenance", "PASS" if n == 0 else "FAIL", n, "0 issues",
                   "clean" if n == 0 else "; ".join(issues[:5]) + (f" (+{n - 5} more)" if n > 5 else ""))


def check_clock(sc):
    """Every time_utc parses, equals start + t within 1 ms, stays in the window, is monotonic."""
    start = sc.cfg.start.timestamp()
    problems, max_err, nrows = [], 0.0, 0
    files = [sc.root / "truth" / "tracks.csv", sc.root / "fused" / "fixes.csv"]
    files += [p for sid in sc.sensors() for p in sorted((sc.root / "sensors" / sid).glob("*.csv"))]
    for p in files:
        if not p.exists():
            continue
        df = pd.read_csv(p)
        rel = p.relative_to(sc.root)
        if ("t" in df.columns) != ("time_utc" in df.columns):
            problems.append(f"{rel}: has {'t' if 't' in df.columns else 'time_utc'} but not both")
            continue
        if "t" not in df.columns:
            continue
        t = df["t"].to_numpy(float)
        try:
            epoch = np.array([_iso_epoch(s) for s in df["time_utc"].astype(str)])
        except Exception as e:
            problems.append(f"{rel}: unparseable time_utc ({e})")
            continue
        err = np.abs(epoch - (start + t))
        max_err = max(max_err, float(err.max()) if err.size else 0.0)
        nrows += len(df)
        if (err > 1e-3 + 1e-9).any():
            problems.append(f"{rel}: {int((err > 1e-3 + 1e-9).sum())} rows where time_utc != start+t (max {1000 * err.max():.1f} ms)")
        win = (t >= -1e-9) & (t <= sc.cfg.duration_s + 1e-9)
        if (~win).any():
            problems.append(f"{rel}: {int((~win).sum())} rows outside the scenario window")
        group = df["sensor_id"] if "sensor_id" in df.columns else (
            df["object_id"] if "object_id" in df.columns else None)
        keys = group.fillna("?").astype(str) if group is not None else pd.Series("file", index=df.index)
        for k, g in pd.Series(t).groupby(keys.to_numpy()):
            if (np.diff(g.to_numpy()) < 0).any():
                problems.append(f"{rel}: [{k}] timestamps not monotonic")
    n = len(problems)
    return _result("clock", "Clock sync", "PASS" if n == 0 else "FAIL", n,
                   "0 problems; abs(time_utc − (start+t)) ≤ 1 ms",
                   f"{nrows} rows, max |time_utc − (start+t)| = {1000 * max_err:.3f} ms"
                   if n == 0 else "; ".join(problems[:5]) + (f" (+{n - 5} more)" if n > 5 else ""))


def check_bearing(sc):
    """Measured bearing vs geometric bearing from site.json + truth; median = site bias."""
    rows = []
    for sid in sc.sensors():
        r = sc.recs(sid)
        if r is None or r["site"] is None or "bearing_deg" not in r["df"].columns:
            continue
        meas = r["df"]["bearing_deg"].to_numpy(float)
        std = r["df"]["bearing_std_deg"].to_numpy(float) if "bearing_std_deg" in r["df"] else np.full(len(meas), np.nan)
        ok = r["ok"] & np.isfinite(meas)
        if not ok.any():
            continue
        resid = _wrap180(meas - r["brg"])
        bias = float(np.median(resid[ok]))
        err = _wrap180(resid - bias)
        use = ok & r["los"] & np.isfinite(std) & (std > 0)
        share = float(np.mean(np.abs(err[use]) <= 2 * std[use])) if use.any() else None
        rows.append((sid, bias, share, int(ok.sum()), int(use.sum())))
    if not rows:
        return _result("bearing_geometry", "Bearing geometry", "SKIP", None, "≥ 0.85",
                       "no sensor with bearings + site.json")
    worst = min(s for _, _, s, _, _ in rows if s is not None)
    detail = "; ".join(
        f"{sid}: bias {bias:+.2f}°, within 2σ {'n/a' if s is None else f'{s:.3f}'} (n={n}, n_los={nl})"
        for sid, bias, s, n, nl in rows)
    return _result("bearing_geometry", "Bearing geometry", "PASS" if worst >= 0.85 else "FAIL",
                   round(worst, 4), "≥ 0.85 of LOS within 2σ", detail)


def check_shadow(sc):
    """Excess loss over free space (catalog EIRP, real geometry): NLOS must exceed LOS by ≥ 10 dB."""
    rows = []
    for sid in sc.sensors():
        r = sc.recs(sid)
        if r is None or r["site"] is None or "power_dbm" not in r["df"].columns:
            continue
        f = r["df"]["freq_mhz"].to_numpy(float) if "freq_mhz" in r["df"] else np.full(len(r["df"]), np.nan)
        valid = r["ok"] & np.isfinite(r["eirp"]) & np.isfinite(f) & (r["rng"] > 10)
        if (valid & r["los"]).sum() < MIN_N or (valid & ~r["los"]).sum() < MIN_N:
            continue  # underpowered: a median of a handful of records proves nothing either way
        excess = r["eirp"] - itu.fspl_db(r["rng"] / 1000, f / 1000) - r["df"]["power_dbm"].to_numpy(float)
        med_los = float(np.median(excess[valid & r["los"]]))
        med_nlos = float(np.median(excess[valid & ~r["los"]]))
        rows.append((sid, med_los, med_nlos, med_nlos - med_los,
                     int((valid & r["los"]).sum()), int((valid & ~r["los"]).sum())))
    if not rows:
        return _result("terrain_shadow", "Terrain shadow", "SKIP", None, "≥ 10 dB",
                       f"no sensor with ≥ {MIN_N} LOS and ≥ {MIN_N} NLOS detections with power + geometry")
    worst = min(d for *_, d, _, _ in rows)
    detail = "; ".join(f"{sid}: excess LOS {a:.1f} dB (n={n1}) vs NLOS {b:.1f} dB (n={n2}), Δ={d:.1f} dB"
                       for sid, a, b, d, n1, n2 in rows)
    return _result("terrain_shadow", "Terrain shadow", "PASS" if worst >= 10.0 else "FAIL",
                   round(worst, 2), "NLOS − LOS median excess ≥ 10 dB", detail)


def check_occlusion(sc):
    """Detection rate inside ≥30 s DEM-NLOS intervals must be < 0.5× the rate outside."""
    drones = [o for o, ty in sc.types.items()
              if CATALOG.get(ty, {}).get("kind") == "drone" and sc.sides.get(o) == "hostile"]
    pairs = []
    for sid in sc.sensors():
        r = sc.recs(sid)
        if r is None or r["site"] is None or "power_dbm" not in r["df"]:
            continue
        die = _death(sc, sid)
        for o in drones:
            tr = sc.tracks[sc.tracks["object_id"] == o].sort_values("t")
            if sc.window:
                tr = tr[tr["t"].between(*sc.window)]
            if tr.empty:
                continue
            tt = tr["t"].to_numpy(float)
            tgt = np.stack([tr["x"], tr["y"], tr["alt_msl_m"]], -1)
            losm = sc.world.los(np.broadcast_to(r["site"], tgt.shape), tgt)
            idx = np.flatnonzero(~losm)
            ivals = []
            if idx.size:
                for run in np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1):
                    a, b = tt[run[0]], tt[run[-1]]
                    if b - a >= 30.0:
                        ivals.append((max(a, tt[0]), min(b, min(tt[-1], die))))
            ivals = [(a, b) for a, b in ivals if b > a]
            t0, t1 = max(tt[0], 0.0), min(tt[-1], die)
            dt_in = sum(b - a for a, b in ivals)
            dt_out = (t1 - t0) - dt_in
            if dt_in <= 0 or dt_out <= 0:
                continue
            det_t = r["df"]["t"].to_numpy(float)
            is_obj = (r["df"]["object_id"].fillna("").astype(str) == o).to_numpy()
            in_win = (det_t >= t0) & (det_t <= t1)
            n_in = int(sum((is_obj & (det_t >= a) & (det_t <= b)).sum() for a, b in ivals))
            n_out = int((is_obj & in_win).sum()) - n_in
            rate_in, rate_out = n_in / dt_in, n_out / dt_out
            if rate_out > 0:
                ratio = rate_in / rate_out
            else:
                ratio = float("inf") if n_in else None
            pairs.append((sid, o, len(ivals), dt_in, n_in, n_out, ratio))
    if not pairs:
        return _result("occlusion_gaps", "Occlusion gaps", "SKIP", None, "< 0.5",
                       "no sensor/drone pair with NLOS intervals ≥ 30 s")
    ratios = [p[6] for p in pairs if p[6] is not None]
    worst = max(ratios) if ratios else None
    detail = "; ".join(f"{s}/{o}: {ni} interval(s) {dt:.0f}s, {a} det in vs {b} out, ratio "
                       + ("inf" if ratio == float("inf") else "n/a" if ratio is None else f"{ratio:.3f}")
                       for s, o, ni, dt, a, b, ratio in pairs)
    if worst is None:
        return _result("occlusion_gaps", "Occlusion gaps", "SKIP", None, "< 0.5",
                       "only pairs with no detections at all; " + detail)
    return _result("occlusion_gaps", "Occlusion gaps", "PASS" if worst < 0.5 else "FAIL",
                   None if worst == float("inf") else round(worst, 4), "rate_in / rate_out < 0.5",
                   detail)


def check_fixes(sc):
    """Fix error vs truth should scatter around the reported cep50: ~50% of fixes inside it."""
    fp, kp = sc.root / "fused" / "fixes.csv", sc.root / "answer_key" / "fused.csv"
    if not fp.exists() or not kp.exists():
        return _result("fix_calibration", "Fix calibration", "SKIP", None, "share in [0.35, 0.65]",
                       "no fused/fixes.csv + answer_key/fused.csv")
    fx, key = pd.read_csv(fp), pd.read_csv(kp)
    if sc.window and "t" in fx.columns:
        fx = fx[fx["t"].between(*sc.window)]
    need_fx = {"fix_id", "t", "lat", "lon", "cep50_m"} - set(fx.columns)
    need_k = {"fix_id", "object_id"} - set(key.columns)
    if need_fx or need_k:
        return _result("fix_calibration", "Fix calibration", "SKIP", None, "share in [0.35, 0.65]",
                       f"missing columns {sorted(need_fx | need_k)}")
    m = fx.merge(key[["fix_id", "object_id"]], on="fix_id")
    errs, ceps = [], []
    for o, g in m.groupby(m["object_id"].fillna("").astype(str)):
        if not o or o not in set(sc.tracks["object_id"]):
            continue
        pos = sc.state(o, g["t"].to_numpy(float))
        gx, gy = sc.world.to_xy(g["lat"].to_numpy(float), g["lon"].to_numpy(float))
        good = np.isfinite(pos).all(1)
        errs.extend(np.hypot(gx[good] - pos[good, 0], gy[good] - pos[good, 1]))
        ceps.extend(g["cep50_m"].to_numpy(float)[good])
    if not errs:
        return _result("fix_calibration", "Fix calibration", "SKIP", None, "share in [0.35, 0.65]",
                       "no fixes with an attributable object")
    errs, ceps = np.array(errs), np.array(ceps)
    share = float(np.mean(errs < ceps))
    return _result("fix_calibration", "Fix calibration", "PASS" if 0.35 <= share <= 0.65 else "FAIL",
                   round(share, 4), "share(error < cep50_m) in [0.35, 0.65]",
                   f"n={len(errs)}, median error {np.median(errs):.0f} m, median cep50 {np.median(ceps):.0f} m")


def check_range_law(sc):
    """In LOS, loss grows with distance like physics allows: fitted path-loss exponent in [1.5, 4.5]
    (free space = 2), from received power relative to the transmitter's EIRP vs log10 range."""
    rows = []
    for sid in sc.sensors():
        r = sc.recs(sid)
        if r is None or r["site"] is None or "power_dbm" not in r["df"].columns:
            continue
        use = r["ok"] & r["los"] & np.isfinite(r["eirp"]) & (r["rng"] > 10)
        if use.sum() < MIN_N:
            continue
        rel = (r["df"]["power_dbm"].to_numpy(float) - r["eirp"])[use]  # emitters differ in power
        lg = np.log10(r["rng"][use])
        if np.ptp(lg) < MIN_LOG_SPAN:
            continue  # too little range spread for a distance law to show above fading
        slope = float(np.polyfit(lg, rel, 1)[0])  # dB per decade of range
        rows.append((sid, -slope / 10.0, int(use.sum())))
    if not rows:
        return _result("range_law", "Range law", "SKIP", None, "path-loss exponent in [1.5, 4.5]",
                       f"no sensor with >= {MIN_N} LOS records spanning >= {MIN_LOG_SPAN} decades of range")
    bad = [n for _, n, _ in rows if not 1.5 <= n <= 4.5]
    worst = max(rows, key=lambda x: abs(x[1] - 2.0))[1]
    detail = "; ".join(f"{sid}: exponent {n:.2f} (n={k})" for sid, n, k in rows)
    return _result("range_law", "Range law", "FAIL" if bad else "PASS", round(worst, 3),
                   "path-loss exponent in [1.5, 4.5] (free space 2)", detail)


def check_acoustic(sc):
    """answer_key delay_s must equal recomputed distance(emission)/c within 2%; arrivals after emission."""
    mics = [s.id for s in sc.cfg.sensors if s.type == "microphone"]
    if not mics:
        return _result("acoustic_delay", "Acoustic delay", "SKIP", None, "≤ 2%",
                       "no microphone in scenario")
    c_sound = 331.3 + 0.606 * sc.cfg.weather.temp_c  # m/s at the scenario's air temperature; wind is not
    worst, bad_cause = 0.0, 0                         # modelled here, so the 2% tolerance has to cover it
    for sid in mics:
        r = sc.recs(sid)
        kp = sc.root / "answer_key" / f"{sid}.csv"
        if r is None or not kp.exists():
            return _result("acoustic_delay", "Acoustic delay", "SKIP", None, "≤ 2%",
                           f"{sid}: no detections or answer key to check")
        key = pd.read_csv(kp)
        if "delay_s" not in key.columns:
            return _result("acoustic_delay", "Acoustic delay", "SKIP", None, "≤ 2%",
                           f"{sid}: answer key has no delay_s to check")
        df = r["df"].merge(key[["record_id", "delay_s"]], on="record_id", how="inner")
        site = r["site"]
        t = df["t"].to_numpy(float)
        obj = df["object_id"].fillna("").astype(str).to_numpy()
        delay_key = df["delay_s"].to_numpy(float)
        for o in pd.unique(obj):
            if not o:
                continue
            sel = np.flatnonzero(obj == o)
            pos0 = sc.state(o, t[sel])
            r0 = np.linalg.norm(pos0 - site, axis=1)
            tau = t[sel] - r0 / c_sound  # sound leaves the source before it arrives
            pos1 = sc.state(o, tau)
            delay = np.linalg.norm(pos1 - site, axis=1) / c_sound
            good = np.isfinite(delay) & (delay > 0) & np.isfinite(delay_key[sel])
            rel = np.abs(delay_key[sel][good] - delay[good]) / delay[good]
            if rel.size:
                worst = max(worst, float(rel.max()))
            span = sc.span(o)
            if span:
                emit = t[sel] - delay_key[sel]
                bad_cause += int((~np.isfinite(delay_key[sel]) | (delay_key[sel] <= 0)
                                  | (emit < span[0] - 1) | (emit > span[1] + 1)).sum())
    ok = worst <= 0.02 and bad_cause == 0
    return _result("acoustic_delay", "Acoustic delay", "PASS" if ok else "FAIL",
                   round(worst, 4), "max |Δdelay|/delay ≤ 2%, no arrival before emission",
                   f"max relative delay error {100 * worst:.2f}%, {bad_cause} causality violations")


def check_spoof(sc):
    """Reported GNSS vs truth: small outside spoof windows, large inside (lying sensors visible)."""
    spoofs = {o.id: o.gnss_spoof for o in sc.cfg.objects if o.gnss_spoof}
    rids = [s.id for s in sc.cfg.sensors if s.type in ("remote_id", "telemetry")]
    if not rids:
        return _result("spoof_visible", "Spoof visibility", "SKIP", None, "large error only inside spoof windows",
                       "no remote_id/telemetry in scenario")
    if not spoofs:
        return _result("spoof_visible", "Spoof visibility", "SKIP", None, "large error only inside spoof windows",
                       "no GNSS spoofing in scenario")
    per = {}
    for sid in rids:
        r = sc.recs(sid)
        if r is None:
            continue
        df = r["df"]
        cols = ("gnss_lat", "gnss_lon") if {"gnss_lat", "gnss_lon"} <= set(df.columns) else \
            (("lat", "lon") if {"lat", "lon"} <= set(df.columns) else None)
        if cols is None:
            continue
        t = df["t"].to_numpy(float)
        obj = df["object_id"].fillna("").astype(str).to_numpy()
        px, py = sc.world.to_xy(df[cols[0]].to_numpy(float), df[cols[1]].to_numpy(float))
        for o in pd.unique(obj):
            if o not in spoofs:
                continue  # honest broadcasters have no window to compare against
            sel = obj == o
            pos = sc.state(o, t[sel])
            good = np.isfinite(pos).all(1)
            err = np.hypot(px[sel][good] - pos[good, 0], py[sel][good] - pos[good, 1])
            ins = (t[sel][good] >= spoofs[o].start_s) & (t[sel][good] <= spoofs[o].end_s) if o in spoofs \
                else np.zeros(err.size, bool)
            per.setdefault(o, [[], []])
            per[o][0].extend(err[~ins])
            per[o][1].extend(err[ins])
    if not per:
        return _result("spoof_visible", "Spoof visibility", "SKIP", None, "large error only inside spoof windows",
                       "no reported positions found in remote_id/telemetry files")
    detail, ok = [], True
    for o, (out_err, in_err) in sorted(per.items()):
        if not in_err:
            detail.append(f"{o}: no records inside its spoof window")
            ok = False
            continue
        mo, mi = float(np.median(out_err)) if out_err else float("nan"), float(np.median(in_err))
        detail.append(f"{o}: median error {mo:.0f} m outside vs {mi:.0f} m inside spoof window")
        ok = ok and mi >= 50.0 and (np.isnan(mo) or mi >= 3 * mo)
    return _result("spoof_visible", "Spoof visibility", "PASS" if ok else "FAIL",
                   None, "error grows ≥3× and ≥50 m inside spoof windows (informational)",
                   "; ".join(detail))


def check_camera(sc):
    """Every camera frame must have a cue (RF fix or radar track) within 5 s."""
    cams = [s.id for s in sc.cfg.sensors if s.type == "camera"]
    if not cams:
        return _result("cross_sensor_time", "Cross-sensor time", "SKIP", None, "every frame within 5 s of a fix",
                       "no camera in scenario")
    fp = sc.root / "fused" / "fixes.csv"
    if not fp.exists():
        return _result("cross_sensor_time", "Cross-sensor time", "SKIP", None, "every frame within 5 s of a fix",
                       "no fused/fixes.csv to cue from")
    fixes = pd.read_csv(fp)
    if "t" not in fixes.columns or fixes.empty:
        return _result("cross_sensor_time", "Cross-sensor time", "SKIP", None, "every frame within 5 s of a fix",
                       "no fixes to cue from")
    cue_t = [fixes["t"].to_numpy(float)]  # a frame may be cued by an RF fix or a confirmed radar track
    for rid in [s.id for s in sc.cfg.sensors if s.type == "radar"]:
        tp = sc.root / "sensors" / rid / "tracks.csv"
        if tp.exists():
            tr = pd.read_csv(tp)
            cue_t.append(tr.loc[tr["state"] == "CONFIRMED", "t"].to_numpy(float))
    ft = np.sort(np.concatenate(cue_t))
    total, uncued = 0, 0
    for sid in cams:
        folder = sc.root / "sensors" / sid
        times = []
        det = folder / "detections.csv"
        if det.exists():
            d = pd.read_csv(det)
            if "t" in d.columns:
                times.append(d["t"].to_numpy(float))
        media = folder / "media.csv"
        if media.exists():
            md = pd.read_csv(media)
            if {"t", "kind"} <= set(md.columns):
                times.append(md.loc[md["kind"] == "image", "t"].to_numpy(float))
        if not times:
            continue
        tt = np.concatenate(times)
        total += tt.size
        idx = np.searchsorted(ft, tt)  # nearest fix without an n×m broadcast
        left = np.where(idx > 0, tt - ft[np.clip(idx - 1, 0, ft.size - 1)], np.inf)
        right = np.where(idx < ft.size, ft[np.clip(idx, 0, ft.size - 1)] - tt, np.inf)
        uncued += int((np.minimum(left, right) > 5.0).sum())
    if total == 0:
        return _result("cross_sensor_time", "Cross-sensor time", "SKIP", None, "every frame within 5 s of a fix",
                       "camera present but no frames found")
    share = 1.0 - uncued / total
    return _result("cross_sensor_time", "Cross-sensor time", "PASS" if uncued == 0 else "FAIL",
                   round(share, 4), "every frame within 5 s of a fix",
                   f"{total} frames, {uncued} without a fix within 5 s")


def _death(sc, sid):
    """The scenario's destroyed_by contract: sensor dark after the destroying object's last tick."""
    for s in sc.cfg.sensors:
        if s.id == sid and s.destroyed_by:
            return sc.span(s.destroyed_by)[1] if sc.span(s.destroyed_by) else float("inf")
    return float("inf")


# --------------------------------------------------------------------------- driver

def audit_dir(root, window=None):
    sc = Scene.load(root, window)
    checks = [check_provenance(sc), check_clock(sc), check_bearing(sc), check_shadow(sc),
              check_occlusion(sc), check_fixes(sc), check_range_law(sc), check_acoustic(sc),
              check_spoof(sc), check_camera(sc)]
    summary = {s: sum(c["status"] == s for c in checks) for s in ("PASS", "FAIL", "SKIP")}
    return {"scenario": sc.cfg.name,
            "summary": {"pass": summary["PASS"], "fail": summary["FAIL"], "skip": summary["SKIP"]},
            "checks": checks}


def _fmt(v):
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.4g}"
    return str(v)


def _cell(v):
    return str(v).replace("|", "\\|")


def _md(audit, baseline, base_note):
    out = [f"# Audit — {audit['scenario']}", "",
           "Independent checks: geometry from `truth/tracks.csv` + `sensors/*/site.json` and the real DEM",
           "(`World.los`), causality and statistics. The answer key's derived columns are never trusted.",
           "",
           "| id | check | status | value | threshold | detail |",
           "|---|---|---|---|---|---|"]
    for c in audit["checks"]:
        out.append(f"| {c['id']} | {c['name']} | {c['status']} | {_fmt(c['value'])} | {_cell(c['threshold'])} | {_cell(c['detail'])} |")
    s = audit["summary"]
    out += ["", f"**{s['pass']} pass, {s['fail']} fail, {s['skip']} skip.**", ""]
    if baseline is not None:
        b = {c["id"]: c for c in baseline["checks"]}
        out += ["## OASIS vs one-shot LLM", "",
                f"One-shot baseline: `{base_note}` (same window, same layout, one LLM call).",
                "",
                "| check | OASIS | one-shot LLM |",
                "|---|---|---|"]
        for c in audit["checks"]:
            o = b.get(c["id"])
            mine = f"{c['status']} ({_fmt(c['value'])})"
            theirs = f"{o['status']} ({_fmt(o['value'])})" if o else "—"
            out.append(f"| {c['name']} | {mine} | {theirs} |")
        bs, ss = baseline["summary"], audit["summary"]
        out += ["", f"OASIS: {ss['pass']} pass / {ss['fail']} fail / {ss['skip']} skip. "
                f"One-shot LLM: {bs['pass']} pass / {bs['fail']} fail / {bs['skip']} skip.", ""]
    elif base_note:
        out += [f"_Baseline not run: {base_note}_", ""]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="mirrorworld audit",
                                 description="Audit a run directory against physics, not against itself.")
    ap.add_argument("out", help="run directory, e.g. out/ros-valley")
    ap.add_argument("--baseline", default=None,
                    help="a one-shot-LLM run directory to compare against")
    ap.add_argument("--window", nargs=2, type=float, metavar=("T0", "T1"), default=None,
                    help="audit only t in [T0, T1] seconds (applied identically to the baseline)")
    args = ap.parse_args(argv)
    window = tuple(args.window) if args.window else None

    audit = audit_dir(args.out, window)
    baseline, note = None, None
    if args.baseline:
        b = Path(args.baseline)
        if (b / "scenario.yaml").exists():
            baseline = audit_dir(b, window)
            note = args.baseline
        else:
            note = f"baseline dir {b} not found — generate it with `python baselines/oneshot/make.py` (needs OPENAI_API_KEY)"

    out = Path(args.out)
    (out / "audit.json").write_text(json.dumps(
        {"scenario": audit["scenario"], "summary": audit["summary"], "checks": audit["checks"],
         "baseline": baseline}, indent=2))
    (out / "audit.md").write_text(_md(audit, baseline, note))

    for c in audit["checks"]:
        print(f"  {c['id']:<18} {c['status']:<4} {_fmt(c['value']):>8}  {c['detail'][:90]}")
    s = audit["summary"]
    print(f"audit {audit['scenario']}: {s['pass']} pass, {s['fail']} fail, {s['skip']} skip "
          f"-> {out}/audit.json, {out}/audit.md")
    if baseline is not None:
        bs = baseline["summary"]
        print(f"baseline: {bs['pass']} pass, {bs['fail']} fail, {bs['skip']} skip (see audit.md)")
    sys.exit(1 if s["fail"] else 0)
