"""Acoustic microphone ("Sky Fortress" style pole mic): what a cheap mic on a 3 m pole records.

One true world -> one waveform per mic. Sources are every object with a catalog `sound`
{f0_hz, level_db_1m}; the signal is a harmonic series k*f0 (k=1..10, amplitudes ~1/k) with
per-harmonic fixed offsets and slow rotor AM, plus broadband noise 10 dB below the tonal
level. Everything is rendered through the real propagation:

  * retarded emission time t = tau + r(tau)/c (two fixed-point iterations) evaluated via
    phase accumulation -> delay AND Doppler fall out of the geometry alone (1 km ~ 2.9 s);
  * 1/r spreading; ISO 9613-1 atmospheric absorption per harmonic from the scenario weather;
  * terrain screening when world.los is False: Maekawa 10*log10(3 + 20N), N = 2*delta/lambda,
    delta = path-length excess over the dominant obstruction of the real DEM profile, capped
    at 25 dB;
  * wind: downwind up to +3 dB, upwind up to -10 dB beyond 300 m, scaled by cos(angle).

Ambient is pink noise at `ambient_dba` (A-weighted, calibrated analytically) plus slow gusts.
Audio is written only where something is plausibly present: predicted source level within
10 dB of ambient, or predicted tone level within 10 dB of the detector's per-bin noise floor
(narrowband tones sit far below the broadband noise yet stay detectable -- that is how the
RF-silent fiber-optic FPV gets caught).

DETECTIONS. Each `frame_s` the detector sums energy in narrow bands around the harmonics of
each catalog f0 class against a local ambient estimate (spectral median). Quiet, slowly
Doppler-drifting tones do not clear `detect_snr_db` in a single 1 s frame at range; a narrowband
tone tracker therefore fits the tone's frequency track over the last `int_s` seconds and
integrates coherently along it (matched-filter gain 10*log10(T), minus `TRACK_LOSS_DB` for
the fit residual) -- the standard acoustic-surveillance technique. This is the only reason the
dusk Shahed and the fiber FPV are heard kilometres out through the terrain screening.
Record times are ARRIVAL times; the answer key gives the emission time and delay per record.

Outputs per mic: sensors/<id>/audio_<k>.wav (int16, BWF bext with a UTC sample time
reference), audio_<k>.json sidecar (start time_utc, fs, gain: dB re 20 uPa at full scale, so
levels are recoverable), a spectrogram PNG per window, detections.csv, media.csv and
status.json. answer_key/<id>.csv maps every record to the dominant object and why.
"""
import json
import struct
from collections import deque

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from scipy import signal

from ..catalog import CATALOG

DEFAULTS = dict(fs=16000, ambient_dba=35.0, max_window_min=10.0, detect_snr_db=6.0,
                frame_s=1.0, int_s=30.0)
LABEL = {"hostile": "target", "unknown": "target", "friendly": "friendly", "neutral": "clutter"}
FAMILY = {"dji_mavic3": "multirotor", "fpv_analog": "FPV", "fpv_fiber": "FPV",
          "interceptor": "FPV", "octopus": "FPV", "jedi": "FPV",
          "shahed136": "two-stroke engine", "gerbera": "two-stroke engine", "orlan10": "two-stroke engine",
          "zala": "electric fixed-wing", "supercam": "electric fixed-wing", "lancet": "electric fixed-wing",
          "geese": "birds"}  # detector class names; tests/test_microphone.py checks every sounding type has one
TRACK_LOSS_DB = 2.5     # AM sidebands + imperfect frequency fit: coherence never reaches theory
N_HARM = 10
R_EARTH = 6371e3
K_REFRACT = 4.0 / 3.0


# --- acoustic physics --------------------------------------------------------------
def c_sound(temp_c):
    return 331.3 + 0.606 * temp_c


def a_weight_db(f):
    """IEC 61672 A-weighting in dB, normalized to 0 dB at 1 kHz."""
    f = np.maximum(np.asarray(f, float), 1e-6)
    num = 12194.0 ** 2 * f ** 4
    den = (f ** 2 + 20.6 ** 2) * np.sqrt((f ** 2 + 107.7 ** 2) * (f ** 2 + 737.9 ** 2)) * (f ** 2 + 12194.0 ** 2)
    return 20 * np.log10(num / den) - 20 * np.log10(
        12194.0 ** 2 * 1e12 / ((1e6 + 20.6 ** 2) * np.sqrt((1e6 + 107.7 ** 2) * (1e6 + 737.9 ** 2)) * (1e6 + 12194.0 ** 2)))


