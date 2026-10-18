# Audit — 04-low-fpv-water

Independent checks: geometry from `truth/tracks.csv` + `sensors/*/site.json` and the real DEM
(`World.los`), causality and statistics. The answer key's derived columns are never trusted.

| id | check | status | value | threshold | detail |
|---|---|---|---|---|---|
| provenance | Provenance | PASS | 0 | 0 issues | clean |
| clock | Clock sync | PASS | 0 | 0 problems; abs(time_utc − (start+t)) ≤ 1 ms | 17350 rows, max \|time_utc − (start+t)\| = 0.469 ms |
| bearing_geometry | Bearing geometry | PASS | 0.9404 | ≥ 0.85 of LOS within 2σ | RF-01: bias -0.12°, within 2σ 0.946 (n=1443, n_los=1167); RF-02: bias -0.11°, within 2σ 0.940 (n=1297, n_los=940); RF-03: bias -0.25°, within 2σ 0.964 (n=742, n_los=335) |
| terrain_shadow | Terrain shadow | PASS | 19.85 | NLOS − LOS median excess ≥ 10 dB | RF-01: excess LOS -3.9 dB (n=1167) vs NLOS 22.5 dB (n=276), Δ=26.3 dB; RF-02: excess LOS 0.5 dB (n=940) vs NLOS 24.4 dB (n=357), Δ=23.9 dB; RF-03: excess LOS -2.0 dB (n=335) vs NLOS 17.9 dB (n=407), Δ=19.9 dB |
| occlusion_gaps | Occlusion gaps | PASS | 0.1879 | rate_in / rate_out < 0.5 | RF-01/fpv_2: 1 interval(s) 34s, 6 det in vs 335 out, ratio 0.188; RF-02/fpv_1: 1 interval(s) 78s, 0 det in vs 227 out, ratio 0.000; RF-02/fpv_2: 1 interval(s) 95s, 0 det in vs 265 out, ratio 0.000; RF-03/fiber_1: 1 interval(s) 327s, 0 det in vs 0 out, ratio n/a; RF-03/fpv_1: 1 interval(s) 206s, 0 det in vs 94 out, ratio 0.000; RF-03/fiber_2: 2 interval(s) 364s, 0 det in vs 0 out, ratio n/a; RF-03/fpv_2: 2 interval(s) 282s, 0 det in vs 104 out, ratio 0.000 |
| fix_calibration | Fix calibration | PASS | 0.4257 | share(error < cep50_m) in [0.35, 0.65] | n=606, median error 258 m, median cep50 239 m |
| range_law | Range law | FAIL | -0.409 | path-loss exponent in [1.5, 4.5] (free space 2) | RF-01: exponent -0.41 (n=1167); RF-02: exponent 2.87 (n=940); RF-03: exponent 3.71 (n=335) |
| acoustic_delay | Acoustic delay | SKIP | — | ≤ 2% | no microphone in scenario |
| spoof_visible | Spoof visibility | SKIP | — | large error only inside spoof windows | no GNSS spoofing in scenario |
| cross_sensor_time | Cross-sensor time | PASS | 1 | every frame within 5 s of a fix | 60 frames, 0 without a fix within 5 s |

**7 pass, 1 fail, 2 skip.**
