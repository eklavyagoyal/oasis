# Audit — 05-lost-contact-hospital

Independent checks: geometry from `truth/tracks.csv` + `sensors/*/site.json` and the real DEM
(`World.los`), causality and statistics. The answer key's derived columns are never trusted.

| id | check | status | value | threshold | detail |
|---|---|---|---|---|---|
| provenance | Provenance | PASS | 0 | 0 issues | clean |
| clock | Clock sync | PASS | 0 | 0 problems; abs(time_utc − (start+t)) ≤ 1 ms | 22078 rows, max \|time_utc − (start+t)\| = 0.481 ms |
| bearing_geometry | Bearing geometry | PASS | 0.9369 | ≥ 0.85 of LOS within 2σ | RF-01: bias -0.44°, within 2σ 0.940 (n=2186, n_los=2186); RF-02: bias +0.06°, within 2σ 0.947 (n=1953, n_los=1953); RF-03: bias +0.36°, within 2σ 0.937 (n=1139, n_los=1125) |
| terrain_shadow | Terrain shadow | SKIP | — | ≥ 10 dB | no sensor with ≥ 20 LOS and ≥ 20 NLOS detections with power + geometry |
| occlusion_gaps | Occlusion gaps | PASS | 0 | rate_in / rate_out < 0.5 | RF-01/fiber_1: 1 interval(s) 40s, 0 det in vs 0 out, ratio n/a; RF-02/mavic_1: 2 interval(s) 153s, 0 det in vs 864 out, ratio 0.000; RF-02/fiber_1: 1 interval(s) 54s, 0 det in vs 0 out, ratio n/a; RF-03/fiber_1: 1 interval(s) 188s, 0 det in vs 0 out, ratio n/a |
| fix_calibration | Fix calibration | PASS | 0.5076 | share(error < cep50_m) in [0.35, 0.65] | n=589, median error 266 m, median cep50 303 m |
| range_law | Range law | PASS | 2.646 | path-loss exponent in [1.5, 4.5] (free space 2) | RF-01: exponent 2.65 (n=2186); RF-02: exponent 2.14 (n=1953); RF-03: exponent 1.95 (n=1125) |
| acoustic_delay | Acoustic delay | SKIP | — | ≤ 2% | no microphone in scenario |
| spoof_visible | Spoof visibility | SKIP | — | large error only inside spoof windows | no GNSS spoofing in scenario |
| cross_sensor_time | Cross-sensor time | PASS | 1 | every frame within 5 s of a fix | 61 frames, 0 without a fix within 5 s |

**7 pass, 0 fail, 3 skip.**