def iso9613_alpha_db_per_km(f, temp_c, rh_pct, p_kpa=101.325):
    """ISO 9613-1 atmospheric absorption, dB/km, f in Hz (oxygen + nitrogen + classical)."""
    T, T0 = temp_c + 273.15, 273.15
    tr = T / T0
    ps_pr = 10 ** (-6.8346 * (T0 / T) ** 1.261 + 4.6151)          # saturation pressure ratio
    h = rh_pct * ps_pr * (101.325 / p_kpa)                        # water-vapour molar conc., %
    f_ro = (p_kpa / 101.325) * (24 + 4.04e4 * h * (0.02 + h) / (0.391 + h))
    f_rn = (p_kpa / 101.325) * tr ** -0.5 * (9 + 280 * h * np.exp(-4.17 * (tr ** (-1 / 3) - 1)))
    classical = 1.84e-11 * (p_kpa / 101.325) * np.sqrt(tr)
    r_o = 0.01275 * np.exp(-2239.1 / T) * f_ro / (f_ro ** 2 + f ** 2)
    r_n = 0.1068 * np.exp(-3352.0 / T) * f_rn / (f_rn ** 2 + f ** 2)
    # the bracket yields dB/m at f in Hz; report dB/km
    return 1000.0 * 8.686 * f ** 2 * (classical + tr ** -2.5 * (r_o + r_n))


def wind_gain_db(cos_theta, r):
    """Downwind up to +3 dB, upwind up to -10 dB beyond 300 m, scaled by cos(angle)."""
    cos_theta = np.asarray(cos_theta, float)
    return (3.0 * np.maximum(cos_theta, 0.0) + 10.0 * np.minimum(cos_theta, 0.0)) * np.clip(r / 300.0, 0.0, 1.0)


def screen_loss_db(world, p, mic, c, freqs, n_prof=160):
    """Maekawa terrain-screening loss (dB) per source position and per frequency.

    p (N,3) source x,y,z MSL at emission, mic (3,), freqs (F,) -> (N, F) losses and (N,) LOS.
    delta = path-length difference over the highest blocking point of the real DEM profile
    (earth-curvature bulge included), loss = 10*log10(3 + 20*2*delta/lambda), capped at 25 dB.
    """
    p = np.atleast_2d(np.asarray(p, float))
    freqs = np.atleast_1d(np.asarray(freqs, float))
    good = np.isfinite(p).all(1)  # sources off air (before launch / after impact) are silent anyway
    p = np.where(good[:, None], p, np.asarray(mic, float) + [1.0, 0.0, 0.0])
    los = np.asarray(world.los(p, np.broadcast_to(np.asarray(mic, float), p.shape))).reshape(-1) & good
    D = np.maximum(np.hypot(mic[0] - p[:, 0], mic[1] - p[:, 1]), 1.0)
    prof = world.profile(p[:, 0], p[:, 1], mic[0], mic[1], n_prof)          # (N, n)
    ts = np.linspace(0.0, 1.0, n_prof)
    ray = p[:, 2][:, None] + (mic[2] - p[:, 2])[:, None] * ts
    bulge = (D[:, None] * ts) * (D[:, None] * (1.0 - ts)) / (2 * K_REFRACT * R_EARTH)
    exc = prof + bulge - ray
    exc[:, 0] = -np.inf
    exc[:, -1] = -np.inf
    j = exc.argmax(1)
    e = np.maximum(exc[np.arange(j.size), j], 0.0)
    d1, d2 = D * ts[j], D * (1.0 - ts[j])
    delta = np.hypot(d1, e) + np.hypot(d2, e) - D
    n_fresnel = 2.0 * delta[:, None] * freqs[None, :] / c
    loss = np.minimum(25.0, 10.0 * np.log10(3.0 + 20.0 * n_fresnel))
    return np.where(los[:, None], 0.0, loss), los


# --- source model ------------------------------------------------------------------
def source_spec(sound, rng, temp_c, rh_pct):
    """Harmonic amplitudes at 1 m (total power -> level_db_1m), AM wobble, broadband level."""
    f0, level = sound["f0_hz"], sound["level_db_1m"]
    ks = np.arange(1, N_HARM + 1)
    off = rng.normal(0.0, 1.5, N_HARM)                 # fixed per-harmonic offset, dB
    power = (1.0 / ks ** 2) * 10 ** (off / 10.0)       # amplitude ~1/k -> -6 dB per octave
    power = power / power.sum() * 10 ** (level / 10.0)
    return dict(
        f0=f0, ks=ks, freqs=ks * f0,
        amp=np.sqrt(2.0 * power),                      # peak amplitude per harmonic (RMS^2 = power)
        bb_var=10 ** ((level - 10.0) / 10.0),          # broadband noise 10 dB below the tonal level
        am_f=rng.uniform(0.15, 1.2, 2), am_ph=rng.uniform(0.0, 2 * np.pi, 2), am_depth=0.15,
        alpha=iso9613_alpha_db_per_km(ks * f0, temp_c, rh_pct),
    )


