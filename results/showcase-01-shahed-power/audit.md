# Audit — 01-shahed-power

Independent checks: geometry from `truth/tracks.csv` + `sensors/*/site.json` and the real DEM
(`World.los`), causality and statistics. The answer key's derived columns are never trusted.

| id | check | status | value | threshold | detail |
|---|---|---|---|---|---|
| provenance | Provenance | PASS | 0 | 0 issues | clean |
| clock | Clock sync | PASS | 0 | 0 problems; abs(time_utc − (start+t)) ≤ 1 ms | 9342 rows, max \|time_utc − (start+t)\| = 0.472 ms |
| bearing_geometry | Bearing geometry | PASS | 0.9362 | ≥ 0.85 of LOS within 2σ | RF-01: bias -0.87°, within 2σ 0.953 (n=110, n_los=64); RF-02: bias +0.24°, within 2σ 0.936 (n=47, n_los=47) |
| terrain_shadow | Terrain shadow | FAIL | 9.58 | NLOS − LOS median excess ≥ 10 dB | RF-01: excess LOS -3.1 dB (n=64) vs NLOS 6.5 dB (n=46), Δ=9.6 dB |
| occlusion_gaps | Occlusion gaps | SKIP | — | < 0.5 | no sensor/drone pair with NLOS intervals ≥ 30 s |
| fix_calibration | Fix calibration | FAIL | 0.9 | share(error < cep50_m) in [0.35, 0.65] | n=10, median error 434 m, median cep50 1020 m |
| range_law | Range law | FAIL | 0.317 | path-loss exponent in [1.5, 4.5] (free space 2) | RF-01: exponent 0.32 (n=64); RF-02: exponent 3.50 (n=47) |
| acoustic_delay | Acoustic delay | SKIP | — | ≤ 2% | no microphone in scenario |
| spoof_visible | Spoof visibility | SKIP | — | large error only inside spoof windows | no remote_id/telemetry in scenario |
| cross_sensor_time | Cross-sensor time | PASS | 1 | every frame within 5 s of a fix | 27 frames, 0 without a fix within 5 s |

**4 pass, 3 fail, 3 skip.**
