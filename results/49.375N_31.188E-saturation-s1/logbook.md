# Log book: 49.375N_31.188E-saturation-s1

49.3754° N · 31.1882° E · 10 km square · 04 Nov 2026 14:01:00 UTC · 20 min · seed 1

Weather: wind from 145° at 1.6 m/s, 7 °C, visibility 12.8 km.

## Cast

| id | type | side | where |
|---|---|---|---|
| SITE-01 | site | friendly | 49.4177° N · 31.2216° E |
| ADT-01 | ad_team | friendly | 49.4177° N · 31.2402° E |
| ADB-01 | ad_battery | friendly | 49.4071° N · 31.2065° E |
| shahed_1 | shahed136 | hostile | moves: 5 waypoints |
| gerbera_1 | gerbera | hostile | moves: 5 waypoints |
| shahed_2 | shahed136 | hostile | moves: 4 waypoints |
| shahed_3 | shahed136 | hostile | moves: 4 waypoints |
| gerbera_2 | gerbera | hostile | moves: 4 waypoints |
| gerbera_3 | gerbera | hostile | moves: 4 waypoints |
| INT-01 | interceptor | friendly | moves: 2 waypoints |
| op_INT-01 | operator | friendly | 49.4177° N · 31.2423° E |
| INT-02 | interceptor | friendly | moves: 2 waypoints |
| op_INT-02 | operator | friendly | 49.4177° N · 31.2440° E |
| INT-03 | interceptor | friendly | moves: 2 waypoints |
| op_INT-03 | operator | friendly | 49.4168° N · 31.2404° E |
| wifi_1 | wifi_ap | neutral | 49.4177° N · 31.2531° E |
| geese_1 | geese | neutral | moves: 2 waypoints |

**Sensors:** RF-01 (rf_df), RF-02 (rf_df), RF-03 (rf_df), RADAR-01 (radar), CAM-01 (camera), ACOUSTIC-01 (microphone), ACOUSTIC-02 (microphone), RID-01 (remote_id), C2-01 (c2)

## Timeline

TRUTH is what happened. SENSOR is the first record each sensor made of each object. C2 is what the command post concluded from sensor data alone (41 routine new-track notices are left out).

