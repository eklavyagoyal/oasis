"""Wideband SDR recorder: short raw IQ snapshots of the band as SigMF.

One snapshot per chosen moment: every on-air in-band link is synthesised as a burst train at
baseband offset (f - centre), thermal noise is added, and the capture is saved as ci16_le.
Sensor files stay blind: annotations with object ids live only under answer_key/.
Power convention: |x|^2 averaged over samples is the power in mW (no 50-ohm reference).
"""
import csv
import json
import math

import numpy as np
from PIL import Image, ImageDraw

from . import rf_df

DEFAULTS = dict(center_mhz=2440.0, fs_msps=30.72, dur_ms=20.0, nf_db=6.0, gain_dbi=3.0,
                max_snapshots=12, times_s=None)
FS_GEN = 30.72e6  # OFDM generation rate: 15 kHz subcarriers, FFT 2048, CP 144


# ------------------------------------------------------------------ waveform generators (from research/rf_emitters)

def freq_shift(x, f_off, fs, t0=0.0):
    """Mix to f_off; t0 keeps the oscillator phase continuous w.r.t. the capture start."""
    n = np.arange(len(x))
    return x * np.exp(2j * np.pi * f_off * (n / fs + t0))


def fft_resample(x, fs_in, fs_out):
    """Band-limited resample by zero-padding / truncating the spectrum (numpy only)."""
    n_in, n_out = len(x), int(round(len(x) * fs_out / fs_in))
    spec = np.fft.fftshift(np.fft.fft(x))
    if n_out >= n_in:
        pad = n_out - n_in
        spec = np.concatenate([np.zeros(pad // 2, complex), spec, np.zeros(pad - pad // 2, complex)])
    else:
        cut = n_in - n_out
        spec = spec[cut // 2: cut // 2 + n_out]
    return np.fft.ifft(np.fft.ifftshift(spec)) * (n_out / n_in)


def unit_power(x):
    return x / np.sqrt(np.mean(np.abs(x) ** 2))


def ofdm(grid, n_fft, cps):
    """grid: (n_sym, n_used) symbols mapped symmetrically around (excluded) DC."""
    half = grid.shape[1] // 2
    out = []
    for row, cp in zip(grid, cps):
        spec = np.zeros(n_fft, complex)
        spec[1:half + 1] = row[half:]
        spec[-half:] = row[:half]
        sym = np.fft.ifft(spec) * np.sqrt(n_fft)
        out.append(np.concatenate([sym[-cp:], sym]))
    return np.concatenate(out)


def qam(rng, shape, order=4):
    m = int(np.sqrt(order))
    lv = np.arange(m) * 2 - (m - 1)
    s = rng.choice(lv, shape) + 1j * rng.choice(lv, shape)
    return s / np.sqrt(np.mean(np.abs(lv) ** 2) * 2)


def wifi_burst(fs_out, rng, n_data_sym):
    """802.11a/g-like PPDU at 20 MS/s: STF-like, LTF-like, then 16-QAM data with 0.8 us GI."""
    used = np.r_[-26:0, 1:27]

    def sym(vals, cp):
        spec = np.zeros(64, complex)
        spec[used % 64] = vals
        s = np.fft.ifft(spec) * 8
        return np.concatenate([s[-cp:], s])

    stf_vals = np.zeros(52, complex)
    stf_vals[::4] = qam(rng, 13, 4) * 2
    stf = np.tile(sym(stf_vals, 0)[:16], 10)
    ltf_core = sym(rng.choice([-1.0, 1.0], 52) + 0j, 0)
    ltf = np.concatenate([ltf_core[-32:], ltf_core, ltf_core])
    data = np.concatenate([sym(qam(rng, 52, 16), 16) for _ in range(n_data_sym)])
    return fft_resample(np.concatenate([stf, ltf, data]), 20e6, fs_out)


# ------------------------------------------------------------------ burst trains and synthesis

def _bursts(rng, e, dur_s):
    """Burst train for the sig_class: (t0, dur, f_mhz, bw_mhz, kind) within the snapshot."""
    sc, duty = e["sig_class"], e["duty"]
    if sc == "OcuSync video":  # near-continuous TDD frames, on air `duty` of the time
        t0, out = 0.0, []
        while t0 < dur_s:
            out.append((t0, min(5e-3 * duty, dur_s - t0), e["f0"], e["bw_mhz"], "ofdm16"))
            t0 += 5e-3
        return out
    if sc == "OcuSync RC":  # measured hops: 0.4-1.7 ms bursts every 2-6 ms across the band
        t0, out = 0.0, []
        while t0 < dur_s:
            f = rng.uniform(e["band_mhz"][0] + 2.5, e["band_mhz"][1] - 2.5)
            out.append((t0, min(rng.uniform(0.4e-3, 1.7e-3), dur_s - t0), f, 5.0, "ofdm4"))
            t0 += rng.uniform(2e-3, 6e-3)
        return out
    if sc == "Wi-Fi":  # sparse PPDUs, airtime = duty
        n = max(1, round(duty * dur_s / 0.4e-3))
        return [(float(t), min(rng.uniform(0.2e-3, 0.6e-3), dur_s - t), e["f0"], e["bw_mhz"], "wifi")
                for t in np.sort(rng.uniform(0, max(dur_s - 0.6e-3, 0.0), n))]
    if sc == "Wideband noise":  # barrage jammer: continuous band-limited noise
        return [(0.0, dur_s, e["f0"], e["bw_mhz"], "noise")]
    n = max(1, round(duty * dur_s / 0.5e-3))  # anything else: noise burst train at its duty
    return [(float(t), min(rng.uniform(0.3e-3, 0.7e-3), dur_s - t), e["f0"], e["bw_mhz"], "noise")
            for t in np.sort(rng.uniform(0, max(dur_s - 0.7e-3, 0.0), n))]


def _noise(rng, fs, dur_s, f_off, bw_hz):
    """Flat complex noise on the bins whose RF (f_off + f) stays inside the emitter band.

    Built at its final RF position: for a jammer wider than fs the baseband+shift route
    cannot represent the whole visible slice.
    """
    n = max(2, int(round(dur_s * fs)))
    spec = np.fft.fft((rng.standard_normal(n) + 1j * rng.standard_normal(n)) / np.sqrt(2))
    spec *= np.abs(np.fft.fftfreq(n, 1 / fs) - f_off) <= bw_hz / 2  # bin RF = f_off + f
    return np.fft.ifft(spec)


def _waveform(rng, kind, fs, dur_s, bw_hz):
    """Baseband burst at fs; OFDM is generated at FS_GEN then band-limited resampled."""
    if kind == "wifi":
        return wifi_burst(fs, rng, max(1, int(round((dur_s * 20e6 - 320) / 80))))
    n_sc = max(2, int(bw_hz / 15e3) // 2 * 2)
    n_sym = max(1, int(round(dur_s * FS_GEN / 2188)))
    x = ofdm(qam(rng, (n_sym, n_sc), 16 if kind == "ofdm16" else 4), 2048, [144] * n_sym)
    return x if fs == FS_GEN else fft_resample(x, FS_GEN, fs)


def synthesise_snapshot(rng, center_mhz, fs, dur_s, emitters, nf_db):
    """Snapshot IQ in sqrt(mW), noise floor dBm, and answer-key annotations (one per burst).

    Each burst carries the link's P_rx with a per-burst +/-1 dB jitter, spread over its occupied
    bandwidth; the front end keeps only the slice inside the capture band (never aliases it in),
    so a fully in-band burst carries P_rx and a clipped one keeps its power spectral density.
    """
    n = int(round(dur_s * fs))
    noise_dbm = -174.0 + 10 * np.log10(fs) + nf_db
    x = np.sqrt(10 ** (noise_dbm / 10)) * (rng.standard_normal(n) + 1j * rng.standard_normal(n)) / np.sqrt(2)
    ann = []
    for e in emitters:
        for t0, dur, f_mhz, bw_mhz, kind in _bursts(rng, e, dur_s):
            half, edge = bw_mhz / 2, (fs / 2) * 1e-6
            flo, fhi = max(f_mhz - half, center_mhz - edge), min(f_mhz + half, center_mhz + edge)
            if flo >= fhi:
                continue  # entirely outside the capture band (a hop this radio cannot see)
            s0 = int(round(t0 * fs))
            if s0 >= n:
                continue
            f_off = (f_mhz - center_mhz) * 1e6
            if kind == "noise":  # stationary: already on its RF bins, scaled to keep the PSD
                w = unit_power(_noise(rng, fs, dur, f_off, bw_mhz * 1e6)) * np.sqrt((fhi - flo) / bw_mhz)
                seg = w[: n - s0]
            else:
                w = unit_power(_waveform(rng, kind, fs, dur, bw_mhz * 1e6))
                spec = np.fft.fft(w)
                spec *= np.abs(f_off + np.fft.fftfreq(len(w), 1 / fs)) < fs / 2  # no aliasing past Nyquist
                seg = freq_shift(np.fft.ifft(spec), f_off, fs, t0=s0 / fs)[: n - s0]
            p_dbm = e["p_rx_dbm"] + rng.uniform(-1, 1)  # per-burst +/- 1 dB jitter
            seg = np.sqrt(10 ** (p_dbm / 10)) * seg
            x[s0:s0 + seg.size] += seg
            ann.append({
                "core:sample_start": s0, "core:sample_count": int(seg.size),
                "core:freq_lower_edge": round(flo * 1e6), "core:freq_upper_edge": round(fhi * 1e6),
                "core:label": e["sig_class"],
                "mirror:object_id": e["tx_obj"], "mirror:link": e["id"],
                "mirror:rx_power_dbm": round(p_dbm, 1),
            })
    ann.sort(key=lambda a: a["core:sample_start"])
    return x, noise_dbm, ann


def quantise(x):
    """ci16_le I/Q at roughly half of full scale; returns (int16 (n, 2), dBm at full scale)."""
    s = 16384.0 / np.abs(x).max()
    y = np.clip(np.round(np.stack([x.real, x.imag], 1) * s), -32767, 32767)
    return y.astype("<i2"), float(20 * np.log10(32767.0 / s))


def _spectrogram(x, path, label):
    """Time down, frequency across, dB colour ramp; the label is burned into the top-left."""
    nper = 1024
    rows = x.size // nper
    X = np.fft.fftshift(np.fft.fft(x[: rows * nper].reshape(rows, nper)), axes=1)
    pdb = 10 * np.log10((np.abs(X) / nper) ** 2 + 1e-30)  # dBm per bin
    lo, hi = np.percentile(pdb, 25), pdb.max()
    v = np.clip((pdb - lo) / max(hi - lo, 1e-9), 0, 1)
    ramp = np.array([[12, 25, 70], [30, 90, 150], [40, 170, 150], [170, 210, 70], [250, 235, 90]], float)
    rgb = np.stack([np.interp(v, np.linspace(0, 1, len(ramp)), ramp[:, c]) for c in range(3)], -1)
    img = Image.fromarray(rgb.astype(np.uint8), "RGB")
    ImageDraw.Draw(img).text((4, 2), label, fill=(255, 255, 255))
    img.save(path)


# ------------------------------------------------------------------ sensor plumbing

def _params(sensor):
    unknown = set(sensor.params) - set(DEFAULTS)
    if unknown:
        raise ValueError(f"rf_iq {sensor.id}: unknown params {sorted(unknown)}")
    p = {**DEFAULTS, **sensor.params}
    for k in ("center_mhz", "fs_msps", "dur_ms", "nf_db", "gain_dbi"):
        p[k] = float(p[k])
    if not all(np.isfinite(p[k]) for k in ("center_mhz", "fs_msps", "dur_ms", "nf_db", "gain_dbi")):
        raise ValueError(f"rf_iq {sensor.id}: centre/rate/duration/params must be finite")
    if p["center_mhz"] <= 0 or p["fs_msps"] <= 0 or p["dur_ms"] <= 0:
        raise ValueError(f"rf_iq {sensor.id}: center_mhz, fs_msps and dur_ms must be > 0")
    p["max_snapshots"] = int(p["max_snapshots"])
    if p["max_snapshots"] < 1:
        raise ValueError(f"rf_iq {sensor.id}: max_snapshots must be >= 1")
    if p["times_s"] is not None:
        if not isinstance(p["times_s"], (list, tuple)) or not p["times_s"]:
            raise ValueError(f"rf_iq {sensor.id}: times_s must be a non-empty list or null")
        p["times_s"] = sorted(float(t) for t in p["times_s"])
        if not all(np.isfinite(p["times_s"])) or p["times_s"][0] < 0:
            raise ValueError(f"rf_iq {sensor.id}: times_s must be finite and >= 0")
    return p


def _visible(link, lo, hi):
    """Can the link's emissions land inside the capture band [lo, hi] MHz?"""
    if link["hop"]:
        return link["band_mhz"][0] < hi and link["band_mhz"][1] > lo
    return link["f0"] - link["bw_mhz"] / 2 < hi and link["f0"] + link["bw_mhz"] / 2 > lo


def _active(link, ctx, t):
    if not np.isfinite(ctx.state(link["tx_obj"], t)["x"]):
        return False
    return link["tx_obj"] == link["owner"] or bool(np.isfinite(ctx.state(link["owner"], t)["x"]))


def _pick_times(p, links, ctx, sensor):
    """Up to max_snapshots times spread evenly over truth ticks with a non-neutral link on air."""
    lo, hi = p["center_mhz"] - p["fs_msps"] / 2, p["center_mhz"] + p["fs_msps"] / 2
    ticks = np.arange(math.ceil(ctx.cfg.duration_s * ctx.cfg.truth_hz)) / ctx.cfg.truth_hz
    on = np.zeros(ticks.shape, bool)
    for L in links:
        if ctx.objects[L["owner"]].side == "neutral":
            continue
        if L["hop"]:
            near = L["band_mhz"][0] < hi and L["band_mhz"][1] > lo
        else:
            near = lo <= L["f0"] <= hi  # a centre frequency inside the capture band
        if not near:
            continue
        act = np.isfinite(ctx.state(L["tx_obj"], ticks)["x"])
        if L["tx_obj"] != L["owner"]:
            act &= np.isfinite(ctx.state(L["owner"], ticks)["x"])
        on |= act
    tt = ticks[on & ctx.alive(sensor, ticks)]
    if tt.size <= p["max_snapshots"]:
        return list(tt)
    i = np.unique(np.round(np.linspace(0, tt.size - 1, p["max_snapshots"])).astype(int))
    return list(tt[i])


def run(sensors, ctx):
    links = rf_df._links(ctx)
    (ctx.out / "answer_key").mkdir(parents=True, exist_ok=True)
    for s in sensors:
        p = _params(s)
        if p["times_s"] is not None and p["times_s"][-1] >= ctx.cfg.duration_s:
            raise ValueError(f"rf_iq {s.id}: times_s beyond the scenario duration")
        rng = ctx.rng(f"rf_iq:{s.id}")
        center, fs, dur_s = p["center_mhz"], p["fs_msps"] * 1e6, p["dur_ms"] * 1e-3
        lo, hi = center - p["fs_msps"] / 2, center + p["fs_msps"] / 2
        times = [t for t in (p["times_s"] or _pick_times(p, links, ctx, s)) if ctx.alive(s, t)]
        rx = ctx.sensor_xyz(s)
        folder, keydir = ctx.out / "sensors" / s.id, ctx.out / "answer_key" / s.id
        folder.mkdir(parents=True, exist_ok=True)
        keydir.mkdir(parents=True, exist_ok=True)
        rows = []
        for k, t in enumerate(times):
            emitters = []
            for L in links:
                if not _visible(L, lo, hi) or not _active(L, ctx, t):
                    continue
                st = ctx.state(L["tx_obj"], t)
                loss = rf_df.path_loss_db(ctx.world, np.array([[st["x"], st["y"], st["z"]]]), rx, L["f0"])[0]
                emitters.append({**L, "p_rx_dbm": L["eirp_dbm"] + p["gain_dbi"] - loss})
            x, noise_dbm, ann = synthesise_snapshot(rng, center, fs, dur_s, emitters, p["nf_db"])
            iq, fs_dbm = quantise(x)
            stem = f"snap_{k:03d}"
            iq.tofile(folder / f"{stem}.sigmf-data")
            glob = {
                "core:datatype": "ci16_le", "core:sample_rate": fs, "core:version": "1.2.0",
                "core:hw": "OASIS synthetic SDR",
                "core:description": f"SYNTHETIC {s.id} wideband snapshot at {center:g} MHz; "
                                    f"noise floor {noise_dbm:.1f} dBm; ci16 full scale = {fs_dbm:.1f} dBm",
                "core:extensions": [{"name": "mirror", "version": "0.1.0", "optional": True}],
                "mirror:full_scale_dbm": round(fs_dbm, 2),
            }
            caps = [{"core:sample_start": 0, "core:frequency": center * 1e6, "core:datetime": ctx.iso(t)}]
            (folder / f"{stem}.sigmf-meta").write_text(json.dumps(
                {"global": glob, "captures": caps, "annotations": []}, indent=2))
            (keydir / f"{stem}.sigmf-meta").write_text(json.dumps(
                {"global": glob, "captures": caps, "annotations": ann}, indent=2))
            _spectrogram(x, folder / f"{stem}.png", f"{ctx.iso(t)}  {center:g} MHz")
            rows.append([f"{s.id}-{k:06d}", ctx.iso(t), f"{t:.3f}", len(ann),
                         ";".join(dict.fromkeys(a["mirror:object_id"] for a in ann)), f"{stem}.sigmf-data"])
        with open(ctx.out / "answer_key" / f"{s.id}.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["record_id", "time_utc", "t", "n_bursts", "object_ids", "file"])
            w.writerows(rows)
        print(f"{s.id}: {len(times)} snapshot(s), {sum(r[3] for r in rows)} burst(s)")
