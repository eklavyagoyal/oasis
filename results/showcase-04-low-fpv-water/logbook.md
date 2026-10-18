# Log book: 04-low-fpv-water

49.3754° N · 31.1882° E · 10 km square · 04 Nov 2026 14:01:00 UTC · 20 min · seed 408

Weather: wind from 62° at 5.3 m/s, 5 °C, visibility 11.6 km.

## Cast

| id | type | side | where |
|---|---|---|---|
| SITE-01 | water_works | friendly | 49.4035° N · 31.2280° E |
| ADT-01 | ad_team | friendly | 49.3935° N · 31.2131° E |
| ADB-01 | ad_battery | friendly | 49.4085° N · 31.2496° E |
| fiber_1 | fpv_fiber | hostile | moves: 4 waypoints |
| fpv_1 | fpv_analog | hostile | moves: 5 waypoints |
| op_fpv_1 | operator | hostile | 49.4135° N · 31.1296° E |
| fiber_2 | fpv_fiber | hostile | moves: 5 waypoints |
| fpv_2 | fpv_analog | hostile | moves: 5 waypoints |
| op_fpv_2 | operator | hostile | 49.4107° N · 31.1365° E |
| INT-01 | jedi | friendly | moves: 2 waypoints |
| op_INT-01 | operator | friendly | 49.3910° N · 31.2158° E |
| INT-02 | jedi | friendly | moves: 2 waypoints |
| op_INT-02 | operator | friendly | 49.3917° N · 31.2145° E |

**Sensors:** RF-01 (rf_df), RF-02 (rf_df), RF-03 (rf_df), RADAR-01 (radar), CAM-01 (camera), RID-01 (remote_id), C2-01 (c2)

## Timeline

TRUTH is what happened. SENSOR is the first record each sensor made of each object. C2 is what the command post concluded from sensor data alone (39 routine new-track notices are left out).