| UTC | T+ | voice | event |
|---|---|---|---|
| 14:01:00 |     0.0 s | SENSOR | RF-03 first records **wifi_1** (466 records in all) |
| 14:01:00 |     0.0 s | SENSOR | RF-01 first records **wifi_1** (489 records in all) |
| 14:01:09 |     9.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000000 at 2022 m |
| 14:01:09 |     9.0 s | C2 | ADT-01 → alerted (first warn alert ALT-000001) |
| 14:01:09 |     9.0 s | C2 | ADT-01 → responding (dispatched on ALT-000001) |
| 14:01:09 |     9.0 s | C2 | ADB-01 → alerted (first warn alert ALT-000001) |
| 14:01:09 |     9.0 s | C2 | ADB-01 → responding (dispatched on ALT-000001) |
| 14:01:09 |     9.0 s | C2 | INT-01 → alerted (first warn alert ALT-000001) |
| 14:01:09 |     9.0 s | C2 | INT-02 → alerted (first warn alert ALT-000001) |
| 14:01:09 |     9.0 s | C2 | INT-03 → alerted (first warn alert ALT-000001) |
| 14:01:54 |    54.0 s | TRUTH | **geese_1** (geese, neutral) airborne |
| 14:01:57 |    57.0 s | SENSOR | RADAR-01 first records **geese_1** (337 records in all) |
| 14:01:59 |    59.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000001 at 2278 m |
| 14:02:23 |    83.0 s | SENSOR | ACOUSTIC-02 first records **geese_1** (214 records in all) |
| 14:02:26 |    86.0 s | C2 | WARN: LOST CONTACT TRK-000000: no update for 60 s |
| 14:02:32 |    92.0 s | SENSOR | ACOUSTIC-01 first records **geese_1** (189 records in all) |
| 14:02:49 |   109.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000002 at 2199 m |
| 14:03:08 |   128.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000003 at 1630 m |
| 14:03:21 |   141.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000004 at 2414 m |
| 14:03:54 |   174.0 s | C2 | WARN: LOST CONTACT TRK-000002: no update for 60 s |
| 14:04:45 |   225.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000005 at 2367 m |
| 14:05:11 |   251.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000006 at 2467 m |
| 14:05:20 |   260.0 s | C2 | WARN: LOST CONTACT TRK-000004: no update for 60 s |
| 14:05:50 |   290.5 s | TRUTH | **shahed_2** (shahed136, hostile) airborne |
| 14:05:51 |   291.0 s | SENSOR | RADAR-01 first records **shahed_2** (14 records in all) |
| 14:05:52 |   292.5 s | TRUTH | **gerbera_2** (gerbera, hostile) airborne |
| 14:05:54 |   294.0 s | SENSOR | RADAR-01 first records **gerbera_2** (12 records in all) |
| 14:05:55 |   295.0 s | TRUTH | **shahed_1** (shahed136, hostile) airborne |
| 14:05:56 |   296.8 s | C2 | INT-02 → available (asset on hand) |
| 14:05:56 |   296.8 s | C2 | INT-02 → responding (launched by C2) |
| 14:05:57 |   297.0 s | SENSOR | RF-01 first records **op_INT-02** (78 records in all) |
| 14:05:57 |   297.0 s | SENSOR | RF-01 first records **INT-02** (78 records in all) |
| 14:05:57 |   297.0 s | SENSOR | RF-03 first records **op_INT-02** (78 records in all) |
| 14:05:57 |   297.0 s | SENSOR | RF-03 first records **INT-02** (77 records in all) |
| 14:05:57 |   297.0 s | TRUTH | **INT-02** (interceptor, friendly) airborne |
| 14:06:00 |   300.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000007 at 1431 m |
| 14:06:00 |   300.0 s | SENSOR | RF-03 first records **shahed_2** (3 records in all) |
| 14:06:00 |   300.0 s | SENSOR | RF-02 first records **INT-02** (55 records in all) |
| 14:06:04 |   304.0 s | SENSOR | RADAR-01 first records **shahed_1** (96 records in all) |
| 14:06:05 |   305.0 s | SENSOR | RF-02 first records **shahed_2** (5 records in all) |
| 14:06:05 |   305.0 s | SENSOR | RF-03 first records **shahed_1** (7 records in all) |
| 14:06:10 |   310.0 s | SENSOR | ACOUSTIC-02 first records **shahed_2** (50 records in all) |
| 14:06:11 |   311.0 s | C2 | CRITICAL: CLOSE TO SITE-01: TRK-000007 at 924 m |
| 14:06:11 |   311.0 s | C2 | SITE-01 → approached (confirmed track TRK-000007 within 924 m) |
| 14:06:11 |   311.0 s | SENSOR | RF-01 first records **shahed_1** (8 records in all) |
| 14:06:11 |   311.0 s | SENSOR | ACOUSTIC-01 first records **shahed_1** (113 records in all) |
| 14:06:13 |   313.0 s | SENSOR | RF-02 first records **shahed_1** (8 records in all) |
| 14:06:13 |   313.0 s | SENSOR | ACOUSTIC-01 first records **shahed_2** (20 records in all) |
| 14:06:16 |   316.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000009 at 1942 m |
| 14:06:20 |   320.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000010 at 845 m |
| 14:06:20 |   320.0 s | C2 | CRITICAL: CLOSE TO SITE-01: TRK-000010 at 845 m |
| 14:06:22 |   322.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000011 at 2477 m |
| 14:06:39 |   339.9 s | C2 | INT-03 → available (asset on hand) |
| 14:06:39 |   339.9 s | C2 | INT-03 → responding (launched by C2) |
| 14:06:40 |   340.0 s | SENSOR | RF-03 first records **INT-03** (32 records in all) |
| 14:06:40 |   340.0 s | SENSOR | RF-03 first records **op_INT-03** (66 records in all) |
| 14:06:40 |   340.0 s | SENSOR | RF-01 first records **op_INT-03** (66 records in all) |
| 14:06:40 |   340.0 s | SENSOR | RF-01 first records **INT-03** (45 records in all) |
| 14:06:40 |   340.0 s | TRUTH | **INT-03** (interceptor, friendly) airborne |
| 14:06:48 |   348.0 s | SENSOR | RF-02 first records **INT-03** (34 records in all) |
| 14:06:50 |   350.0 s | C2 | CRITICAL: CLOSE TO SITE-01: TRK-000006 at 884 m |
| 14:06:53 |   353.7 s | C2 | INT-01 → available (asset on hand) |
| 14:06:53 |   353.7 s | C2 | INT-01 → responding (launched by C2) |
| 14:06:54 |   354.0 s | SENSOR | RF-03 first records **INT-01** (84 records in all) |
| 14:06:54 |   354.0 s | SENSOR | RF-03 first records **op_INT-01** (90 records in all) |
| 14:06:54 |   354.0 s | TRUTH | **INT-01** (interceptor, friendly) airborne |
| 14:06:56 |   356.0 s | SENSOR | RF-01 first records **INT-01** (81 records in all) |
| 14:06:57 |   357.0 s | SENSOR | RF-01 first records **op_INT-01** (30 records in all) |
| 14:06:58 |   358.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000014 at 1250 m |
| 14:07:00 |   360.0 s | SENSOR | RF-01 first records **shahed_2** (1 records in all) |
| 14:07:00 |   360.0 s | SENSOR | ACOUSTIC-02 first records **shahed_1** (84 records in all) |
| 14:07:02 |   362.0 s | SENSOR | RF-02 first records **INT-01** (52 records in all) |
| 14:07:04 |   364.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000015 at 2115 m |
| 14:07:11 |   371.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000016 at 363 m |
| 14:07:11 |   371.0 s | C2 | CRITICAL: CLOSE TO SITE-01: TRK-000016 at 363 m |
| 14:07:14 |   374.0 s | TRUTH | **INT-02** at the rendezvous point |
| 14:07:14 |   374.5 s | C2 | INT-02 → no contact (no C2 track within 500 m at its end) |
| 14:07:14 |   374.5 s | TRUTH | **shahed_2** intercepted (closest approach to SITE-01: 3036.2 m) |
| 14:07:19 |   379.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000017 at 1066 m |
| 14:07:25 |   385.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000018 at 1338 m |
| 14:07:26 |   386.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000019 at 1992 m |
| 14:07:33 |   393.0 s | C2 | WARN: LOST CONTACT TRK-000009: no update for 60 s |
| 14:07:38 |   398.0 s | SENSOR | RADAR-01 first records **INT-01** (25 records in all) |
| 14:07:40 |   400.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000020 at 2506 m |
| 14:07:42 |   402.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000021 at 1470 m |
| 14:07:45 |   405.5 s | C2 | INT-03 → no contact (no C2 track within 500 m at its end) |
| 14:07:45 |   405.5 s | TRUTH | **gerbera_2** intercepted (closest approach to SITE-01: 2572.6 m) |
| 14:07:45 |   405.5 s | TRUTH | **INT-03** at the rendezvous point |
| 14:07:51 |   411.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000022 at 1849 m |
| 14:07:59 |   419.0 s | C2 | WARN: LOST CONTACT TRK-000006: no update for 60 s |
| 14:08:12 |   432.0 s | C2 | WARN: LOST CONTACT TRK-000007: no update for 60 s |
| 14:08:12 |   432.0 s | C2 | WARN: LOST CONTACT TRK-000014: no update for 60 s |
| 14:08:23 |   443.5 s | C2 | INT-01 → rendezvous reported (C2 track TRK-000012 within 460 m at its end) |
| 14:08:23 |   443.5 s | TRUTH | **shahed_1** intercepted (closest approach to SITE-01: 4384.1 m) |
| 14:08:23 |   443.5 s | TRUTH | **INT-01** at the rendezvous point |
| 14:08:29 |   449.0 s | C2 | WARN: LOST CONTACT TRK-000018: no update for 60 s |
| 14:08:41 |   461.0 s | C2 | WARN: LOST CONTACT TRK-000020: no update for 60 s |
| 14:08:46 |   466.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000023 at 2574 m |
| 14:09:28 |   508.0 s | C2 | WARN: LOST CONTACT TRK-000012: no update for 60 s |
| 14:09:28 |   508.0 s | C2 | WARN: LOST CONTACT TRK-000017: no update for 60 s |
| 14:09:28 |   508.0 s | C2 | WARN: LOST CONTACT TRK-000021: no update for 60 s |
| 14:09:36 |   516.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000024 at 2237 m |
| 14:10:22 |   562.5 s | TRUTH | **gerbera_3** (gerbera, hostile) airborne |
| 14:10:29 |   569.5 s | TRUTH | **gerbera_1** (gerbera, hostile) airborne |
| 14:10:33 |   573.5 s | TRUTH | **shahed_3** (shahed136, hostile) airborne |
| 14:10:34 |   574.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000026 at 2154 m |
| 14:10:36 |   576.0 s | C2 | WARN: LOST CONTACT TRK-000003: no update for 60 s |
| 14:10:36 |   576.0 s | SENSOR | RF-03 first records **shahed_3** (11 records in all) |
| 14:10:36 |   576.0 s | SENSOR | RADAR-01 first records **shahed_3** (97 records in all) |
| 14:10:41 |   581.0 s | SENSOR | RADAR-01 first records **gerbera_3** (17 records in all) |
| 14:10:42 |   582.0 s | SENSOR | ACOUSTIC-02 first records **gerbera_3** (6 records in all) |
| 14:10:45 |   585.0 s | SENSOR | ACOUSTIC-01 first records **gerbera_3** (1 records in all) |
| 14:10:46 |   586.0 s | SENSOR | ACOUSTIC-01 first records **gerbera_1** (47 records in all) |
| 14:10:48 |   588.0 s | SENSOR | ACOUSTIC-02 first records **shahed_3** (178 records in all) |
| 14:10:49 |   589.0 s | SENSOR | ACOUSTIC-01 first records **shahed_3** (170 records in all) |
| 14:10:51 |   591.0 s | SENSOR | RADAR-01 first records **gerbera_1** (101 records in all) |
| 14:10:52 |   592.0 s | SENSOR | RF-01 first records **shahed_3** (10 records in all) |
| 14:11:26 |   626.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000029 at 2188 m |
| 14:12:01 |   661.0 s | C2 | WARN: LOST CONTACT TRK-000026: no update for 60 s |
| 14:12:03 |   663.0 s | SENSOR | RF-02 first records **shahed_3** (10 records in all) |
| 14:12:06 |   666.0 s | C2 | WARN: LOST CONTACT TRK-000027: no update for 60 s |
| 14:12:08 |   668.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000032 at 2532 m |
| 14:12:25 |   685.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000033 at 2173 m |
| 14:12:40 |   700.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000028 at 2983 m |
| 14:12:49 |   709.0 s | C2 | WARN: LOST CONTACT TRK-000030: no update for 60 s |
| 14:12:51 |   711.5 s | TRUTH | **geese_1** track ends |
| 14:13:13 |   733.0 s | TRUTH | **gerbera_3** reaches SITE-01 (22.2 m) |
| 14:13:25 |   745.0 s | C2 | CRITICAL: CLOSE TO SITE-01: TRK-000028 at 949 m |
| 14:13:26 |   746.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000031 at 2977 m |
| 14:13:36 |   756.0 s | C2 | WARN: LOST CONTACT TRK-000033: no update for 60 s |
| 14:13:45 |   765.5 s | TRUTH | **shahed_3** reaches SITE-01 (5.2 m) |
| 14:13:46 |   766.0 s | SENSOR | ACOUSTIC-02 first records **gerbera_1** (41 records in all) |
| 14:14:10 |   790.0 s | C2 | CRITICAL: CLOSE TO SITE-01: TRK-000031 at 818 m |
| 14:14:12 |   792.0 s | C2 | WARN: LOST CONTACT TRK-000032: no update for 60 s |
| 14:14:26 |   806.5 s | TRUTH | **gerbera_1** reaches SITE-01 (21.7 m) |
| 14:14:31 |   811.0 s | C2 | WARN: LOST CONTACT TRK-000028: no update for 60 s |
| 14:14:33 |   813.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000034 at 2009 m |
| 14:15:02 |   842.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000035 at 2152 m |
| 14:15:16 |   856.0 s | C2 | WARN: LOST CONTACT TRK-000031: no update for 60 s |
| 14:15:25 |   865.0 s | C2 | WARN: SENSOR SILENT ACOUSTIC-01: no detections since 2026-11-04T14:14:25.000Z (ACOUSTIC-02, CAM-01, RADAR-01, RF-01, RF-03 still reporting) |
| 14:15:26 |   866.0 s | C2 | WARN: SENSOR SILENT ACOUSTIC-02: no detections since 2026-11-04T14:14:26.000Z (CAM-01, RADAR-01, RF-01, RF-03 still reporting) |
| 14:16:06 |   906.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000036 at 2289 m |
| 14:16:35 |   935.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000037 at 2024 m |
| 14:16:35 |   935.0 s | C2 | WARN: LOST CONTACT TRK-000035: no update for 60 s |
| 14:17:20 |   980.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000038 at 2234 m |
| 14:17:58 |  1018.0 s | C2 | WARN: LOST CONTACT TRK-000037: no update for 60 s |
| 14:18:31 |  1051.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000039 at 2248 m |
| 14:18:47 |  1067.0 s | C2 | WARN: LOST CONTACT TRK-000038: no update for 60 s |
| 14:20:22 |  1162.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000040 at 2468 m |
| 14:20:39 |  1179.0 s | C2 | WARN: LOST CONTACT TRK-000039: no update for 60 s |
| 14:20:59 |  1199.5 s | C2 | ADT-01 → no contact (no C2 track within 500 m at its end) |
| 14:20:59 |  1199.5 s | C2 | ADB-01 → no contact (no C2 track within 500 m at its end) |

