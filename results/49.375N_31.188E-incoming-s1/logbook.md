# Log book: 49.375N_31.188E-incoming-s1

49.3754° N · 31.1882° E · 10 km square · 04 Nov 2026 14:01:00 UTC · 20 min · seed 1

Weather: wind from 145° at 1.6 m/s, 7 °C, visibility 12.8 km.

## Cast

| id | type | side | where |
|---|---|---|---|
| SITE-01 | site | friendly | 49.4177° N · 31.2216° E |
| ADT-01 | ad_team | friendly | 49.4177° N · 31.2402° E |
| ADB-01 | ad_battery | friendly | 49.4071° N · 31.2065° E |
| gerbera_1 | gerbera | hostile | moves: 4 waypoints |
| orlan_1 | orlan10 | hostile | moves: 6 waypoints |
| shahed_1 | shahed136 | hostile | moves: 5 waypoints |
| shahed_2 | shahed136 | hostile | moves: 5 waypoints |
| gerbera_2 | gerbera | hostile | moves: 5 waypoints |
| gerbera_3 | gerbera | hostile | moves: 4 waypoints |
| wifi_1 | wifi_ap | neutral | 49.4177° N · 31.2531° E |
| geese_1 | geese | neutral | moves: 2 waypoints |

**Sensors:** RF-01 (rf_df), RF-02 (rf_df), RF-03 (rf_df), RADAR-01 (radar), CAM-01 (camera), ACOUSTIC-01 (microphone), ACOUSTIC-02 (microphone), RID-01 (remote_id), C2-01 (c2)

## Timeline

TRUTH is what happened. SENSOR is the first record each sensor made of each object. C2 is what the command post concluded from sensor data alone (39 routine new-track notices are left out).