def retarded(state_fn, mic, t, c, iters=2):
    """Emission time tau solving t = tau + r(tau)/c by two fixed-point iterations.

    Returns tau, r, p where p is the source (x, y, z) at tau; non-finite where the
    source does not exist yet at the emission time (it simply is not heard then).
    """
    t = np.asarray(t, float)
    tau = t - np.linalg.norm(state_fn(t) - mic, axis=-1) / c
    for _ in range(iters):
        tau = t - np.linalg.norm(state_fn(tau) - mic, axis=-1) / c
    p = state_fn(tau)
    return tau, np.linalg.norm(p - mic, axis=-1), p


# --- ambient ----------------------------------------------------------------------
def ambient_s0(fs, ambient_dba):
    """S0 of the pink PSD S(f) = S0/f [(20 uPa)^2/Hz] whose A-weighted level is ambient_dba."""
    f = np.linspace(20.0, fs / 2.0, 4096)
    integral = np.trapezoid(10 ** (a_weight_db(f) / 10.0) / f, f)
    return 10 ** (ambient_dba / 10.0) / integral


def pink_noise(rng, n, fs, s0):
    """Pink noise with one-sided PSD S0/f, synthesized in the frequency domain."""
    x = rng.normal(size=n // 2 + 1) + 1j * rng.normal(size=n // 2 + 1)
    f = np.fft.rfftfreq(n, 1.0 / fs)
    # E|X|^2 = 2 per bin; one-sided PSD of irfft output is 2|Y|^2/(fs*n) -> scale below
    scale = np.sqrt(s0 * fs * n / 4.0) / np.sqrt(np.maximum(f, fs / n))
    scale[0] = 0.0
    return np.fft.irfft(x * scale, n)


# --- rendering --------------------------------------------------------------------
def render_source(world, env, mic, state_fn, spec, t0, t1, fs, noise_rng,
                  tones=True, broadband=True, chunk=16384):
    """One source's pressure at the mic over arrival times [t0, t1), in dB re 20 uPa units.

    env: {c, wind_to (2,)}. Phases accumulate on emission time tau, so Doppler and delay
    come from geometry alone. Where the source does not exist yet at tau the contribution
    is zero (the sound has not arrived).
    """
    n = int(round((t1 - t0) * fs))
    out = np.zeros(n)
    c = env["c"]
    g = t0 - 80.0   # emission-time base of the broadband noise (covers the worst-case delay)
    noise = pink_noise(noise_rng, int((t1 - g) * fs) + 16, fs, spec["bb_var"]) if broadband else None
    prev_tau, phases = None, np.zeros(N_HARM)
    for i0 in range(0, n, chunk):
        m = min(chunk, n - i0)
        t = t0 + np.arange(i0, i0 + m) / fs
        tau, r, p = retarded(state_fn, mic, t, c)
        hear = np.isfinite(r) & np.isfinite(tau)     # source exists at its emission time
        tau_s = np.where(hear, tau, t)               # sanitized so phases never go NaN
        r_s = np.where(hear, r, 1e6)
        ref = int(np.argmax(hear)) if hear.any() else m // 2   # first heard sample for slow scalars
        screen, _ = screen_loss_db(world, p[[ref]], mic, c, spec["freqs"])
        screen = np.nan_to_num(screen, nan=0.0)
        u = mic[:2] - p[ref, :2]
        cos_theta = float(np.dot(env["wind_to"], u / max(np.linalg.norm(u), 1.0)))
        wind = wind_gain_db(np.nan_to_num(cos_theta), r_s)
        am = spec["am_depth"] * np.sin(
            2 * np.pi * spec["am_f"][:, None] * tau_s[None, :] + spec["am_ph"][:, None]).sum(0)
        dtau = np.diff(np.concatenate(
            [[prev_tau if prev_tau is not None else tau_s[0] - 1.0 / fs], tau_s]))
        gain = np.where(hear, 1.0 + am, 0.0)
        att_r = 20 * np.log10(r_s) + wind
        if tones:
            for j in range(N_HARM):
                f_k = spec["freqs"][j]
                att = att_r + spec["alpha"][j] * r_s / 1000.0 + screen[0, j]
                ph = phases[j] + np.cumsum(2 * np.pi * f_k * dtau)
                out[i0:i0 + m] += spec["amp"][j] * 10 ** (-att / 20.0) * gain * np.sin(ph)
                phases[j] = ph[-1]
        if broadband:
            nb = np.interp((tau_s - g) * fs, np.arange(noise.size, dtype=float), noise)
            att = att_r + spec["alpha"][0] * r_s / 1000.0 + screen[0, 0]
            out[i0:i0 + m] += nb * 10 ** (-att / 20.0) * gain
        prev_tau = tau_s[-1]
    return out


def render_ambient(rng, n, fs, s0, t0):
    """Pink ambient at ambient_dba plus slow wind gusts (dB-scale sinusoids)."""
    x = pink_noise(rng, n, fs, s0)
    t = t0 + np.arange(n) / fs
    gust_db = 1.5 * np.sin(2 * np.pi * 0.011 * t + 0.7) + 1.0 * np.sin(2 * np.pi * 0.023 * t + 2.1)
    return x * 10 ** (gust_db / 20.0)


def measure_dba(x, fs):
    """A-weighted level of a signal, dB re 20 uPa."""
    x = np.asarray(x, float)
    if x.size < 256:
        return float("nan")
    f, pxx = signal.welch(x, fs, nperseg=min(8192, x.size))
    return float(10.0 * np.log10(np.trapezoid(pxx * 10 ** (a_weight_db(f) / 10.0), f) + 1e-30))


# --- per-frame prediction (gating + answer key) ------------------------------------
def predict(world, env, mic, state_fn, spec, t_grid, chunk=2048):
    """Physics-predicted quantities per arrival frame: range, delay, levels, LOS."""
    c = env["c"]
    tau, r, p = retarded(state_fn, mic, t_grid, c)
    valid = np.isfinite(r) & (tau >= 0.0)
    screen = np.zeros((t_grid.size, N_HARM))
    los = np.zeros(t_grid.size, bool)
    for i0 in range(0, t_grid.size, chunk):
        m = (np.arange(t_grid.size) >= i0) & (np.arange(t_grid.size) < i0 + chunk) & valid
        if not m.any():
            continue
        s, l = screen_loss_db(world, p[m], mic, c, spec["freqs"])
        screen[m], los[m] = s, l
    u = mic[None, :2] - p[:, :2]
    cos_theta = (u @ env["wind_to"]) / np.maximum(np.linalg.norm(u, axis=1), 1.0)
    wind = wind_gain_db(cos_theta, r)
    att = (20 * np.log10(r)[:, None] + spec["alpha"][None, :] * r[:, None] / 1000.0
           + screen + wind[:, None])                       # (T, N_HARM) dB
    power_k = (spec["amp"] ** 2 / 2.0)[:, None] * 10 ** (-att.T / 10.0)  # (N_HARM, T)
    power_bb = spec["bb_var"] * 10 ** (-att[:, 0] / 10.0)
    aw = 10 ** (a_weight_db(spec["freqs"]) / 10.0)
    level_tot = 10 * np.log10(power_k.sum(0) + power_bb + 1e-300)
    level_dba = 10 * np.log10((power_k * aw[:, None]).sum(0)
                              + power_bb * 10 ** (a_weight_db(spec["f0"]) / 10.0) + 1e-300)
    level_fund = 10 * np.log10(power_k[0] + 1e-300)
    valid &= np.isfinite(level_tot)
    return dict(tau=tau, r=r, los=los, valid=valid, level_tot=level_tot,
                level_dba=level_dba, level_fund=level_fund)


# --- detector ---------------------------------------------------------------------
PFA_TRACK = 1e-3  # false-alarm probability per tone-tracker update on pure ambient


def detect(x, fs, t0, params, classes, rng):
    """Narrowband harmonic-sum detector with a coherent tone tracker over the last int_s.

    Each frame: energy in narrow bands (3 bins) around the harmonics of each catalog f0
    class over the Doppler grid the class's catalog speed allows, against a local ambient
    estimate (spectral median). The tracker fits f(t) across frames, dechirps the span and
    integrates coherently (10*log10(span) gain), which is what makes quiet, drifting tones
    cross `detect_snr_db` at range. Returns detection dicts (arrival times).
    """
    frame_n = int(round(params["frame_s"] * fs))
    thr = params["detect_snr_db"]
    n_frames = x.size // frame_n
    geo = []
    for cl in classes:
        step = 1.0 / (cl["f0"] * params["frame_s"])
        shifts = np.arange(-cl["vmax"] / 343.0, cl["vmax"] / 343.0 + step, step)
        bins = np.rint(cl["ks"][:, None] * cl["f0"] * (1.0 + shifts[None, :]) * params["frame_s"]).astype(int)
        geo.append((cl, shifts, np.clip(bins, 0, x.size)))

    x_d = signal.decimate(x, 8, ftype="fir", zero_phase=True) if x.size >= 128 else x
    fs_d = fs / 8
    tracks = {cl["family"] + str(cl["f0"]): {"hist": deque(), "stat": None, "weak": 99}
              for cl, _, _ in geo}
    det = []
    for k in range(n_frames):
        seg = x[k * frame_n:(k + 1) * frame_n] * np.hanning(frame_n)
        spec = np.abs(np.fft.rfft(seg)) ** 2
        med = signal.medfilt(spec, 21) + 1e-30
        t_arr = t0 + (k + 1) * params["frame_s"]
        short_db, f_est = {}, {}
        for cl, shifts, bins in geo:
            key = cl["family"] + str(cl["f0"])
            if bins.max() + 1 >= spec.size:
                short_db[key], f_est[key] = -99.0, cl["f0"]
                continue
            tone = (spec[np.clip(bins - 1, 0, spec.size - 1)] + spec[bins]
                    + spec[np.clip(bins + 1, 0, spec.size - 1)]).sum(0)
            noise = (3.0 * med[bins]).sum(0)
            j = int(np.argmax(tone / noise))
            short_db[key] = 10.0 * np.log10(tone[j] / noise[j] + 1e-30)
            b0 = int(bins[0, j])
            if 0 < b0 < spec.size - 1:
                a, b, c3 = spec[b0 - 1], spec[b0], spec[b0 + 1]
                den = a - 2 * b + c3
                delta = 0.5 * (a - c3) / den if abs(den) > 1e-30 else 0.0
                f_est[key] = cl["f0"] * (1.0 + shifts[j]) + np.clip(delta, -1, 1) / params["frame_s"]
            else:
                f_est[key] = cl["f0"] * (1.0 + shifts[j])

        best = None
        for cl, _, _ in geo:
            key = cl["family"] + str(cl["f0"])
            tr = tracks[key]
            tr["hist"].append((t_arr, f_est[key]))
            while tr["hist"] and tr["hist"][0][0] < t_arr - params["int_s"] - params["frame_s"]:
                tr["hist"].popleft()
            if short_db[key] > -8.0:
                tr["weak"] = 0
            else:
                tr["weak"] += 1
                if tr["weak"] > 3:
                    tr["stat"] = None
            hist = list(tr["hist"])
            if len(hist) >= 8 and k % 3 == 0 and tr["weak"] <= 3:
                tk = np.array([h[0] for h in hist])
                fk = np.array([h[1] for h in hist])
                coef = np.array([fk.mean(), 0.0])
                for _ in range(2):  # robust line fit: false peaks off the track get dropped
                    a_mat = np.stack([np.ones_like(tk), tk - tk.mean()], 1)
                    coef, *_ = np.linalg.lstsq(a_mat, fk, rcond=None)
                    resid = fk - a_mat @ coef
                    s = 1.4826 * np.median(np.abs(resid - np.median(resid))) + 1e-9
                    keep = np.abs(resid) <= 2.5 * s
                    if 6 <= keep.sum() < tk.size:
                        tk, fk = tk[keep], fk[keep]
                slope, f_mid = coef[1], coef[0]
                i0 = max(int(round((tk.min() - t0) * fs_d)), 0)
                i1 = min(int(round((tk.max() + params["frame_s"] - t0) * fs_d)), x_d.size)
                if i1 - i0 >= int(0.5 * fs_d):
                    u = (np.arange(i0, i1) / fs_d) - 0.5 * (i1 - i0) / fs_d
                    y = x_d[i0:i1] * np.hanning(i1 - i0) * np.exp(-1j * np.pi * slope * u ** 2)
                    y_spec = np.abs(np.fft.fft(y)) ** 2
                    freqs = np.fft.fftfreq(i1 - i0, 1.0 / fs_d)
                    near = np.abs(freqs - f_mid) <= 3.0
                    pk = int(np.argmax(np.where(near, y_spec, -np.inf)))
                    around = (np.abs(freqs - f_mid) >= 2.0) & (np.abs(freqs - f_mid) <= 20.0)
                    # CFAR: the max of M searched bins of pure noise sits ~ln(M/pfa)/ln2 above their median, so
                    # reference the peak to that level (pfa per tracker update), not to the median itself
                    cfar = np.log(max(int(near.sum()), 2) / PFA_TRACK) / np.log(2.0)
                    ratio = y_spec[pk] / (np.median(y_spec[around]) + 1e-30)
                    tr["stat"] = (ratio / cfar * 10 ** (thr / 10.0), (i1 - i0) / fs_d)
            ratio_db = short_db[key]
            if tr["stat"] is not None:
                ratio_db = max(ratio_db, 10.0 * np.log10(tr["stat"][0] + 1e-30))
            if best is None or ratio_db > best[1]:
                best = (cl, ratio_db, key)

        if best is not None and best[1] > thr:
            cl, snr_db, key = best
            rivals = []
            for c2, _, _ in geo:
                if c2 is cl:
                    continue
                k2 = c2["family"] + str(c2["f0"])
                stat2 = tracks[k2]["stat"]
                r2 = 10.0 * np.log10(stat2[0] + 1e-30) if stat2 is not None else short_db[k2]
                rivals.append((r2, c2["family"]))
            rivals.sort(key=lambda z: z[0], reverse=True)
            p_correct = float(np.clip(0.55 + 0.06 * (snr_db - thr), 0.55, 0.98))
            fam = cl["family"]
            conf = round(p_correct, 2)
            if rivals and rng.random() > p_correct:
                fam = rivals[0][1]
                conf = round(1.0 - p_correct, 2)
            det.append(dict(t=t_arr, family=fam, snr_db=round(float(snr_db), 1), conf=conf))
    return det


# --- output files -----------------------------------------------------------------
def write_wav_bwf(path, x_i16, fs, t_ref_samples, description):
    """int16 PCM WAV with a BWF bext chunk (time reference in samples since UTC midnight)."""
    fmt = struct.pack("<HHIIHH", 1, 1, fs, fs * 2, 2, 16)
    bext = (
        description.encode("ascii", "replace")[:255].ljust(256, b"\0")
        + b"Mirror World".ljust(32, b"\0")
        + b"microphone".ljust(32, b"\0")
        + b"2026-11-04" + b"00:00:00"
        + struct.pack("<Q", int(t_ref_samples))
        + struct.pack("<H", 1) + b"\0" * 64 + b"\0" * 190
    )
    data = x_i16.astype("<i2").tobytes()
    chunks = b"fmt " + struct.pack("<I", len(fmt)) + fmt
    chunks += b"bext" + struct.pack("<I", len(bext)) + bext
    chunks += b"data" + struct.pack("<I", len(data)) + data
    with open(path, "wb") as fh:
        fh.write(b"RIFF" + struct.pack("<I", 4 + len(chunks)) + b"WAVE" + chunks)


def spectrogram_png(path, x, fs, label, cols=1400, nfft=2048):
    """Log-scaled 0-4 kHz spectrogram: time across, low frequencies at the bottom."""
    x = np.asarray(x, float)
    if x.size < nfft:
        x = np.pad(x, (0, nfft - x.size))
    hop = max(1, (x.size - nfft) // cols)
    n_frames = 1 + (x.size - nfft) // hop
    frames = np.lib.stride_tricks.as_strided(
        x, (n_frames, nfft), (x.strides[0] * hop, x.strides[0])).copy()
    mag = np.abs(np.fft.rfft(frames * np.hanning(nfft), axis=1))
    f = np.fft.rfftfreq(nfft, 1.0 / fs)
    db = 20 * np.log10(mag[:, f <= 4000.0].T + 1e-12)[::-1]   # (freq, time), low freq at the bottom
    db -= db.max()
    img = np.clip((db + 70.0) / 70.0 * 255, 0, 255).astype(np.uint8)
    im = Image.fromarray(img, "L").resize((min(cols, img.shape[1] * 2), 512), Image.BILINEAR)
    lut = np.stack([
        np.interp(np.linspace(0, 1, 256), [0, .35, .7, 1], [30, 30, 250, 255]),
        np.interp(np.linspace(0, 1, 256), [0, .35, .7, 1], [20, 180, 220, 255]),
        np.interp(np.linspace(0, 1, 256), [0, .35, .7, 1], [60, 240, 60, 255]),
    ], 1).astype(np.uint8)
    im = Image.merge("RGB", [im.point(list(lut[:, i])) for i in range(3)])
    draw = ImageDraw.Draw(im)
    try:
        font = ImageFont.load_default(size=18)
    except TypeError:
        font = ImageFont.load_default()
    draw.text((8, 6), label, fill=(255, 255, 255), font=font)
    im.save(path)


# --- one sensor -------------------------------------------------------------------
def _windows(active, t_grid, max_s, gap_s=15.0):
    """Merge active frames into windows (padded, gaps merged, split at max_s)."""
    idx = np.flatnonzero(active)
    if idx.size == 0:
        return []
    dt = t_grid[1] - t_grid[0]
    runs = np.split(idx, np.flatnonzero(np.diff(idx) > gap_s / dt) + 1)
    spans = [(max(t_grid[r[0]] - 5.0, 0.0), t_grid[r[-1]] + 10.0) for r in runs]
    merged = [spans[0]]
    for a, b in spans[1:]:
        if a - merged[-1][1] <= gap_s:
            merged[-1] = (merged[-1][0], b)
        else:
            merged.append((a, b))
    out = []
    for a, b in merged:
        while b - a > max_s:
            out.append((a, a + max_s))
            a += max_s
        out.append((a, b))
    return out


def _sensor(sensor, ctx):
    p = {**DEFAULTS, **sensor.params}
    cfg = ctx.cfg
    wind_to = np.array([np.sin(np.radians(cfg.weather.wind_from_deg + 180.0)),
                        np.cos(np.radians(cfg.weather.wind_from_deg + 180.0))])
    env = dict(temp_c=cfg.weather.temp_c, rh_pct=cfg.weather.rh_pct,
               c=c_sound(cfg.weather.temp_c), wind_to=wind_to)
    mic = ctx.sensor_xyz(sensor)
    s0 = ambient_s0(p["fs"], p["ambient_dba"])

    sources = []
    for o in cfg.objects:
        sound = CATALOG[o.type].get("sound")
        if not sound:
            continue
        spec = source_spec(sound, ctx.rng(f"mic:src:{o.id}"), env["temp_c"], env["rh_pct"])
        sources.append(dict(obj=o, sound=sound, spec=spec,
                            state=lambda t, oid=o.id: np.stack(
                                [ctx.state(oid, t)[k] for k in "xyz"], -1)))

    t_grid = np.arange(0.0, cfg.duration_s, p["frame_s"])
    alive = ctx.alive(sensor, t_grid)
    preds = {s["obj"].id: predict(ctx.world, env, mic, s["state"], s["spec"], t_grid) for s in sources}

    active = np.zeros(t_grid.size, bool)
    for s in sources:
        pr = preds[s["obj"].id]
        snr_pred = (pr["level_fund"] - 10 * np.log10(s0 / s["spec"]["f0"])
                    + 10 * np.log10(p["int_s"]) - TRACK_LOSS_DB)
        active |= pr["valid"] & ((snr_pred >= p["detect_snr_db"] - 2.0)
                                 | (pr["level_dba"] >= p["ambient_dba"] - 10.0))
    active &= alive

    windows = _windows(active, t_grid, p["max_window_min"] * 60.0)
    max_level = max((pr["level_tot"][pr["valid"]].max() for pr in preds.values()
                     if pr["valid"].any()), default=0.0)
    gain_db = float(np.ceil(max_level + 15.0))   # fixed per mic: ~15 dB over the loudest predicted RMS

    folder = ctx.out / "sensors" / sensor.id
    folder.mkdir(parents=True, exist_ok=True)
    (ctx.out / "answer_key").mkdir(parents=True, exist_ok=True)
    lat, lon = ctx.world.to_ll(mic[0], mic[1])
    (folder / "site.json").write_text(json.dumps(dict(
        sensor_id=sensor.id, lat=round(float(lat), 6), lon=round(float(lon), 6),
        alt_msl_m=round(float(mic[2]), 1), mast_m=sensor.mast_m), indent=1))

    classes = []
    for f0 in sorted({s["sound"]["f0_hz"] for s in sources}):
        types = [s["obj"].type for s in sources if s["sound"]["f0_hz"] == f0]
        classes.append(dict(f0=f0, ks=np.arange(1, N_HARM + 1),
                            vmax=max(CATALOG[ty]["speed_mps"] for ty in types),
                            family=FAMILY[types[0]]))

    det_rows, key_rows, media = [], [], []
    clips = 0
    for widx, (w0, w1) in enumerate(windows):
        n = int(round((w1 - w0) * p["fs"]))
        mix = np.zeros(n)
        for s in sources:
            pr = preds[s["obj"].id]
            m = (t_grid >= w0 - 1.0) & (t_grid <= w1 + 1.0)
            if not (pr["valid"] & m).any():
                continue
            mix += render_source(ctx.world, env, mic, s["state"], s["spec"], w0, w1, p["fs"],
                                 ctx.rng(f"mic:noise:{sensor.id}:{s['obj'].id}:{widx}"))
        mix += render_ambient(ctx.rng(f"mic:ambient:{sensor.id}:{widx}"), n, p["fs"], s0, w0)
        scaled = mix / 10 ** (gain_db / 20.0) * 32767.0
        clips += int((np.abs(scaled) > 32767.0).sum())
        x_i16 = np.clip(scaled, -32767, 32767).astype("<i2")
        name = f"audio_{widx + 1}"
        midnight_s = cfg.start.hour * 3600 + cfg.start.minute * 60 + cfg.start.second
        write_wav_bwf(folder / f"{name}.wav", x_i16, p["fs"],
                      round((midnight_s + w0) * p["fs"]), f"{sensor.id} {ctx.iso(w0)}")
        (folder / f"{name}.json").write_text(json.dumps(dict(
            sensor_id=sensor.id, start_time_utc=ctx.iso(w0), t0=round(w0, 3),
            fs=p["fs"], samples=int(n), gain_db_re_20upa_per_fs=gain_db,
            ambient_dba=p["ambient_dba"]), indent=1))
        spectrogram_png(folder / f"{name}.png", x_i16.astype(float), p["fs"],
                        f"{sensor.id}  {ctx.iso(w0)}  {name}.wav")
        media.append((w0, "audio", f"{name}.wav"))
        media.append((w0, "image", f"{name}.png"))

        # detections run on the actual int16 samples: quantization is part of the record
        x_play = x_i16.astype(float) / 32767.0 * 10 ** (gain_db / 20.0)
        dets = detect(x_play, p["fs"], w0, p, classes, ctx.rng(f"mic:det:{sensor.id}:{widx}"))
        if not dets:
            continue
        tt = np.array([d["t"] for d in dets])

        def at(pr):
            """Prediction at the exact arrival time, interpolated over the active frames."""
            v = pr["valid"]
            kk = np.clip(np.searchsorted(t_grid, tt), 0, t_grid.size - 1)
            if not v.any():
                nan = np.full(tt.shape, np.nan)
                return dict(tau=nan, r=nan, level_tot=nan, level_dba=nan, level_fund=nan,
                            los=np.zeros(tt.shape, bool), valid=np.zeros(tt.shape, bool))
            return dict(
                tau=np.interp(tt, t_grid[v], pr["tau"][v]), r=np.interp(tt, t_grid[v], pr["r"][v]),
                level_tot=np.interp(tt, t_grid[v], pr["level_tot"][v]),
                level_dba=np.interp(tt, t_grid[v], pr["level_dba"][v]),
                level_fund=np.interp(tt, t_grid[v], pr["level_fund"][v]),
                los=pr["los"][kk], valid=v[kk])

        at_src = [(s, at(preds[s["obj"].id])) for s in sources]
        for j, d in enumerate(dets):
            cands = [(a["level_tot"][j], s, a) for s, a in at_src if a["valid"][j]]
            if not cands or d["t"] > ctx.cfg.duration_s:  # sound still in flight when recording stops
                continue
            level, dom, a = max(cands, key=lambda c2: c2[0])
            i_end = int(round((d["t"] - w0) * p["fs"]))
            i_start = max(0, i_end - int(p["frame_s"] * p["fs"]))
            det_rows.append(dict(t=d["t"], sensor_id=sensor.id,
                                 level_dba=round(measure_dba(x_play[i_start:i_end], p["fs"]), 1),
                                 snr_db=d["snr_db"], **{"class": d["family"], "conf": d["conf"]}))
            key_rows.append(dict(
                object_id=dom["obj"].id, link=f"{dom['obj'].id}:sound", label=LABEL[dom["obj"].side],
                true_range_m=round(float(a["r"][j]), 1), emission_t=round(float(a["tau"][j]), 3),
                delay_s=round(float(d["t"] - a["tau"][j]), 3), los=bool(a["los"][j]),
                level_at_mic_db=round(float(level), 1), level_at_mic_dba=round(float(a["level_dba"][j]), 1),
                tone_level_db=round(float(a["level_fund"][j]), 1)))

    det_df = pd.DataFrame(det_rows, columns=["t", "sensor_id", "level_dba", "snr_db", "class", "conf"])
    det_df = det_df.sort_values("t").reset_index(drop=True)
    ids = [f"{sensor.id}-{k:06d}" for k in range(len(det_df))]
    det_df.insert(0, "record_id", ids)
    det_df.insert(1, "time_utc", ctx.iso(det_df["t"].to_numpy()))
    det_df.to_csv(folder / "detections.csv", index=False)
    key_df = pd.DataFrame(key_rows, columns=["object_id", "link", "label", "true_range_m", "emission_t",
                                             "delay_s", "los", "level_at_mic_db", "level_at_mic_dba",
                                             "tone_level_db"])
    key_df.insert(0, "record_id", ids)
    key_df.to_csv(ctx.out / "answer_key" / f"{sensor.id}.csv", index=False)
    pd.DataFrame([(t, ctx.iso(t), kind, path) for t, kind, path in sorted(media)],
                 columns=["t", "time_utc", "kind", "path"]).to_csv(folder / "media.csv", index=False)
    (folder / "status.json").write_text(json.dumps(dict(
        sensor_id=sensor.id, params=p, gain_db_re_20upa_per_fs=gain_db,
        windows=[dict(start=ctx.iso(a), end=ctx.iso(b), seconds=round(b - a, 1)) for a, b in windows],
        audio_minutes=round(sum(b - a for a, b in windows) / 60.0, 1),
        detections=len(det_df), clipped_samples=clips,
        note=("clipped samples present: gain is too low" if clips else "")), indent=1))


def run(sensors, ctx):
    for s in sensors:
        _sensor(s, ctx)