## Outcome per hostile

| hostile | airborne | first sensor record | first C2 alert | truth outcome |
|---|---|---|---|---|
| shahed_1 | 14:05:55 | 14:06:04 (+9 s) | none | intercepted |
| gerbera_1 | 14:10:29 | 14:10:46 (+16 s) | none | reached |
| shahed_2 | 14:05:50 | 14:05:51 (+0 s) | none | intercepted |
| shahed_3 | 14:10:33 | 14:10:36 (+2 s) | 14:12:40 (+126 s) | reached |
| gerbera_2 | 14:05:52 | 14:05:54 (+2 s) | none | intercepted |
| gerbera_3 | 14:10:22 | 14:10:41 (+18 s) | none | reached |

## Audit (independent physics checks)

**6 pass · 2 fail · 2 skip**

| check | status | value |
|---|---|---|
| Provenance | PASS | 0 |
| Clock sync | PASS | 0 |
| Bearing geometry | PASS | 0.9207 |
| Terrain shadow | PASS | 19.32 |
| Occlusion gaps | SKIP | — |
| Fix calibration | PASS | 0.5637 |
| Range law | FAIL | 0.261 |
| Acoustic delay | FAIL | 0.0235 |
| Spoof visibility | SKIP | — |
| Cross-sensor time | PASS | 1.0 |
