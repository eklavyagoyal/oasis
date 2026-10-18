# Log book: 49.375N_31.188E-recon-strike-s1

49.3754° N · 31.1882° E · 10 km square · 04 Nov 2026 14:01:00 UTC · 20 min · seed 1

Weather: wind from 145° at 1.6 m/s, 7 °C, visibility 12.8 km.

## Cast

| id | type | side | where |
|---|---|---|---|
| SITE-01 | site | friendly | 49.4177° N · 31.2216° E |
| ADT-01 | ad_team | friendly | 49.4177° N · 31.2402° E |
| ADB-01 | ad_battery | friendly | 49.4071° N · 31.2065° E |
| orlan_1 | orlan10 | hostile | moves: 6 waypoints |
| lancet_1 | lancet | hostile | moves: 4 waypoints |
| wifi_1 | wifi_ap | neutral | 49.4177° N · 31.2531° E |
| geese_1 | geese | neutral | moves: 2 waypoints |

**Sensors:** RF-01 (rf_df), RF-02 (rf_df), RF-03 (rf_df), RADAR-01 (radar), CAM-01 (camera), ACOUSTIC-01 (microphone), ACOUSTIC-02 (microphone), RID-01 (remote_id), C2-01 (c2)

## Timeline

TRUTH is what happened. SENSOR is the first record each sensor made of each object. C2 is what the command post concluded from sensor data alone (40 routine new-track notices are left out).

