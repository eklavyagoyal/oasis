"""Self-check for mirrorworld/sensors/microphone.py — run: uv run python tests/test_microphone.py

Covers the core physics and the detector mechanism:
  1. retarded delay: static source at 1 km -> cross-correlation peak at 1000/c (±1 ms)
  2. Doppler: approaching source at 50 m/s -> f0*c/(c-v) within 1%
  3. terrain screening: a source behind a synthetic wall is >= 10 dB quieter
  4. ISO 9613-1 absorption sanity and ambient/level bookkeeping
  5. the coherent tone tracker detects a drifting tone 4 dB below the per-bin noise floor
  6. BWF WAV round-trip: samples, fs and the bext UTC time reference survive
"""
import struct
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mirrorworld.sensors import microphone as mic  # noqa: E402

FS = 16000
ENV = dict(c=mic.c_sound(5.0), wind_to=np.array([0.0, 1.0]))  # crosswind: zero wind gain
SOUND = {"f0_hz": 450.0, "level_db_1m": 86.0}


class FlatWorld:
    def height(self, x, y):
        x, _ = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float))
        return np.zeros(x.shape)

    def profile(self, xa, ya, xb, yb, n):
        xa, ya, xb, yb = np.broadcast_arrays(*[np.asarray(v, float) for v in (xa, ya, xb, yb)])
        ts = np.linspace(0.0, 1.0, n)
        return self.height(xa[..., None] + (xb - xa)[..., None] * ts,
                           ya[..., None] + (yb - ya)[..., None] * ts)

    def los(self, a, b):
        a, b = np.broadcast_arrays(np.asarray(a, float), np.asarray(b, float))
        ok = np.ones(a.shape[:-1], bool)
        return bool(ok) if a.ndim == 1 else ok


class WallWorld(FlatWorld):
    """Flat except a 30 m wall across x in [300, 320] m."""

    def height(self, x, y):
        x, y = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float))
        return np.where((x >= 300.0) & (x <= 320.0), 30.0, 0.0)

    def los(self, a, b):
        a, b = np.broadcast_arrays(np.asarray(a, float), np.asarray(b, float))
        ts = np.linspace(0.0, 1.0, 201)[1:-1]
        xs = a[..., 0, None] + (b[..., 0, None] - a[..., 0, None]) * ts
        ys = a[..., 1, None] + (b[..., 1, None] - a[..., 1, None]) * ts
        zs = a[..., 2, None] + (b[..., 2, None] - a[..., 2, None]) * ts
        ok = (zs > self.height(xs, ys)).all(-1)
        return bool(ok) if a.ndim == 1 else ok


def static_state(x, y, z):
    return lambda t: np.stack([np.full_like(np.asarray(t, float), x),
                               np.full_like(np.asarray(t, float), y),
                               np.full_like(np.asarray(t, float), z)], -1)


def test_delay():
    spec = mic.source_spec(SOUND, np.random.default_rng(1), 5.0, 80.0)
    mic_xyz = np.array([0.0, 0.0, 3.0])
    t0, t1 = 0.0, 4.0
    x = mic.render_source(FlatWorld(), ENV, mic_xyz, static_state(1000.0, 0.0, 10.0), spec,
                          t0, t1, FS, np.random.default_rng(2), tones=False, broadband=True)
    # zero-delay copy of the emitted broadband noise: same generator, indexed at arrival clock
    g = t0 - 80.0
    noise = mic.pink_noise(np.random.default_rng(2), int((t1 - g) * FS) + 16, FS, spec["bb_var"])
    ref = noise[int((t0 - g) * FS):int((t0 - g) * FS) + x.size]

    def band(v):  # whiten: pink noise's sub-Hz content would broaden the correlation peak
        V = np.fft.rfft(v)
        f = np.fft.rfftfreq(v.size, 1.0 / FS)
        return np.fft.irfft(np.where((f >= 100.0) & (f <= 2000.0), V, 0.0), v.size)

    corr = np.correlate(band(x), band(ref), mode="full")
    lag = (int(np.argmax(np.abs(corr))) - (ref.size - 1)) / FS
    expect = 1000.0 / mic.c_sound(5.0)
    assert abs(lag - expect) < 1e-3, f"delay {lag:.6f} s != {expect:.6f} s"
    tau, r, _ = mic.retarded(static_state(1000.0, 0.0, 10.0), mic_xyz,
                             np.array([3.0]), ENV["c"])
    assert abs((3.0 - tau[0]) - r[0] / ENV["c"]) < 1e-9 and abs(r[0] - 1000.0) < 0.1
    print(f"ok delay: {lag:.6f} s vs 1000/c = {expect:.6f} s")


def test_doppler():
    spec = mic.source_spec(SOUND, np.random.default_rng(1), 5.0, 80.0)
    mic_xyz = np.array([0.0, 0.0, 3.0])
    moving = lambda t: np.stack([1500.0 - 50.0 * np.asarray(t, float),
                                 np.zeros_like(np.asarray(t, float)),
                                 np.full_like(np.asarray(t, float), 10.0)], -1)
    x = mic.render_source(FlatWorld(), ENV, mic_xyz, moving, spec, 0.0, 2.0, FS,
                          np.random.default_rng(2), tones=True, broadband=False)
    seg = x[8000:24000] * np.hanning(16000)
    spec_f = np.abs(np.fft.rfft(seg)) ** 2
    f = np.fft.rfftfreq(16000, 1.0 / FS)
    near = (f > 450.0) & (f < 600.0)
    b = int(np.argmax(np.where(near, spec_f, -np.inf)))
    a, bb, c3 = spec_f[b - 1], spec_f[b], spec_f[b + 1]
    den = a - 2 * bb + c3
    f_peak = f[b] + (0.5 * (a - c3) / den * (f[1] - f[0]) if abs(den) > 1e-30 else 0.0)
    expect = SOUND["f0_hz"] * ENV["c"] / (ENV["c"] - 50.0)
    assert abs(f_peak - expect) / expect < 0.01, f"Doppler {f_peak:.1f} Hz != {expect:.1f} Hz"
    print(f"ok doppler: {f_peak:.2f} Hz vs c/(c-v) = {expect:.2f} Hz")