| UTC | T+ | voice | event |
|---|---|---|---|
| 14:06:23 |   323.5 s | TRUTH | **fpv_1** (fpv_analog, hostile) airborne |
| 14:06:24 |   324.0 s | SENSOR | RF-01 first records **fpv_1** (277 records in all) |
| 14:06:24 |   324.0 s | SENSOR | RF-01 first records **op_fpv_1** (270 records in all) |
| 14:06:24 |   324.0 s | SENSOR | RF-02 first records **op_fpv_1** (278 records in all) |
| 14:06:24 |   324.0 s | SENSOR | RF-02 first records **fpv_1** (227 records in all) |
| 14:06:33 |   333.0 s | SENSOR | RF-03 first records **op_fpv_1** (9 records in all) |
| 14:07:43 |   403.5 s | TRUTH | **fpv_2** (fpv_analog, hostile) airborne |
| 14:07:44 |   404.0 s | SENSOR | RF-02 first records **fpv_2** (265 records in all) |
| 14:07:44 |   404.0 s | SENSOR | RF-01 first records **fpv_2** (341 records in all) |
| 14:07:44 |   404.0 s | SENSOR | RF-02 first records **op_fpv_2** (397 records in all) |
| 14:07:44 |   404.0 s | SENSOR | RF-01 first records **op_fpv_2** (397 records in all) |
| 14:07:44 |   404.0 s | SENSOR | RF-03 first records **op_fpv_2** (397 records in all) |
| 14:08:01 |   421.0 s | C2 | WARN: LOST CONTACT TRK-000002: no update for 60 s |
| 14:08:01 |   421.0 s | C2 | ADT-01 → alerted (first warn alert ALT-000005) |
| 14:08:01 |   421.0 s | C2 | ADT-01 → responding (dispatched on ALT-000005) |
| 14:08:01 |   421.0 s | C2 | ADB-01 → alerted (first warn alert ALT-000005) |
| 14:08:01 |   421.0 s | C2 | ADB-01 → responding (dispatched on ALT-000005) |
| 14:08:31 |   451.0 s | C2 | WARN: LOST CONTACT TRK-000000: no update for 60 s |
| 14:09:32 |   512.0 s | C2 | WARN: LOST CONTACT TRK-000003: no update for 60 s |
| 14:09:47 |   527.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000009 at 2905 m |
| 14:09:56 |   536.0 s | SENSOR | RF-03 first records **fpv_1** (94 records in all) |
| 14:09:57 |   537.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000001 at 2828 m |
| 14:09:57 |   537.0 s | SENSOR | RADAR-01 first records **fpv_1** (1 records in all) |
| 14:10:12 |   552.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000012 at 2649 m |
| 14:10:15 |   555.0 s | C2 | WARN: LOST CONTACT TRK-000008: no update for 60 s |
| 14:10:25 |   565.0 s | SENSOR | RADAR-01 first records **fpv_2** (2 records in all) |
| 14:10:30 |   570.0 s | SENSOR | RF-03 first records **fpv_2** (104 records in all) |
| 14:10:46 |   586.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000013 at 2850 m |
| 14:10:57 |   597.0 s | C2 | CRITICAL: CLOSE TO SITE-01: TRK-000009 at 947 m |
| 14:10:57 |   597.0 s | C2 | SITE-01 → approached (confirmed track TRK-000009 within 947 m) |
| 14:11:07 |   607.0 s | C2 | WARN: LOST CONTACT TRK-000001: no update for 60 s |
| 14:11:22 |   622.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000015 at 2788 m |
| 14:11:33 |   633.0 s | TRUTH | **fpv_1** reaches SITE-01 (9.2 m) |
| 14:12:05 |   665.0 s | C2 | WARN: LOST CONTACT TRK-000009: no update for 60 s |
| 14:12:07 |   667.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000020 at 2942 m |
| 14:12:19 |   679.0 s | TRUTH | **fiber_2** (fpv_fiber, hostile) airborne |
| 14:12:22 |   682.0 s | TRUTH | **fiber_1** (fpv_fiber, hostile) airborne |
| 14:13:03 |   723.0 s | C2 | WARN: LOST CONTACT TRK-000017: no update for 60 s |
| 14:13:06 |   726.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000022 at 2096 m |
| 14:13:09 |   729.0 s | C2 | WARN: LOST CONTACT TRK-000005: no update for 60 s |
| 14:13:27 |   747.0 s | C2 | WARN: LOST CONTACT TRK-000020: no update for 60 s |
| 14:13:35 |   755.0 s | C2 | WARN: LOST CONTACT TRK-000011: no update for 60 s |
| 14:14:11 |   791.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000030 at 289 m |
| 14:14:11 |   791.0 s | C2 | CRITICAL: CLOSE TO SITE-01: TRK-000030 at 289 m |
| 14:14:17 |   797.0 s | SENSOR | RADAR-01 first records **fiber_2** (2 records in all) |
| 14:14:20 |   800.0 s | TRUTH | **fpv_2** reaches SITE-01 (5.4 m) |
| 14:14:43 |   823.0 s | C2 | WARN: LOST CONTACT TRK-000022: no update for 60 s |
| 14:15:17 |   857.0 s | C2 | WARN: LOST CONTACT TRK-000024: no update for 60 s |
| 14:15:20 |   860.0 s | C2 | WARN: LOST CONTACT TRK-000021: no update for 60 s |
| 14:16:30 |   930.0 s | SENSOR | RADAR-01 first records **fiber_1** (28 records in all) |
| 14:17:37 |   997.5 s | TRUTH | **INT-02** (jedi, friendly) airborne |
| 14:17:38 |   998.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000031 at 2517 m |
| 14:17:38 |   998.0 s | SENSOR | RF-02 first records **op_INT-02** (57 records in all) |
| 14:17:38 |   998.0 s | SENSOR | RF-01 first records **op_INT-02** (57 records in all) |
| 14:17:38 |   998.0 s | SENSOR | RF-01 first records **INT-02** (57 records in all) |
| 14:17:38 |   998.0 s | SENSOR | RF-03 first records **op_INT-02** (57 records in all) |
| 14:17:38 |   998.0 s | SENSOR | RF-02 first records **INT-02** (38 records in all) |
| 14:17:38 |   998.0 s | SENSOR | RF-03 first records **INT-02** (38 records in all) |
| 14:17:40 |  1000.0 s | SENSOR | RADAR-01 first records **INT-02** (12 records in all) |
| 14:17:41 |  1001.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000032 at 2734 m |
| 14:17:41 |  1001.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000033 at 1439 m |
| 14:17:45 |  1005.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000034 at 1635 m |
| 14:18:10 |  1030.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000035 at 2628 m |
| 14:18:18 |  1038.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000036 at 1479 m |
| 14:18:34 |  1054.0 s | TRUTH | **INT-02** track ends |
| 14:18:34 |  1054.5 s | TRUTH | **fiber_2** track ends |
| 14:18:51 |  1071.5 s | TRUTH | **INT-01** (jedi, friendly) airborne |
| 14:18:52 |  1072.0 s | SENSOR | RF-03 first records **op_INT-01** (22 records in all) |
| 14:18:52 |  1072.0 s | SENSOR | RF-02 first records **INT-01** (13 records in all) |
| 14:18:52 |  1072.0 s | SENSOR | RF-02 first records **op_INT-01** (22 records in all) |
| 14:18:52 |  1072.0 s | SENSOR | RF-01 first records **op_INT-01** (22 records in all) |
| 14:18:52 |  1072.0 s | SENSOR | RF-01 first records **INT-01** (22 records in all) |
| 14:18:52 |  1072.0 s | SENSOR | RF-03 first records **INT-01** (21 records in all) |
| 14:18:55 |  1075.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000037 at 2041 m |
| 14:18:55 |  1075.0 s | SENSOR | RADAR-01 first records **INT-01** (8 records in all) |
| 14:19:09 |  1089.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000038 at 1548 m |
| 14:19:13 |  1093.5 s | TRUTH | **fiber_1** track ends |
| 14:19:13 |  1093.5 s | TRUTH | **INT-01** track ends |
| 14:19:19 |  1099.0 s | C2 | WARN: LOST CONTACT TRK-000032: no update for 60 s |
| 14:19:20 |  1100.0 s | C2 | WARN: LOST CONTACT TRK-000031: no update for 60 s |
| 14:19:52 |  1132.0 s | C2 | WARN: LOST CONTACT TRK-000036: no update for 60 s |
| 14:19:58 |  1138.0 s | C2 | WARN: LOST CONTACT TRK-000035: no update for 60 s |
| 14:20:08 |  1148.0 s | C2 | WARN: LOST CONTACT TRK-000037: no update for 60 s |
| 14:20:12 |  1152.0 s | C2 | WARN: LOST CONTACT TRK-000033: no update for 60 s |
| 14:20:13 |  1153.0 s | C2 | WARN: LOST CONTACT TRK-000038: no update for 60 s |
| 14:20:13 |  1153.0 s | C2 | WARN: SENSOR SILENT RF-01: no detections since 2026-11-04T14:19:13.000Z (CAM-01, RADAR-01 still reporting) |
| 14:20:13 |  1153.0 s | C2 | WARN: SENSOR SILENT RF-02: no detections since 2026-11-04T14:19:13.000Z (CAM-01, RADAR-01 still reporting) |
| 14:20:18 |  1158.0 s | C2 | WARN: SENSOR SILENT CAM-01: no detections since 2026-11-04T14:19:18.000Z (RADAR-01, RF-03 still reporting) |
| 14:20:59 |  1199.5 s | C2 | ADT-01 → no contact (no C2 track within 500 m at its end) |
| 14:20:59 |  1199.5 s | C2 | ADB-01 → no contact (no C2 track within 500 m at its end) |

## Outcome per hostile

| hostile | airborne | first sensor record | first C2 alert | truth outcome |
|---|---|---|---|---|
| fiber_1 | 14:12:22 | 14:16:30 (+248 s) | none | not reached |
| fpv_1 | 14:06:23 | 14:06:24 (+0 s) | 14:06:58 (+34 s) | reached |
| fiber_2 | 14:12:19 | 14:14:17 (+118 s) | none | not reached |
| fpv_2 | 14:07:43 | 14:07:44 (+0 s) | 14:08:07 (+24 s) | reached |

## Audit (independent physics checks)

**7 pass · 1 fail · 2 skip**

| check | status | value |
|---|---|---|
| Provenance | PASS | 0 |
| Clock sync | PASS | 0 |
| Bearing geometry | PASS | 0.9404 |
| Terrain shadow | PASS | 19.85 |
| Occlusion gaps | PASS | 0.1879 |
| Fix calibration | PASS | 0.4257 |
| Range law | FAIL | -0.409 |
| Acoustic delay | SKIP | — |
| Spoof visibility | SKIP | — |
| Cross-sensor time | PASS | 1.0 |
