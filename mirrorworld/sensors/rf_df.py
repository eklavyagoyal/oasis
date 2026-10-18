"""RF direction finding: what DF receivers on masts would have logged, and the fixes they give.

Per link, receiver and report tick:
  real DEM profile (<= 30 m spacing) -> free space + ITU-R P.526-16 delta-Bullington diffraction
  + location-correlated log-normal shadowing + Rician fading (K by band, ~Rayleigh when blocked)
  -> received power; kTB + NF + co-channel interference (Wi-Fi, jammers, through the same terrain)
  -> SINR; energy-detector threshold; bearing error = site floor + 1/sqrt(SNR) term, wider and
  sometimes wild when terrain blocks the path, plus a fixed per-site calibration bias.
Uplinks are transmitted by the operator object, so DF on them finds the pilot, not the drone.
Fixes cross bearings from the detections alone (association by tick + decoded emitter id /
class / frequency) and are written as CoT like the brief's example.
"""
import hashlib
import json
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

from .. import itu
from ..catalog import CATALOG

AE_KM = itu.k_factor_from_dn(45.0) * itu.R_EARTH_KM  # median effective earth radius (k ~ 1.40)
LABEL = {"hostile": "target", "unknown": "target", "friendly": "friendly", "neutral": "clutter"}
_LINKS = [(p, L) for p in CATALOG.values() for L in p.get("links", [])]
CLASSES = sorted({L["sig_class"] for _, L in _LINKS})
HOPPING = {L["sig_class"] for _, L in _LINKS if L["hop"]}
CONTROL = {L["sig_class"] for _, L in _LINKS if L["tx"] == "operator"}  # uplinks: the emitter is the pilot
FIXED = {L["sig_class"] for p, L in _LINKS if p["kind"] not in ("drone", "bird")}  # Wi-Fi, jammers
ROTARY = {L["sig_class"] for p, L in _LINKS if p.get("shape") == "quad" and L["tx"] == "self"}
DECODABLE = {"OcuSync video", "OcuSync RC"}  # DJI DroneID-style serial decode needs a strong signal
DEFAULTS = dict(report_hz=1.0, nf_db=6.0, gain_dbi=3.0, manmade_db=0.0, thr_db=-3.0, bearing_floor_deg=2.5,
                dwell_samples=100, looks_per_report=10, fa_per_min=0.5, decode_snr_db=15.0, lob_m=8000)
SHADOW_CORR_M, SHADOW_LOS_DB, SHADOW_NLOS_DB = 60.0, 3.0, 6.0
K_LOS_DB = ([1000, 2400, 5800], [12, 20, 27])  # Rician K vs MHz, air-to-ground measurements
K_NLOS_DB, NLOS_EXTRA_DEG, WILD_SPREAD_DEG = 1.5, 3.0, 25.0


def path_loss_db(world, tx, rx, f_mhz):
    """Free space + terrain diffraction (dB). tx (N, 3), rx (3,) or (N, 3): local x, y, z in m MSL."""
    return _path(world, tx, rx, f_mhz)[0]


def _path(world, tx, rx, f_mhz):
    """Returns total_db, diffraction_db, los. One frequency per call: hopping across a band moves loss < 0.3 dB."""
    tx = np.atleast_2d(np.asarray(tx, float))
    rx = np.broadcast_to(np.asarray(rx, float), tx.shape)
    f_ghz = float(f_mhz) / 1000
    D = np.maximum(np.hypot(rx[:, 0] - tx[:, 0], rx[:, 1] - tx[:, 1]), 2.0)
    m = max(int(np.ceil(D.max() / 30.0)) + 1, 16)  # coarser than the 30 m DEM posting skips ridge crests
    h = world.profile(tx[:, 0], tx[:, 1], rx[:, 0], rx[:, 1], m)
    d = (D / 1000)[:, None] * np.linspace(0, 1, m)
    agl_t, agl_r = np.maximum(tx[:, 2] - h[:, 0], 0.5), np.maximum(rx[:, 2] - h[:, -1], 0.5)
    ld, _, los = itu.delta_bullington(d, h, agl_t, agl_r, f_ghz, AE_KM)
    return itu.fspl_db(np.hypot(D, rx[:, 2] - tx[:, 2]) / 1000, f_ghz) + ld, ld, los


