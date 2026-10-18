# Log book: 49.375N_31.188E-lost-contact-s1

49.3754° N · 31.1882° E · 10 km square · 04 Nov 2026 14:01:00 UTC · 20 min · seed 1

Weather: wind from 145° at 1.6 m/s, 7 °C, visibility 12.8 km.

## Cast

| id | type | side | where |
|---|---|---|---|
| SITE-01 | site | friendly | 49.4177° N · 31.2216° E |
| ADT-01 | ad_team | friendly | 49.4177° N · 31.2402° E |
| ADB-01 | ad_battery | friendly | 49.4071° N · 31.2065° E |
| mavic_1 | dji_mavic3 | hostile | moves: 9 waypoints |
| op_mavic_1 | operator | hostile | 49.3728° N · 31.1338° E |
| fiber_1 | fpv_fiber | hostile | moves: 5 waypoints |
| wifi_1 | wifi_ap | neutral | 49.4177° N · 31.2531° E |
| geese_1 | geese | neutral | moves: 2 waypoints |
| jammer_1 | jammer | friendly | 49.3655° N · 31.1274° E |

**Sensors:** RF-01 (rf_df), RF-02 (rf_df), RF-03 (rf_df), RADAR-01 (radar), CAM-01 (camera), ACOUSTIC-01 (microphone), ACOUSTIC-02 (microphone), RID-01 (remote_id), C2-01 (c2)

## Timeline

TRUTH is what happened. SENSOR is the first record each sensor made of each object. C2 is what the command post concluded from sensor data alone (73 routine new-track notices are left out).

