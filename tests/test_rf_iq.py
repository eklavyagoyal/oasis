"""rf_iq self-check: plain asserts, run with `uv run python tests/test_rf_iq.py`."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mirrorworld.sensors import rf_iq  # noqa: E402

FS, CENTER, NF = 30.72e6, 2440.0, 6.0
NOISE_FLOOR_DBM = -174.0 + 10 * np.log10(FS) + NF


def recovered(iq, fs_dbm):
    """Snapshot IQ in sqrt(mW) from the quantised ci16 using the recorded full-scale dBm."""
    return (iq[:, 0].astype(np.float64) + 1j * iq[:, 1]) / 32767.0 * 10 ** (fs_dbm / 20)


def inband_power_dbm(x, f_lo_off_hz, f_hi_off_hz):
    """Power in the bins between two baseband offsets (relative to the capture centre)."""
    f = np.fft.fftfreq(x.size, 1 / FS)
    X = np.fft.fft(x)
    m = (f >= f_lo_off_hz) & (f <= f_hi_off_hz)
    return 10 * np.log10((np.abs(X[m]) ** 2).sum() / x.size ** 2)


# --- noise-only snapshot: total power matches kTB + NF within 1 dB -------
x, noise_dbm, ann = rf_iq.synthesise_snapshot(np.random.default_rng(1), CENTER, FS, 2e-3, [], NF)
assert not ann, "no bursts without emitters"
assert abs(noise_dbm - NOISE_FLOOR_DBM) < 1e-9
iq, fs_dbm = rf_iq.quantise(x)
p_dbm = 10 * np.log10(np.mean(np.abs(recovered(iq, fs_dbm)) ** 2))
assert abs(p_dbm - NOISE_FLOOR_DBM) <= 1.0, f"noise-only {p_dbm:.2f} dBm, want {NOISE_FLOOR_DBM:.2f} dBm"

# --- one emitter at known P_rx, high SNR: in-band power within 1.5 dB ----
P_RX_DBM = -20.0
em = {"id": "uav:jam", "tx_obj": "uav", "sig_class": "Wideband noise", "duty": 1.0,
      "bw_mhz": 5.0, "band_mhz": (2400.0, 2500.0), "f0": 2443.0, "hop": False, "p_rx_dbm": P_RX_DBM}
x, noise_dbm, ann = rf_iq.synthesise_snapshot(np.random.default_rng(2), CENTER, FS, 2e-3, [em], NF)
assert len(ann) == 1 and ann[0]["mirror:object_id"] == "uav"
iq, fs_dbm = rf_iq.quantise(x)
p_dbm = inband_power_dbm(recovered(iq, fs_dbm), 0.5e6, 5.5e6)  # the emitter's 5 MHz at +3 MHz
assert abs(p_dbm - P_RX_DBM) <= 1.5, f"in-band {p_dbm:.2f} dBm, want {P_RX_DBM:.2f} dBm"

print("all rf_iq tests passed")