def _sigma_deg(snr_db, p):
    """DF bearing spread: site floor (multipath, calibration residue) + statistical term ~ 1/sqrt(SNR)."""
    stat = np.degrees(1 / (np.pi * np.sqrt(10 ** (np.asarray(snr_db) / 10) * p["dwell_samples"])))
    return np.hypot(p["bearing_floor_deg"], stat)


def _fading_db(rng, k_db, looks=4):
    """Rician power fade averaged over a few looks (the detector integrates over its dwell)."""
    k = 10 ** (np.asarray(k_db, float) / 10)[:, None]
    n = rng.normal(size=(k.shape[0], looks)) + 1j * rng.normal(size=(k.shape[0], looks))
    return 10 * np.log10((np.abs(np.sqrt(k / (k + 1)) + np.sqrt(0.5 / (k + 1)) * n) ** 2).mean(1))


def _links(ctx):
    """Every radio link in the scenario: who transmits it and where it sits in frequency."""
    rng = ctx.rng("rf:channels")
    operator_of = {o.controls: o.id for o in ctx.objects.values() if o.controls}
    links = []
    for o in ctx.objects.values():
        for L in CATALOG[o.type].get("links", []):
            tx = o.id if L["tx"] == "self" else operator_of.get(o.id)
            if tx is None:
                continue  # an uplink whose operator isn't in the scenario
            lo, hi = L["band_mhz"]
            f0 = rng.choice(L["channels"]) if "channels" in L else rng.uniform(lo + L["bw_mhz"] / 2, hi - L["bw_mhz"] / 2)
            sig = hashlib.sha1(f"{ctx.cfg.seed}:{o.id}:{L['name']}".encode()).hexdigest()[:8]
            links.append({**L, "id": f"{o.id}:{L['name']}", "owner": o.id, "tx_obj": tx, "f0": float(f0), "sig": sig})
    return links