| UTC | T+ | voice | event |
|---|---|---|---|
| 14:01:00 |     0.0 s | SENSOR | RF-01 first records **wifi_1** (389 records in all) |
| 14:01:01 |     1.0 s | SENSOR | RF-03 first records **wifi_1** (476 records in all) |
| 14:01:28 |    28.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000000 at 1871 m |
| 14:01:28 |    28.0 s | C2 | ADT-01 → alerted (first warn alert ALT-000001) |
| 14:01:28 |    28.0 s | C2 | ADT-01 → responding (dispatched on ALT-000001) |
| 14:01:28 |    28.0 s | C2 | ADB-01 → alerted (first warn alert ALT-000001) |
| 14:01:28 |    28.0 s | C2 | ADB-01 → responding (dispatched on ALT-000001) |
| 14:02:24 |    84.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000001 at 2199 m |
| 14:02:46 |   106.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000002 at 2063 m |
| 14:02:55 |   115.0 s | C2 | WARN: LOST CONTACT TRK-000000: no update for 60 s |
| 14:03:28 |   148.0 s | C2 | WARN: LOST CONTACT TRK-000001: no update for 60 s |
| 14:04:39 |   219.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000003 at 2344 m |
| 14:05:16 |   256.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000004 at 2090 m |
| 14:05:17 |   257.0 s | C2 | WARN: LOST CONTACT TRK-000002: no update for 60 s |
| 14:05:42 |   282.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000005 at 2276 m |
| 14:06:06 |   306.0 s | TRUTH | **fiber_1** (fpv_fiber, hostile) airborne |
| 14:06:18 |   318.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000006 at 1959 m |
| 14:06:25 |   325.0 s | SENSOR | ACOUSTIC-02 first records **fiber_1** (4 records in all) |
| 14:06:57 |   357.0 s | C2 | WARN: LOST CONTACT TRK-000005: no update for 60 s |
| 14:07:00 |   360.0 s | SENSOR | RADAR-01 first records **fiber_1** (1 records in all) |
| 14:07:11 |   371.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000007 at 2189 m |
| 14:08:12 |   432.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000008 at 2298 m |
| 14:08:30 |   450.0 s | C2 | WARN: LOST CONTACT TRK-000007: no update for 60 s |
| 14:08:43 |   463.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000009 at 1989 m |
| 14:09:11 |   491.7 s | TRUTH | **jammer_1** on |
| 14:09:12 |   492.0 s | SENSOR | RF-01 first records **jammer_1** (197 records in all) |
| 14:09:12 |   492.0 s | SENSOR | RF-03 first records **jammer_1** (132 records in all) |
| 14:09:12 |   492.0 s | SENSOR | RF-02 first records **jammer_1** (197 records in all) |
| 14:09:25 |   505.5 s | TRUTH | **fiber_1** reaches SITE-01 (0.3 m) |
| 14:09:27 |   507.5 s | TRUTH | **geese_1** (geese, neutral) airborne |
| 14:09:36 |   516.5 s | TRUTH | **mavic_1** (dji_mavic3, hostile) airborne |
| 14:09:37 |   517.0 s | SENSOR | RID-01 first records **mavic_1** (607 records in all) |
| 14:09:39 |   519.0 s | SENSOR | RF-03 first records **op_mavic_1** (432 records in all) |
| 14:09:40 |   520.0 s | SENSOR | RF-03 first records **mavic_1** (660 records in all) |
| 14:09:45 |   525.0 s | SENSOR | RADAR-01 first records **geese_1** (325 records in all) |
| 14:10:41 |   581.0 s | SENSOR | ACOUSTIC-02 first records **geese_1** (364 records in all) |
| 14:11:07 |   607.0 s | SENSOR | ACOUSTIC-01 first records **mavic_1** (76 records in all) |
| 14:12:28 |   688.1 s | TRUTH | **jammer_1** off |
| 14:12:29 |   689.0 s | SENSOR | RF-02 first records **op_mavic_1** (469 records in all) |
| 14:12:29 |   689.0 s | SENSOR | RF-01 first records **mavic_1** (511 records in all) |
| 14:12:29 |   689.0 s | SENSOR | RF-01 first records **op_mavic_1** (480 records in all) |
| 14:12:29 |   689.0 s | SENSOR | RF-02 first records **mavic_1** (511 records in all) |
| 14:12:34 |   694.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000020 at 2090 m |
| 14:12:55 |   715.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000023 at 2285 m |
| 14:13:25 |   745.0 s | SENSOR | RADAR-01 first records **mavic_1** (86 records in all) |
| 14:14:09 |   789.0 s | C2 | WARN: LOST CONTACT TRK-000018: no update for 60 s |
| 14:14:15 |   795.0 s | SENSOR | ACOUSTIC-01 first records **geese_1** (277 records in all) |
| 14:14:23 |   803.0 s | C2 | WARN: LOST CONTACT TRK-000010: no update for 60 s |
| 14:14:39 |   819.0 s | C2 | WARN: LOST CONTACT TRK-000023: no update for 60 s |
| 14:14:40 |   820.0 s | C2 | WARN: LOST CONTACT TRK-000027: no update for 60 s |
| 14:14:50 |   830.0 s | C2 | WARN: LOST CONTACT TRK-000022: no update for 60 s |
| 14:15:04 |   844.0 s | C2 | WARN: LOST CONTACT TRK-000019: no update for 60 s |
| 14:15:07 |   847.0 s | C2 | WARN: LOST CONTACT TRK-000021: no update for 60 s |
| 14:15:25 |   865.0 s | C2 | WARN: LOST CONTACT TRK-000031: no update for 60 s |
| 14:15:30 |   870.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000039 at 2049 m |
| 14:15:53 |   893.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000045 at 2094 m |
| 14:16:10 |   910.0 s | C2 | WARN: LOST CONTACT TRK-000034: no update for 60 s |
| 14:16:31 |   931.0 s | C2 | WARN: LOST CONTACT TRK-000037: no update for 60 s |
| 14:16:47 |   947.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000048 at 2222 m |
| 14:17:01 |   961.0 s | C2 | WARN: LOST CONTACT TRK-000028: no update for 60 s |
| 14:17:12 |   972.0 s | C2 | WARN: LOST CONTACT TRK-000029: no update for 60 s |
| 14:17:18 |   978.0 s | C2 | WARN: LOST CONTACT TRK-000045: no update for 60 s |
| 14:17:21 |   981.0 s | C2 | WARN: LOST CONTACT TRK-000044: no update for 60 s |
| 14:17:29 |   989.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000052 at 2400 m |
| 14:18:14 |  1034.0 s | C2 | WARN: LOST CONTACT TRK-000030: no update for 60 s |
| 14:18:22 |  1042.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000059 at 2324 m |
| 14:18:44 |  1064.0 s | C2 | WARN: LOST CONTACT TRK-000051: no update for 60 s |
| 14:18:49 |  1069.0 s | C2 | WARN: LOST CONTACT TRK-000033: no update for 60 s |
| 14:18:49 |  1069.0 s | C2 | WARN: LOST CONTACT TRK-000052: no update for 60 s |
| 14:19:07 |  1087.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000062 at 2150 m |
| 14:19:39 |  1119.0 s | C2 | WARN: LOST CONTACT TRK-000049: no update for 60 s |
| 14:19:47 |  1127.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000064 at 2097 m |
| 14:19:47 |  1127.0 s | SENSOR | ACOUSTIC-02 first records **mavic_1** (2 records in all) |
| 14:19:53 |  1133.0 s | C2 | WARN: LOST CONTACT TRK-000047: no update for 60 s |
| 14:20:19 |  1159.0 s | C2 | WARN: LOST CONTACT TRK-000063: no update for 60 s |
| 14:20:23 |  1163.0 s | C2 | WARN: LOST CONTACT TRK-000062: no update for 60 s |
| 14:20:40 |  1180.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000070 at 2480 m |
| 14:20:52 |  1192.0 s | C2 | WARN: SENSOR SILENT ACOUSTIC-02: no detections since 2026-11-04T14:19:52.000Z (ACOUSTIC-01, CAM-01, RADAR-01, RF-01, RF-02, RF-03, RID-01 still reporting) |
| 14:20:53 |  1193.0 s | C2 | WARN: LOST CONTACT TRK-000056: no update for 60 s |
| 14:20:59 |  1199.5 s | C2 | ADT-01 → no contact (no C2 track within 500 m at its end) |
| 14:20:59 |  1199.5 s | C2 | ADB-01 → no contact (no C2 track within 500 m at its end) |
| 14:21:00 |  1200.0 s | C2 | SITE-01 → not reached (no confirmed track within 1 km) |

## Outcome per hostile

| hostile | airborne | first sensor record | first C2 alert | truth outcome |
|---|---|---|---|---|
| mavic_1 | 14:09:36 | 14:09:37 (+1 s) | 14:12:29 (+172 s) | not reached |
| fiber_1 | 14:06:06 | 14:06:25 (+19 s) | none | reached |

## Audit (independent physics checks)

**6 pass · 2 fail · 2 skip**

| check | status | value |
|---|---|---|
| Provenance | PASS | 0 |
| Clock sync | PASS | 0 |
| Bearing geometry | PASS | 0.9401 |
| Terrain shadow | FAIL | 9.22 |
| Occlusion gaps | SKIP | — |
| Fix calibration | PASS | 0.4377 |
| Range law | FAIL | 0.847 |
| Acoustic delay | PASS | 0.0022 |
| Spoof visibility | SKIP | — |
| Cross-sensor time | PASS | 1.0 |