| UTC | T+ | voice | event |
|---|---|---|---|
| 14:01:00 |     0.0 s | SENSOR | RF-03 first records **wifi_1** (449 records in all) |
| 14:01:00 |     0.0 s | SENSOR | RF-01 first records **wifi_1** (440 records in all) |
| 14:01:14 |    14.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000000 at 2097 m |
| 14:01:14 |    14.0 s | C2 | ADT-01 → alerted (first warn alert ALT-000001) |
| 14:01:14 |    14.0 s | C2 | ADT-01 → responding (dispatched on ALT-000001) |
| 14:01:14 |    14.0 s | C2 | ADB-01 → alerted (first warn alert ALT-000001) |
| 14:01:14 |    14.0 s | C2 | ADB-01 → responding (dispatched on ALT-000001) |
| 14:02:14 |    74.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000001 at 2082 m |
| 14:02:36 |    96.5 s | TRUTH | **gerbera_2** (gerbera, hostile) airborne |
| 14:02:39 |    99.0 s | SENSOR | RADAR-01 first records **gerbera_2** (1 records in all) |
| 14:02:41 |   101.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000002 at 2356 m |
| 14:02:42 |   102.0 s | TRUTH | **gerbera_2** reaches SITE-01 (8.9 m) |
| 14:02:55 |   115.0 s | C2 | WARN: LOST CONTACT TRK-000000: no update for 60 s |
| 14:03:06 |   126.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000003 at 1991 m |
| 14:03:17 |   137.0 s | C2 | WARN: LOST CONTACT TRK-000001: no update for 60 s |
| 14:04:15 |   195.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000004 at 2138 m |
| 14:04:31 |   211.0 s | TRUTH | **gerbera_1** (gerbera, hostile) airborne |
| 14:04:34 |   214.0 s | SENSOR | RADAR-01 first records **gerbera_1** (22 records in all) |
| 14:04:39 |   219.0 s | C2 | WARN: LOST CONTACT TRK-000003: no update for 60 s |
| 14:04:47 |   227.0 s | SENSOR | ACOUSTIC-01 first records **gerbera_1** (84 records in all) |
| 14:04:48 |   228.0 s | SENSOR | ACOUSTIC-02 first records **gerbera_1** (59 records in all) |
| 14:04:53 |   233.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000006 at 2336 m |
| 14:05:26 |   266.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000008 at 2188 m |
| 14:06:06 |   306.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000009 at 209 m |
| 14:06:06 |   306.0 s | C2 | CRITICAL: CLOSE TO SITE-01: TRK-000009 at 209 m |
| 14:06:06 |   306.0 s | SENSOR | RF-02 first records **orlan_1** (382 records in all) |
| 14:06:06 |   306.0 s | SENSOR | RF-03 first records **orlan_1** (382 records in all) |
| 14:06:06 |   306.0 s | SENSOR | RF-01 first records **orlan_1** (382 records in all) |
| 14:06:06 |   306.0 s | TRUTH | **orlan_1** (orlan10, hostile) airborne |
| 14:06:07 |   307.0 s | SENSOR | RADAR-01 first records **orlan_1** (255 records in all) |
| 14:06:08 |   308.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000010 at 2248 m |
| 14:06:08 |   308.0 s | C2 | SITE-01 → approached (confirmed track TRK-000009 within 220 m) |
| 14:06:17 |   317.0 s | C2 | WARN: LOST CONTACT TRK-000007: no update for 60 s |
| 14:06:22 |   322.0 s | SENSOR | ACOUSTIC-02 first records **orlan_1** (131 records in all) |
| 14:06:25 |   325.5 s | TRUTH | **gerbera_1** reaches SITE-01 (5.3 m) |
| 14:06:34 |   334.0 s | SENSOR | ACOUSTIC-01 first records **orlan_1** (41 records in all) |
| 14:07:11 |   371.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000011 at 2168 m |
| 14:07:24 |   384.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000012 at 2593 m |
| 14:07:36 |   396.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000013 at 2352 m |
| 14:08:00 |   420.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000014 at 2301 m |
| 14:08:30 |   450.5 s | TRUTH | **shahed_2** (shahed136, hostile) airborne |
| 14:08:31 |   451.0 s | SENSOR | RADAR-01 first records **shahed_2** (136 records in all) |
| 14:08:32 |   452.0 s | SENSOR | RF-02 first records **shahed_2** (20 records in all) |
| 14:08:39 |   459.0 s | SENSOR | RF-01 first records **shahed_2** (20 records in all) |
| 14:08:44 |   464.0 s | SENSOR | ACOUSTIC-01 first records **shahed_2** (111 records in all) |
| 14:08:45 |   465.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000015 at 2076 m |
| 14:08:47 |   467.0 s | SENSOR | ACOUSTIC-02 first records **shahed_2** (95 records in all) |
| 14:08:52 |   472.5 s | TRUTH | **gerbera_3** (gerbera, hostile) airborne |
| 14:08:59 |   479.0 s | SENSOR | RF-03 first records **shahed_2** (18 records in all) |
| 14:09:09 |   489.0 s | SENSOR | RADAR-01 first records **gerbera_3** (9 records in all) |
| 14:09:19 |   499.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000018 at 2302 m |
| 14:09:24 |   504.5 s | TRUTH | **geese_1** (geese, neutral) airborne |
| 14:09:26 |   506.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000019 at 554 m |
| 14:09:26 |   506.0 s | C2 | CRITICAL: CLOSE TO SITE-01: TRK-000019 at 554 m |
| 14:09:26 |   506.0 s | SENSOR | RADAR-01 first records **geese_1** (319 records in all) |
| 14:09:27 |   507.5 s | TRUTH | **shahed_1** (shahed136, hostile) airborne |
| 14:09:31 |   511.0 s | SENSOR | RADAR-01 first records **shahed_1** (57 records in all) |
| 14:09:38 |   518.0 s | TRUTH | **gerbera_3** reaches SITE-01 (3.6 m) |
| 14:09:45 |   525.0 s | SENSOR | ACOUSTIC-02 first records **shahed_1** (138 records in all) |
| 14:09:48 |   528.0 s | SENSOR | ACOUSTIC-01 first records **shahed_1** (125 records in all) |
| 14:10:00 |   540.0 s | SENSOR | RF-02 first records **shahed_1** (9 records in all) |
| 14:10:05 |   545.0 s | SENSOR | RF-01 first records **shahed_1** (11 records in all) |
| 14:10:16 |   556.0 s | SENSOR | RF-03 first records **shahed_1** (3 records in all) |
| 14:10:31 |   571.0 s | C2 | WARN: LOST CONTACT TRK-000019: no update for 60 s |
| 14:10:35 |   575.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000021 at 2245 m |
| 14:11:07 |   607.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000020 at 2531 m |
| 14:11:14 |   614.0 s | C2 | WARN: LOST CONTACT TRK-000018: no update for 60 s |
| 14:11:32 |   632.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000024 at 2342 m |
| 14:11:39 |   639.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000016 at 2951 m |
| 14:11:42 |   642.0 s | C2 | CRITICAL: CLOSE TO SITE-01: TRK-000020 at 970 m |
| 14:12:02 |   662.5 s | TRUTH | **shahed_1** reaches SITE-01 (22.1 m) |
| 14:12:11 |   671.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000025 at 1999 m |
| 14:12:14 |   674.0 s | C2 | CRITICAL: CLOSE TO SITE-01: TRK-000016 at 816 m |
| 14:12:27 |   687.0 s | TRUTH | **orlan_1** track ends |
| 14:12:28 |   688.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000026 at 2200 m |
| 14:12:39 |   699.5 s | TRUTH | **shahed_2** reaches SITE-01 (13.2 m) |
| 14:12:40 |   700.0 s | SENSOR | ACOUSTIC-02 first records **geese_1** (391 records in all) |
| 14:12:48 |   708.0 s | SENSOR | ACOUSTIC-01 first records **geese_1** (335 records in all) |
| 14:12:51 |   711.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000027 at 2249 m |
| 14:13:01 |   721.0 s | C2 | WARN: LOST CONTACT TRK-000020: no update for 60 s |
| 14:13:06 |   726.0 s | C2 | WARN: LOST CONTACT TRK-000024: no update for 60 s |
| 14:13:21 |   741.0 s | C2 | WARN: LOST CONTACT TRK-000023: no update for 60 s |
| 14:13:26 |   746.0 s | C2 | WARN: LOST CONTACT TRK-000009: no update for 60 s |
| 14:13:43 |   763.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000028 at 2153 m |
| 14:13:43 |   763.0 s | C2 | WARN: LOST CONTACT TRK-000016: no update for 60 s |
| 14:14:18 |   798.0 s | C2 | WARN: LOST CONTACT TRK-000027: no update for 60 s |
| 14:14:23 |   803.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000029 at 2196 m |
| 14:15:02 |   842.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000030 at 2398 m |
| 14:15:02 |   842.0 s | C2 | WARN: LOST CONTACT TRK-000028: no update for 60 s |
| 14:15:40 |   880.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000031 at 2390 m |
| 14:16:02 |   902.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000032 at 2300 m |
| 14:16:23 |   923.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000033 at 2230 m |
| 14:17:01 |   961.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000034 at 2289 m |
| 14:17:39 |   999.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000035 at 1994 m |
| 14:18:19 |  1039.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000036 at 2137 m |
| 14:19:25 |  1105.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000037 at 2424 m |
| 14:20:03 |  1143.0 s | C2 | WARN: LOST CONTACT TRK-000036: no update for 60 s |
| 14:20:23 |  1163.0 s | C2 | WARN: LOST CONTACT TRK-000022: no update for 60 s |
| 14:20:58 |  1198.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000038 at 2264 m |
| 14:20:59 |  1199.5 s | C2 | ADT-01 → no contact (no C2 track within 500 m at its end) |
| 14:20:59 |  1199.5 s | C2 | ADB-01 → no contact (no C2 track within 500 m at its end) |