def _receive(sensor, ctx, links):
    """One receiver: detections (what it logged) and answer-key rows (why it logged them)."""
    p = {**DEFAULTS, **sensor.params}
    rng = ctx.rng(f"rf:{sensor.id}")
    bias = p.get("calib_bias_deg", rng.normal(0, 1.0))
    rx = ctx.sensor_xyz(sensor)
    t = np.arange(0, ctx.cfg.duration_s, 1 / p["report_hz"])
    alive = ctx.alive(sensor, t)
    sk, sph = rng.normal(0, 1 / SHADOW_CORR_M, (64, 2)), rng.uniform(0, 2 * np.pi, 64)  # shadowing field features

    per = []
    for L in links:
        st = ctx.state(L["tx_obj"], t)
        tx = np.stack([st["x"], st["y"], st["z"]], -1)
        active = alive & np.isfinite(tx[:, 0])
        if L["tx_obj"] != L["owner"]:  # an uplink is only on air while its drone flies
            active &= np.isfinite(ctx.state(L["owner"], t)["x"])
        tx = np.where(active[:, None], tx, rx + [10.0, 0, 0])  # parked by the mast while inactive; masked below
        lo, hi = L["band_mhz"][0] + L["bw_mhz"] / 2, L["band_mhz"][1] - L["bw_mhz"] / 2
        f = rng.uniform(lo, hi, t.size) if L["hop"] else np.full(t.size, L["f0"])
        loss, diff, los = np.full(t.size, np.inf), np.zeros(t.size), np.zeros(t.size, bool)
        if active.any():  # only propagate while on air: a day-long scenario is mostly silence
            loss[active], diff[active], los[active] = _path(ctx.world, tx[active], rx, L["f0"])
        # same place -> same shadow: a unit-variance Gaussian field (random Fourier features), ~60 m correlation
        shadow = np.sqrt(2 / 64) * np.cos(tx[:, :2] @ sk.T + sph).sum(1) * np.where(los, SHADOW_LOS_DB, SHADOW_NLOS_DB)
        fade = _fading_db(rng, np.where(los, np.interp(L["f0"], *K_LOS_DB), K_NLOS_DB))
        prx = L["eirp_dbm"] + p["gain_dbi"] - loss - shadow + fade
        # a scanning receiver looks at the band `looks_per_report` times per report: a burst must overlap one look
        on = active & (rng.random(t.size) < 1 - (1 - L["duty"]) ** p["looks_per_report"])
        per.append(dict(L=L, f=f, prx=prx, on=on, active=active, tx=tx, loss=loss, diff=diff, los=los, shadow=shadow, fade=fade))

    det, key = [], []
    for a in per:
        L = a["L"]
        lo, hi = a["f"] - L["bw_mhz"] / 2, a["f"] + L["bw_mhz"] / 2
        i_mw = np.zeros(t.size)
        for b in per:
            if b["L"]["owner"] == L["owner"]:
                continue  # a system's own up/downlink share time (TDD), not interference
            bw = b["L"]["bw_mhz"]
            overlap = np.clip(np.minimum(hi, b["f"] + bw / 2) - np.maximum(lo, b["f"] - bw / 2), 0, None) / bw
            i_mw += np.where(b["active"], 10 ** (b["prx"] / 10) * overlap * b["L"]["duty"], 0.0)  # airtime-weighted
        noise_dbm = -174 + 10 * np.log10(L["bw_mhz"] * 1e6) + p["nf_db"] + p["manmade_db"]
        sinr = a["prx"] - 10 * np.log10(10 ** (noise_dbm / 10) + i_mw)
        hit = a["on"] & (rng.random(t.size) < 1 / (1 + np.exp(-(sinr - p["thr_db"]))))
        i = np.flatnonzero(hit)
        if not i.size:
            continue
        snr = sinr[i] + rng.normal(0, 1.0, i.size)
        true_az = np.degrees(np.arctan2(a["tx"][i, 0] - rx[0], a["tx"][i, 1] - rx[1])) % 360
        nlos = ~a["los"][i]
        sigma = _sigma_deg(sinr[i], p)
        sigma = np.where(nlos, np.hypot(sigma, NLOS_EXTRA_DEG), sigma)
        p_wild = np.where(nlos, 0.05 + 0.25 * (1 - np.exp(-a["diff"][i] / 20)), 0.01)  # reflection beats the diffracted ray
        wild = rng.random(i.size) < p_wild
        err = np.where(wild, rng.normal(0, WILD_SPREAD_DEG, i.size), rng.normal(0, 1, i.size) * sigma)
        p_ok = np.clip(0.55 + 0.025 * snr, 0.55, 0.97)
        ok = rng.random(i.size) < p_ok
        decoded = ok & (sinr[i] > p["decode_snr_db"]) & (L["sig_class"] in DECODABLE)
        det.append(pd.DataFrame({
            "t": t[i], "sensor_id": sensor.id,
            "freq_mhz": (a["f"][i] + rng.normal(0, 0.02 * L["bw_mhz"], i.size)).round(2),
            "bw_mhz": (L["bw_mhz"] * (1 + rng.normal(0, 0.05, i.size))).round(2),
            "power_dbm": (a["prx"][i] + rng.normal(0, 1.0, i.size)).round(1),
            "snr_db": snr.round(1),
            "bearing_deg": ((true_az + bias + err) % 360).round(1),
            "bearing_std_deg": _sigma_deg(snr, p).round(1),  # the DF unit can't know the path is blocked
            "sig_class": np.where(ok, L["sig_class"], rng.choice(CLASSES, i.size)),
            "class_conf": np.clip(p_ok + rng.normal(0, 0.05, i.size), 0.05, 0.99).round(2),
            "emitter_id": np.where(decoded, L["sig"], ""),
        }))
        key.append(pd.DataFrame({
            "object_id": L["tx_obj"], "link": L["id"], "label": LABEL[ctx.objects[L["tx_obj"]].side],
            "true_bearing_deg": true_az.round(2), "true_range_m": np.hypot(*(a["tx"][i, :2] - rx[:2]).T).round(1),
            "los": a["los"][i], "path_loss_db": a["loss"][i].round(1), "diffraction_db": a["diff"][i].round(1),
            "shadow_db": a["shadow"][i].round(1), "fading_db": a["fade"][i].round(1),
            "sinr_db": sinr[i].round(1), "wild_bearing": wild,
        }))

    t_fa = np.sort(rng.uniform(0, ctx.cfg.duration_s, rng.poisson(p["fa_per_min"] * ctx.cfg.duration_s / 60)))
    t_fa = t_fa[ctx.alive(sensor, t_fa)]  # detector false alarms: no object at all
    n, snr_fa = t_fa.size, p["thr_db"] + rng.exponential(1.5, t_fa.size)
    det.append(pd.DataFrame({
        "t": t_fa, "sensor_id": sensor.id,
        "freq_mhz": (rng.choice([866.0, 2440.0, 5800.0], n) + rng.normal(0, 15, n)).round(2),
        "bw_mhz": rng.choice([0.5, 1.4, 10.0, 20.0], n), "power_dbm": (-104 + snr_fa).round(1),
        "snr_db": snr_fa.round(1), "bearing_deg": rng.uniform(0, 360, n).round(1),
        "bearing_std_deg": _sigma_deg(snr_fa, p).round(1),
        "sig_class": rng.choice(CLASSES, n), "class_conf": rng.uniform(0.2, 0.6, n).round(2), "emitter_id": "",
    }))
    key.append(pd.DataFrame({"object_id": [""] * n, "link": "", "label": "false_alarm"}))

    det, key = pd.concat(det, ignore_index=True), pd.concat(key, ignore_index=True)
    order = np.argsort(det["t"].to_numpy(), kind="stable")
    det, key = det.iloc[order].reset_index(drop=True), key.iloc[order].reset_index(drop=True)
    ids = [f"{sensor.id}-{k:06d}" for k in range(len(det))]
    det.insert(0, "record_id", ids)
    det.insert(1, "time_utc", ctx.iso(det["t"].to_numpy()))
    key.insert(0, "record_id", ids)
    return det, key