def test_wall():
    spec = mic.source_spec(SOUND, np.random.default_rng(1), 5.0, 80.0)
    mic_xyz = np.array([0.0, 0.0, 3.0])
    src = static_state(800.0, 0.0, 20.0)
    flat = mic.render_source(FlatWorld(), ENV, mic_xyz, src, spec, 0.0, 3.0, FS,
                             np.random.default_rng(2))
    wall = mic.render_source(WallWorld(), ENV, mic_xyz, src, spec, 0.0, 3.0, FS,
                             np.random.default_rng(2))
    drop = 20 * np.log10(np.sqrt((flat ** 2).mean()) / np.sqrt((wall ** 2).mean()))
    assert drop >= 10.0, f"screening only {drop:.1f} dB"
    loss, los = mic.screen_loss_db(WallWorld(), np.array([[800.0, 0.0, 20.0]]), mic_xyz,
                                   ENV["c"], [450.0])
    assert not los[0] and loss[0, 0] >= 10.0
    print(f"ok wall: screened {drop:.1f} dB quieter (Maekawa {loss[0, 0]:.1f} dB)")


def test_levels():
    a = mic.iso9613_alpha_db_per_km(1000.0, 20.0, 50.0)
    assert 3.0 <= a <= 6.0, f"ISO 9613-1 alpha(1 kHz, 20C, 50%) = {a:.2f} dB/km"
    s0 = mic.ambient_s0(FS, 35.0)
    x = mic.render_ambient(np.random.default_rng(3), 60 * FS, FS, s0, 0.0)
    level = mic.measure_dba(x, FS)
    assert 33.0 <= level <= 37.0, f"ambient renders at {level:.1f} dBA, want 35 +- gusts"
    print(f"ok levels: alpha(1 kHz) = {a:.2f} dB/km, ambient at {level:.1f} dBA")


def test_tone_tracker():
    """A drifting tone 4 dB below the per-bin noise floor is only detectable via integration."""
    params = dict(mic.DEFAULTS, int_s=30.0)
    rng = np.random.default_rng(4)
    s0 = mic.ambient_s0(FS, params["ambient_dba"])
    n = 40 * FS
    t = np.arange(n) / FS
    n0 = s0 / SOUND["f0_hz"]                       # per-Hz ambient at f0
    power = n0 * 10 ** (-4.0 / 10.0)               # 4 dB below the per-bin floor of a 1 s frame
    phase = 2 * np.pi * (SOUND["f0_hz"] * t + 0.5 * 0.1 * t ** 2)   # drift 0.1 Hz/s
    x = np.sqrt(2 * power) * np.sin(phase) + mic.pink_noise(rng, n, FS, s0)
    classes = [dict(f0=SOUND["f0_hz"], ks=np.arange(1, 11), vmax=25.0, family="FPV")]
    dets = mic.detect(x, FS, 0.0, params, classes, np.random.default_rng(5))
    assert dets, "drifting sub-noise tone was not detected"
    best = max(d["snr_db"] for d in dets)
    assert best > params["detect_snr_db"], f"best snr_db {best}"
    assert all(d["family"] == "FPV" or d["conf"] < 0.5 for d in dets)
    noise_only = mic.pink_noise(np.random.default_rng(6), n, FS, s0)
    fa = mic.detect(noise_only, FS, 0.0, params, classes, np.random.default_rng(7))
    assert len(fa) <= 2, f"{len(fa)} false alarms on pure ambient"
    print(f"ok tone tracker: snr_db {best} on a -4 dB/frame tone; {len(fa)} false alarms")


def test_wav_bwf(tmp="test_out.wav"):
    x = (np.sin(2 * np.pi * 440 * np.arange(3200) / FS) * 8000).astype("<i2")
    mic.write_wav_bwf(tmp, x, FS, 123456789, "TEST 2026-11-04T00:00:00.000Z")
    with wave.open(tmp, "rb") as w:
        assert w.getframerate() == FS and w.getnframes() == x.size and w.getsampwidth() == 2
        back = np.frombuffer(w.readframes(w.getnframes()), "<i2")
    assert (back == x).all()
    raw = Path(tmp).read_bytes()
    i = raw.index(b"bext") + 4
    size = struct.unpack("<I", raw[i:i + 4])[0]
    payload = raw[i + 4:i + 4 + size]
    t_ref = struct.unpack("<Q", payload[338:346])[0]
    assert t_ref == 123456789, f"bext time reference {t_ref}"
    Path(tmp).unlink()
    print("ok wav: samples + bext time reference round-trip")


if __name__ == "__main__":
    test_delay()
    test_doppler()
    test_wall()
    test_levels()
    test_tone_tracker()
    test_wav_bwf()
    print("all microphone self-checks passed")
