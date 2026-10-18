# Audit — 49.375N_31.188E-intercepted-s1

Independent checks: geometry from `truth/tracks.csv` + `sensors/*/site.json` and the real DEM
(`World.los`), causality and statistics. The answer key's derived columns are never trusted.

| id | check | status | value | threshold | detail |
|---|---|---|---|---|---|
| provenance | Provenance | PASS | 0 | 0 issues | clean |
| clock | Clock sync | PASS | 0 | 0 problems; abs(time_utc − (start+t)) ≤ 1 ms | 21651 rows, max \|time_utc − (start+t)\| = 0.477 ms |
| bearing_geometry | Bearing geometry | PASS | 0.9304 | ≥ 0.85 of LOS within 2σ | RF-01: bias +0.07°, within 2σ 0.930 (n=1051, n_los=962); RF-02: bias +1.05°, within 2σ 0.952 (n=455, n_los=455); RF-03: bias -0.91°, within 2σ 0.949 (n=1011, n_los=1011) |
| terrain_shadow | Terrain shadow | PASS | 24.46 | NLOS − LOS median excess ≥ 10 dB | RF-01: excess LOS -5.4 dB (n=962) vs NLOS 19.1 dB (n=89), Δ=24.5 dB |
| occlusion_gaps | Occlusion gaps | SKIP | — | < 0.5 | no sensor/drone pair with NLOS intervals ≥ 30 s |
| fix_calibration | Fix calibration | PASS | 0.4888 | share(error < cep50_m) in [0.35, 0.65] | n=534, median error 206 m, median cep50 183 m |
| range_law | Range law | FAIL | 8.757 | path-loss exponent in [1.5, 4.5] (free space 2) | RF-01: exponent 2.90 (n=962); RF-02: exponent 8.76 (n=455); RF-03: exponent 1.07 (n=1011) |
| acoustic_delay | Acoustic delay | PASS | 0.0176 | max \|Δdelay\|/delay ≤ 2%, no arrival before emission | max relative delay error 1.76%, 0 causality violations |
| spoof_visible | Spoof visibility | SKIP | — | large error only inside spoof windows | no GNSS spoofing in scenario |
| cross_sensor_time | Cross-sensor time | PASS | 1 | every frame within 5 s of a fix | 603 frames, 0 without a fix within 5 s |

**7 pass, 1 fail, 2 skip.**