def _ls_fix(s, brg_deg, std_deg):
    """Weighted least-squares crossing of bearing lines. s: (k, 2) sensor x, y. Returns (p, cov) or None."""
    th = np.radians(brg_deg)
    u = np.stack([np.sin(th), np.cos(th)], 1)  # along the bearing
    nrm = np.stack([np.cos(th), -np.sin(th)], 1)  # normal to it
    if len(th) == 2 and abs(np.sin(th[0] - th[1])) < np.sin(np.radians(5)):
        return None  # nearly parallel bearings: no usable crossing
    w = np.ones(len(th))
    for _ in range(2):  # 2nd pass weights each line by 1 / (range * sigma)^2
        A = np.einsum("k,ki,kj->ij", w, nrm, nrm)
        if abs(np.linalg.det(A)) < 1e-12:
            return None
        p = np.linalg.solve(A, np.einsum("k,ki,k->i", w, nrm, (nrm * s).sum(1)))
        r = ((p - s) * u).sum(1)
        if (r <= 0).any():
            return None  # the lines cross behind a receiver
        w = 1 / (r * np.radians(std_deg)) ** 2
    return p, np.linalg.inv(np.einsum("k,ki,kj->ij", w, nrm, nrm))


def _fuse(det, key, ctx, sites, report_hz):
    """Associate detections across receivers without truth, cross their bearings, write fixes + CoT."""
    d = det.assign(tick=np.round(det["t"] * report_hz).astype(int))
    freq_bin = d["sig_class"] + "@" + (d["freq_mhz"] / 5).round().astype(int).astype(str)
    d["key"] = np.where(d["emitter_id"] != "", d["emitter_id"], np.where(d["sig_class"].isin(HOPPING), d["sig_class"], freq_bin))
    obj_of, label_of = dict(zip(key["record_id"], key["object_id"])), dict(zip(key["record_id"], key["label"]))
    half = ctx.cfg.area.size_km * 500
    fixes, answers = [], []
    for _, g in d.groupby(["tick", "key"], sort=True):
        if g["sensor_id"].nunique() < 2 or g["sensor_id"].duplicated().any():
            continue  # one receiver only, or ambiguous (two candidates at one receiver)
        got = _ls_fix(np.array([sites[s][:2] for s in g["sensor_id"]]), g["bearing_deg"].to_numpy(), g["bearing_std_deg"].to_numpy())
        if got is None or np.abs(got[0]).max() > half:
            continue  # no crossing, or it lands outside the mapped area
        (x, y), cov = got
        ev, vec = np.linalg.eigh(cov)
        sig = np.sqrt(np.clip(ev, 0, None))  # minor, major 1-sigma axes
        t = float(g["t"].mean())
        lat, lon = ctx.world.to_ll(x, y)
        fid = f"FIX-{len(fixes):06d}"
        fixes.append(dict(
            fix_id=fid, time_utc=ctx.iso(t), t=t, lat=round(float(lat), 6), lon=round(float(lon), 6),
            hae_m=round(float(ctx.world.height(x, y)), 1),
            ce_m=round(float(np.sqrt((sig ** 2).mean())), 1),  # CoT ce: 1-sigma circular (39% containment)
            cep50_m=round(0.5887 * float(sig.sum()), 1), semi_major_m=round(float(sig[1]), 1),
            semi_minor_m=round(float(sig[0]), 1), orient_deg=round(float(np.degrees(np.arctan2(vec[0, 1], vec[1, 1])) % 180), 1),
            n_sensors=len(g), sig_class=g["sig_class"].iloc[0], freq_mhz=round(float(g["freq_mhz"].mean()), 2),
            record_ids=";".join(g["record_id"])))
        objs = {obj_of[r] for r in g["record_id"]}
        obj = objs.pop() if len(objs) == 1 else "mixed"  # a mis-association is an answer too
        err = np.nan
        if obj not in ("", "mixed"):
            st = ctx.state(obj, np.array([t]))
            err = round(float(np.hypot(st["x"][0] - x, st["y"][0] - y)), 1)
        answers.append(dict(fix_id=fid, object_id=obj, label="mixed" if obj == "mixed" else label_of[g["record_id"].iloc[0]], error_m=err))

    cols = ["fix_id", "time_utc", "t", "lat", "lon", "hae_m", "ce_m", "cep50_m", "semi_major_m", "semi_minor_m",
            "orient_deg", "n_sensors", "sig_class", "freq_mhz", "record_ids"]
    # a false alarm off the tick grid can pull a fix's mean time behind its neighbour: emit in time order
    order = np.argsort([f["t"] for f in fixes], kind="stable")
    fixes, answers = [fixes[i] for i in order], [answers[i] for i in order]
    for n, (f, a) in enumerate(zip(fixes, answers)):
        f["fix_id"] = a["fix_id"] = f"FIX-{n:06d}"
    fixes = pd.DataFrame(fixes, columns=cols)
    out = ctx.out / "fused"
    out.mkdir(parents=True, exist_ok=True)
    fixes.to_csv(out / "fixes.csv", index=False)
    pd.DataFrame(answers, columns=["fix_id", "object_id", "label", "error_m"]).to_csv(ctx.out / "answer_key" / "fused.csv", index=False)
    _write_cot(fixes, det.set_index("record_id"), ctx, out / "fixes.cot.xml")