| UTC | T+ | voice | event |
|---|---|---|---|
| 14:01:02 |     2.0 s | SENSOR | RF-03 first records **wifi_1** (471 records in all) |
| 14:01:03 |     3.0 s | SENSOR | RF-01 first records **wifi_1** (490 records in all) |
| 14:01:10 |    10.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000000 at 2125 m |
| 14:01:10 |    10.0 s | C2 | ADT-01 → alerted (first warn alert ALT-000001) |
| 14:01:10 |    10.0 s | C2 | ADT-01 → responding (dispatched on ALT-000001) |
| 14:01:10 |    10.0 s | C2 | ADB-01 → alerted (first warn alert ALT-000001) |
| 14:01:10 |    10.0 s | C2 | ADB-01 → responding (dispatched on ALT-000001) |
| 14:01:53 |    53.0 s | SENSOR | RF-01 first records **orlan_1** (402 records in all) |
| 14:01:53 |    53.0 s | SENSOR | RF-02 first records **orlan_1** (403 records in all) |
| 14:01:53 |    53.0 s | SENSOR | RF-03 first records **orlan_1** (403 records in all) |
| 14:01:53 |    53.0 s | TRUTH | **orlan_1** (orlan10, hostile) airborne |
| 14:02:07 |    67.0 s | SENSOR | RADAR-01 first records **orlan_1** (282 records in all) |
| 14:02:08 |    68.0 s | SENSOR | ACOUSTIC-02 first records **orlan_1** (347 records in all) |
| 14:02:09 |    69.0 s | SENSOR | ACOUSTIC-01 first records **orlan_1** (326 records in all) |
| 14:02:15 |    75.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000002 at 2152 m |
| 14:02:48 |   108.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000005 at 2355 m |
| 14:02:49 |   109.0 s | C2 | WARN: LOST CONTACT TRK-000000: no update for 60 s |
| 14:02:59 |   119.0 s | TRUTH | **geese_1** (geese, neutral) airborne |
| 14:03:13 |   133.0 s | SENSOR | RADAR-01 first records **geese_1** (337 records in all) |
| 14:03:54 |   174.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000008 at 2139 m |
| 14:04:18 |   198.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000009 at 2184 m |
| 14:04:25 |   205.0 s | C2 | WARN: LOST CONTACT TRK-000006: no update for 60 s |
| 14:04:28 |   208.0 s | SENSOR | RF-01 first records **lancet_1** (254 records in all) |
| 14:04:28 |   208.0 s | SENSOR | RF-02 first records **lancet_1** (259 records in all) |
| 14:04:28 |   208.0 s | SENSOR | RF-03 first records **lancet_1** (258 records in all) |
| 14:04:28 |   208.0 s | TRUTH | **lancet_1** (lancet, hostile) airborne |
| 14:04:30 |   210.0 s | C2 | WARN: LOST CONTACT TRK-000005: no update for 60 s |
| 14:04:42 |   222.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000013 at 2349 m |
| 14:05:09 |   249.0 s | C2 | WARN: LOST CONTACT TRK-000004: no update for 60 s |
| 14:05:26 |   266.0 s | SENSOR | RADAR-01 first records **lancet_1** (38 records in all) |
| 14:06:01 |   301.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000016 at 1746 m |
| 14:06:05 |   305.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000017 at 2334 m |
| 14:06:18 |   318.0 s | C2 | WARN: LOST CONTACT TRK-000013: no update for 60 s |
| 14:06:19 |   319.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000018 at 2900 m |
| 14:06:23 |   323.0 s | C2 | WARN: LOST CONTACT TRK-000003: no update for 60 s |
| 14:06:26 |   326.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000019 at 2410 m |
| 14:06:46 |   346.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000001 at 2988 m |
| 14:07:09 |   369.0 s | SENSOR | CAM-01 first records **lancet_1** (6 records in all) |
| 14:07:17 |   377.0 s | C2 | WARN: LOST CONTACT TRK-000012: no update for 60 s |
| 14:07:27 |   387.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000023 at 2131 m |
| 14:07:35 |   395.0 s | SENSOR | ACOUSTIC-01 first records **geese_1** (313 records in all) |
| 14:07:58 |   418.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000014 at 2995 m |
| 14:08:01 |   421.0 s | SENSOR | ACOUSTIC-02 first records **geese_1** (329 records in all) |
| 14:08:06 |   426.0 s | C2 | WARN: LOST CONTACT TRK-000019: no update for 60 s |
| 14:08:35 |   455.5 s | TRUTH | **orlan_1** track ends |
| 14:08:46 |   466.5 s | TRUTH | **lancet_1** track ends |
| 14:09:00 |   480.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000024 at 2171 m |
| 14:09:02 |   482.0 s | C2 | WARN: LOST CONTACT TRK-000022: no update for 60 s |
| 14:09:28 |   508.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000025 at 2246 m |
| 14:09:29 |   509.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000026 at 2371 m |
| 14:09:33 |   513.0 s | C2 | WARN: LOST CONTACT TRK-000001: no update for 60 s |
| 14:09:40 |   520.0 s | C2 | WARN: LOST CONTACT TRK-000018: no update for 60 s |
| 14:09:45 |   525.0 s | C2 | WARN: LOST CONTACT TRK-000014: no update for 60 s |
| 14:09:52 |   532.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000027 at 2111 m |
| 14:10:01 |   541.0 s | C2 | WARN: LOST CONTACT TRK-000023: no update for 60 s |
| 14:10:39 |   579.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000028 at 2361 m |
| 14:11:15 |   615.0 s | C2 | WARN: LOST CONTACT TRK-000027: no update for 60 s |
| 14:11:20 |   620.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000029 at 2280 m |
| 14:11:59 |   659.0 s | C2 | WARN: LOST CONTACT TRK-000028: no update for 60 s |
| 14:12:38 |   698.0 s | C2 | WARN: LOST CONTACT TRK-000010: no update for 60 s |
| 14:14:10 |   790.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000031 at 2333 m |
| 14:14:30 |   810.5 s | TRUTH | **geese_1** track ends |
| 14:14:41 |   821.0 s | C2 | WARN: LOST CONTACT TRK-000029: no update for 60 s |
| 14:15:18 |   858.0 s | C2 | WARN: SENSOR SILENT ACOUSTIC-01: no detections since 2026-11-04T14:14:18.000Z (ACOUSTIC-02, CAM-01, RADAR-01, RF-01, RF-03 still reporting) |
| 14:15:24 |   864.0 s | C2 | WARN: SENSOR SILENT ACOUSTIC-02: no detections since 2026-11-04T14:14:24.000Z (CAM-01, RADAR-01, RF-01, RF-03 still reporting) |
| 14:15:50 |   890.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000032 at 2455 m |
| 14:16:11 |   911.0 s | C2 | WARN: LOST CONTACT TRK-000031: no update for 60 s |
| 14:16:33 |   933.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000033 at 2073 m |
| 14:17:12 |   972.0 s | C2 | WARN: LOST CONTACT TRK-000032: no update for 60 s |
| 14:17:14 |   974.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000034 at 2253 m |
| 14:18:38 |  1058.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000035 at 2155 m |
| 14:18:47 |  1067.0 s | C2 | WARN: LOST CONTACT TRK-000034: no update for 60 s |
| 14:19:27 |  1107.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000036 at 2164 m |
| 14:19:55 |  1135.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000037 at 2203 m |
| 14:19:58 |  1138.0 s | C2 | WARN: LOST CONTACT TRK-000035: no update for 60 s |
| 14:20:18 |  1158.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000038 at 1911 m |
| 14:20:53 |  1193.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000039 at 2336 m |
| 14:20:59 |  1199.5 s | C2 | ADT-01 → no contact (no C2 track within 500 m at its end) |
| 14:20:59 |  1199.5 s | C2 | ADB-01 → no contact (no C2 track within 500 m at its end) |
| 14:21:00 |  1200.0 s | C2 | SITE-01 → not reached (no confirmed track within 1 km) |

## Outcome per hostile

| hostile | airborne | first sensor record | first C2 alert | truth outcome |
|---|---|---|---|---|
| orlan_1 | 14:01:53 | 14:01:53 (+0 s) | 14:01:53 (+0 s) | not reached |
| lancet_1 | 14:04:28 | 14:04:28 (+0 s) | 14:04:28 (+0 s) | not reached |

## Audit (independent physics checks)

**7 pass · 0 fail · 3 skip**

| check | status | value |
|---|---|---|
| Provenance | PASS | 0 |
| Clock sync | PASS | 0 |
| Bearing geometry | PASS | 0.9498 |
| Terrain shadow | SKIP | — |
| Occlusion gaps | SKIP | — |
| Fix calibration | PASS | 0.4866 |
| Range law | PASS | 2.696 |
| Acoustic delay | PASS | 0.0059 |
| Spoof visibility | SKIP | — |
| Cross-sensor time | PASS | 1.0 |