## Outcome per hostile

| hostile | airborne | first sensor record | first C2 alert | truth outcome |
|---|---|---|---|---|
| gerbera_1 | 14:04:31 | 14:04:34 (+3 s) | none | reached |
| orlan_1 | 14:06:06 | 14:06:06 (+0 s) | 14:06:06 (+0 s) | approached |
| shahed_1 | 14:09:27 | 14:09:31 (+4 s) | none | reached |
| shahed_2 | 14:08:30 | 14:08:31 (+0 s) | 14:11:39 (+188 s) | reached |
| gerbera_2 | 14:02:36 | 14:02:39 (+2 s) | none | reached |
| gerbera_3 | 14:08:52 | 14:09:09 (+16 s) | none | reached |

## Audit (independent physics checks)

**7 pass · 0 fail · 3 skip**

| check | status | value |
|---|---|---|
| Provenance | PASS | 0 |
| Clock sync | PASS | 0 |
| Bearing geometry | PASS | 0.9472 |
| Terrain shadow | SKIP | — |
| Occlusion gaps | SKIP | — |
| Fix calibration | PASS | 0.4943 |
| Range law | PASS | 3.046 |
| Acoustic delay | PASS | 0.0176 |
| Spoof visibility | SKIP | — |
| Cross-sensor time | PASS | 1.0 |