def _cot_kind(sig_class):
    """CoT type + callsign stem for what the signal says the emitter is (MITRE CoTtypes)."""
    if sig_class in CONTROL:
        return "a-u-G-U-C-V-U", "Drone operator?"  # unknown UAV ground control station
    if sig_class in FIXED:
        return "a-u-G", "Ground emitter"
    return ("a-u-A-M-H-Q" if sig_class in ROTARY else "a-u-A"), "Unknown drone"


def _write_cot(fixes, det, ctx, path):
    root = ET.Element("events")
    for f in fixes.itertuples():
        cot_type, stem = _cot_kind(f.sig_class)
        t0, stale = ctx.iso(f.t), ctx.iso(f.t + 30)
        band = f"{f.freq_mhz / 1000:.1f} GHz" if f.freq_mhz >= 1000 else f"{f.freq_mhz:.0f} MHz"
        ev = ET.SubElement(root, "event", version="2.0", uid=f"mw-{ctx.cfg.name}-{f.fix_id}", type=cot_type,
                           how="m-r", time=t0, start=t0, stale=stale)
        ET.SubElement(ev, "point", lat=f"{f.lat:.6f}", lon=f"{f.lon:.6f}", hae=f"{f.hae_m:.1f}", ce=f"{f.ce_m:.1f}", le="9999999.0")
        detail = ET.SubElement(ev, "detail")
        ET.SubElement(detail, "contact", callsign=f"{stem}, {band}")
        recs = f.record_ids.split(";")
        ET.SubElement(detail, "remarks").text = (f"{f.sig_class} heard by {' and '.join(det.loc[recs, 'sensor_id'])}, "
                                                 f"position from crossed bearings (CEP50 {f.cep50_m:.0f} m)")
        ET.SubElement(detail, "__ellipse", major_m=f"{f.semi_major_m:.1f}", minor_m=f"{f.semi_minor_m:.1f}", angle_deg=f"{f.orient_deg:.1f}")
        for rid in recs:
            r = det.loc[rid]
            ET.SubElement(detail, "link", uid=f"sensor-{r.sensor_id}", type="a-f-G-E-S", relation="p-p")
            ET.SubElement(detail, "link", uid=f"lob-{rid}", type="u-rb-a", relation="c-f")
            ET.SubElement(detail, "__signal", sensor=r.sensor_id, freq_mhz=f"{r.freq_mhz:.1f}", power_dbm=f"{r.power_dbm:.1f}",
                          snr_db=f"{r.snr_db:.1f}", bearing_deg=f"{r.bearing_deg:.1f}", record=rid)
    ET.indent(root)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def _write_lobs(det, sensor, site, ctx, path, lob_m):
    """The receiver's own log as ATAK draws it: a sensor marker plus one line of bearing (u-rb-a) per detection."""
    lat, lon, hae = (f"{site['lat']:.6f}", f"{site['lon']:.6f}", f"{site['alt_msl_m']:.1f}")
    uid, root = f"sensor-{sensor.id}", ET.Element("events")
    t0, t1 = ctx.iso(0.0), ctx.iso(ctx.cfg.duration_s)
    ev = ET.SubElement(root, "event", version="2.0", uid=uid, type="a-f-G-E-S", how="h-e", time=t0, start=t0, stale=t1)
    ET.SubElement(ev, "point", lat=lat, lon=lon, hae=hae, ce="5", le="5")
    ET.SubElement(ET.SubElement(ev, "detail"), "contact", callsign=sensor.id)
    for r in det.itertuples():
        ts = ctx.iso(r.t)
        ev = ET.SubElement(root, "event", version="2.0", uid=f"lob-{r.record_id}", type="u-rb-a", how="m-r",
                           time=ts, start=ts, stale=ctx.iso(r.t + 15))
        ET.SubElement(ev, "point", lat=lat, lon=lon, hae=hae, ce="9999999", le="9999999")
        d = ET.SubElement(ev, "detail")
        for tag, val in [("range", lob_m), ("bearing", f"{r.bearing_deg:.1f}"), ("anchorUID", uid),
                         ("rangeUnits", 1), ("bearingUnits", 0), ("northRef", 0)]:
            ET.SubElement(d, tag, value=str(val))
        ET.SubElement(d, "__signal", sensor=sensor.id, freq_mhz=f"{r.freq_mhz:.1f}", power_dbm=f"{r.power_dbm:.1f}",
                      snr_db=f"{r.snr_db:.1f}", sig_class=r.sig_class, record=r.record_id)
    ET.indent(root)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def run(sensors, ctx):
    links = _links(ctx)
    (ctx.out / "answer_key").mkdir(parents=True, exist_ok=True)
    sites, dets, keys = {}, [], []
    for s in sensors:
        sites[s.id] = xyz = ctx.sensor_xyz(s)
        det, key = _receive(s, ctx, links)
        folder = ctx.out / "sensors" / s.id
        folder.mkdir(parents=True, exist_ok=True)
        det.to_csv(folder / "detections.csv", index=False)
        key.to_csv(ctx.out / "answer_key" / f"{s.id}.csv", index=False)
        lat, lon = ctx.world.to_ll(xyz[0], xyz[1])
        site = {"sensor_id": s.id, "lat": round(float(lat), 6), "lon": round(float(lon), 6),
                "alt_msl_m": round(float(xyz[2]), 1), "mast_m": s.mast_m}
        (folder / "site.json").write_text(json.dumps(site, indent=1))  # a receiver knows where it stands: not truth
        _write_lobs(det, s, site, ctx, folder / "detections.cot.xml", {**DEFAULTS, **s.params}["lob_m"])
        dets.append(det)
        keys.append(key)
    _fuse(pd.concat(dets, ignore_index=True), pd.concat(keys, ignore_index=True), ctx, sites,
          {**DEFAULTS, **sensors[0].params}["report_hz"])
