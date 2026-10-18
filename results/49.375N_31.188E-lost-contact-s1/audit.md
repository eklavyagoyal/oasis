# Audit — 49.375N_31.188E-lost-contact-s1

Independent checks: geometry from `truth/tracks.csv` + `sensors/*/site.json` and the real DEM
(`World.los`), causality and statistics. The answer key's derived columns are never trusted.

| id | check | status | value | threshold | detail |
|---|---|---|---|---|---|
| provenance | Provenance | PASS | 0 | 0 issues | clean |
| clock | Clock sync | PASS | 0 | 0 problems; abs(time_utc − (start+t)) ≤ 1 ms | 24901 rows, max \|time_utc − (start+t)\| = 0.489 ms |
| bearing_geometry | Bearing geometry | PASS | 0.9401 | ≥ 0.85 of LOS within 2σ | RF-01: bias +0.01°, within 2σ 0.952 (n=1577, n_los=1577); RF-02: bias +0.76°, within 2σ 0.942 (n=1177, n_los=708); RF-03: bias -0.72°, within 2σ 0.940 (n=1700, n_los=1136) |
| terrain_shadow | Terrain shadow | FAIL | 9.22 | NLOS − LOS median excess ≥ 10 dB | RF-02: excess LOS -4.6 dB (n=708) vs NLOS 21.1 dB (n=469), Δ=25.7 dB; RF-03: excess LOS -2.7 dB (n=1136) vs NLOS 6.5 dB (n=564), Δ=9.2 dB |
| occlusion_gaps | Occlusion gaps | SKIP | — | < 0.5 | only pairs with no detections at all; RF-02/fiber_1: 1 interval(s) 172s, 0 det in vs 0 out, ratio n/a |
| fix_calibration | Fix calibration | PASS | 0.4377 | share(error < cep50_m) in [0.35, 0.65] | n=827, median error 301 m, median cep50 257 m |
| range_law | Range law | FAIL | 0.847 | path-loss exponent in [1.5, 4.5] (free space 2) | RF-01: exponent 0.85 (n=1577); RF-02: exponent 2.24 (n=708); RF-03: exponent 2.31 (n=1136) |
| acoustic_delay | Acoustic delay | PASS | 0.0022 | max \|Δdelay\|/delay ≤ 2%, no arrival before emission | max relative delay error 0.22%, 0 causality violations |
| spoof_visible | Spoof visibility | SKIP | — | large error only inside spoof windows | no GNSS spoofing in scenario |
| cross_sensor_time | Cross-sensor time | PASS | 1 | every frame within 5 s of a fix | 609 frames, 0 without a fix within 5 s |

**6 pass, 2 fail, 2 skip.**
