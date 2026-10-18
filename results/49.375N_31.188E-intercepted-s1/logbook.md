# Log book: 49.375N_31.188E-intercepted-s1

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
| INT-01 | interceptor | friendly | moves: 2 waypoints |
| op_INT-01 | operator | friendly | 49.4170° N · 31.2389° E |
| INT-02 | interceptor | friendly | moves: 2 waypoints |
| op_INT-02 | operator | friendly | 49.4154° N · 31.2370° E |
| wifi_1 | wifi_ap | neutral | 49.4177° N · 31.2531° E |
| geese_1 | geese | neutral | moves: 2 waypoints |

**Sensors:** RF-01 (rf_df), RF-02 (rf_df), RF-03 (rf_df), RADAR-01 (radar), CAM-01 (camera), ACOUSTIC-01 (microphone), ACOUSTIC-02 (microphone), RID-01 (remote_id), C2-01 (c2)

## Timeline

TRUTH is what happened. SENSOR is the first record each sensor made of each object. C2 is what the command post concluded from sensor data alone (43 routine new-track notices are left out).

| UTC | T+ | voice | event |
|---|---|---|---|
| 14:01:01 |     1.0 s | SENSOR | RF-03 first records **wifi_1** (443 records in all) |
| 14:01:02 |     2.0 s | SENSOR | RF-01 first records **wifi_1** (466 records in all) |
| 14:01:23 |    23.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000000 at 2433 m |
| 14:01:23 |    23.0 s | C2 | ADT-01 → alerted (first warn alert ALT-000001) |
| 14:01:23 |    23.0 s | C2 | ADT-01 → responding (dispatched on ALT-000001) |
| 14:01:23 |    23.0 s | C2 | ADB-01 → alerted (first warn alert ALT-000001) |
| 14:01:23 |    23.0 s | C2 | ADB-01 → responding (dispatched on ALT-000001) |
| 14:01:23 |    23.0 s | C2 | INT-01 → alerted (first warn alert ALT-000001) |
| 14:01:23 |    23.0 s | C2 | INT-02 → alerted (first warn alert ALT-000001) |
| 14:02:13 |    73.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000001 at 2149 m |
| 14:02:36 |    96.5 s | TRUTH | **gerbera_2** (gerbera, hostile) airborne |
| 14:02:42 |   102.0 s | TRUTH | **gerbera_2** reaches SITE-01 (8.9 m) |
| 14:02:47 |   107.0 s | C2 | WARN: LOST CONTACT TRK-000000: no update for 60 s |
| 14:03:06 |   126.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000002 at 1974 m |
| 14:03:30 |   150.0 s | C2 | WARN: LOST CONTACT TRK-000001: no update for 60 s |
| 14:04:08 |   188.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000003 at 2438 m |
| 14:04:31 |   211.0 s | SENSOR | RADAR-01 first records **gerbera_1** (26 records in all) |
| 14:04:31 |   211.0 s | TRUTH | **gerbera_1** (gerbera, hostile) airborne |
| 14:04:40 |   220.0 s | C2 | WARN: LOST CONTACT TRK-000002: no update for 60 s |
| 14:04:45 |   225.0 s | SENSOR | ACOUSTIC-01 first records **gerbera_1** (65 records in all) |
| 14:04:48 |   228.0 s | SENSOR | ACOUSTIC-02 first records **gerbera_1** (46 records in all) |
| 14:04:57 |   237.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000005 at 2220 m |
| 14:05:20 |   260.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000007 at 2098 m |
| 14:05:20 |   260.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000006 at 2949 m |
| 14:05:24 |   264.0 s | TRUTH | **geese_1** (geese, neutral) airborne |
| 14:05:39 |   279.0 s | SENSOR | RADAR-01 first records **geese_1** (351 records in all) |
| 14:05:51 |   291.8 s | C2 | INT-01 → available (asset on hand) |
| 14:05:51 |   291.8 s | C2 | INT-01 → responding (launched by C2) |
| 14:05:52 |   292.0 s | SENSOR | RF-03 first records **op_INT-01** (9 records in all) |
| 14:05:52 |   292.0 s | SENSOR | RF-03 first records **INT-01** (9 records in all) |
| 14:05:52 |   292.0 s | SENSOR | RF-01 first records **op_INT-01** (9 records in all) |
| 14:05:52 |   292.0 s | SENSOR | RF-01 first records **INT-01** (9 records in all) |
| 14:05:52 |   292.0 s | TRUTH | **INT-01** (interceptor, friendly) airborne |
| 14:05:53 |   293.0 s | SENSOR | RF-02 first records **INT-01** (3 records in all) |
| 14:06:00 |   300.0 s | TRUTH | **gerbera_1** intercepted (closest approach to SITE-01: 1166.3 m) |
| 14:06:00 |   300.0 s | TRUTH | **INT-01** at the rendezvous point |
| 14:06:00 |   300.4 s | C2 | INT-01 → no contact (no C2 track within 500 m at its end) |
| 14:06:01 |   301.0 s | SENSOR | ACOUSTIC-01 first records **geese_1** (121 records in all) |
| 14:06:01 |   301.0 s | SENSOR | ACOUSTIC-02 first records **geese_1** (81 records in all) |
| 14:06:06 |   306.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000008 at 269 m |
| 14:06:06 |   306.0 s | C2 | CRITICAL: CLOSE TO SITE-01: TRK-000008 at 269 m |
| 14:06:06 |   306.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000009 at 2336 m |
| 14:06:06 |   306.0 s | SENSOR | RF-03 first records **orlan_1** (382 records in all) |
| 14:06:06 |   306.0 s | SENSOR | RF-02 first records **orlan_1** (382 records in all) |
| 14:06:06 |   306.0 s | SENSOR | RF-01 first records **orlan_1** (382 records in all) |
| 14:06:06 |   306.0 s | TRUTH | **orlan_1** (orlan10, hostile) airborne |
| 14:06:08 |   308.0 s | C2 | SITE-01 → approached (confirmed track TRK-000008 within 286 m) |
| 14:06:08 |   308.0 s | SENSOR | RADAR-01 first records **orlan_1** (249 records in all) |
| 14:06:22 |   322.0 s | SENSOR | ACOUSTIC-02 first records **orlan_1** (141 records in all) |
| 14:06:34 |   334.0 s | SENSOR | ACOUSTIC-01 first records **orlan_1** (54 records in all) |
| 14:06:42 |   342.0 s | C2 | WARN: LOST CONTACT TRK-000007: no update for 60 s |
| 14:06:54 |   354.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000010 at 1943 m |
| 14:06:58 |   358.0 s | C2 | WARN: LOST CONTACT TRK-000006: no update for 60 s |
| 14:07:42 |   402.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000011 at 2386 m |
| 14:08:19 |   439.0 s | C2 | WARN: LOST CONTACT TRK-000010: no update for 60 s |
| 14:08:21 |   441.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000013 at 1971 m |
| 14:08:25 |   445.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000014 at 2256 m |
| 14:08:30 |   450.5 s | TRUTH | **shahed_2** (shahed136, hostile) airborne |
| 14:08:31 |   451.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000015 at 2340 m |
| 14:08:32 |   452.0 s | SENSOR | RF-02 first records **shahed_2** (12 records in all) |
| 14:08:34 |   454.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000016 at 2787 m |
| 14:08:37 |   457.0 s | SENSOR | RADAR-01 first records **shahed_2** (67 records in all) |
| 14:08:39 |   459.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000017 at 2823 m |
| 14:08:39 |   459.0 s | SENSOR | RF-01 first records **shahed_2** (14 records in all) |
| 14:08:44 |   464.0 s | SENSOR | ACOUSTIC-01 first records **shahed_2** (64 records in all) |
| 14:08:47 |   467.0 s | SENSOR | ACOUSTIC-02 first records **shahed_2** (58 records in all) |
| 14:08:52 |   472.5 s | TRUTH | **gerbera_3** (gerbera, hostile) airborne |
| 14:08:59 |   479.0 s | SENSOR | RF-03 first records **shahed_2** (5 records in all) |
| 14:09:02 |   482.0 s | SENSOR | RADAR-01 first records **gerbera_3** (7 records in all) |
| 14:09:04 |   484.0 s | C2 | WARN: LOST CONTACT TRK-000012: no update for 60 s |
| 14:09:15 |   495.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000021 at 2135 m |
| 14:09:16 |   496.6 s | C2 | INT-02 → available (asset on hand) |
| 14:09:16 |   496.6 s | C2 | INT-02 → responding (launched by C2) |
| 14:09:17 |   497.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000023 at 1274 m |
| 14:09:17 |   497.0 s | SENSOR | RF-01 first records **op_INT-02** (80 records in all) |
| 14:09:17 |   497.0 s | SENSOR | RF-03 first records **INT-02** (80 records in all) |
| 14:09:17 |   497.0 s | SENSOR | RF-03 first records **op_INT-02** (80 records in all) |
| 14:09:17 |   497.0 s | SENSOR | RF-01 first records **INT-02** (80 records in all) |
| 14:09:17 |   497.0 s | TRUTH | **INT-02** (interceptor, friendly) airborne |
| 14:09:19 |   499.0 s | SENSOR | RF-02 first records **INT-02** (49 records in all) |
| 14:09:27 |   507.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000024 at 1214 m |
| 14:09:27 |   507.5 s | TRUTH | **shahed_1** (shahed136, hostile) airborne |
| 14:09:33 |   513.0 s | SENSOR | RADAR-01 first records **shahed_1** (57 records in all) |
| 14:09:38 |   518.0 s | TRUTH | **gerbera_3** reaches SITE-01 (3.6 m) |
| 14:09:45 |   525.0 s | SENSOR | ACOUSTIC-02 first records **shahed_1** (138 records in all) |
| 14:09:47 |   527.0 s | C2 | WARN: LOST CONTACT TRK-000017: no update for 60 s |
| 14:09:48 |   528.0 s | SENSOR | ACOUSTIC-01 first records **shahed_1** (135 records in all) |
| 14:09:53 |   533.0 s | SENSOR | RADAR-01 first records **INT-02** (10 records in all) |
| 14:10:00 |   540.0 s | SENSOR | RF-02 first records **shahed_1** (9 records in all) |
| 14:10:05 |   545.0 s | SENSOR | RF-01 first records **shahed_1** (11 records in all) |
| 14:10:10 |   550.0 s | C2 | WARN: LOST CONTACT TRK-000016: no update for 60 s |
| 14:10:16 |   556.0 s | SENSOR | RF-03 first records **shahed_1** (3 records in all) |
| 14:10:34 |   574.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000027 at 2157 m |
| 14:10:34 |   574.0 s | C2 | WARN: LOST CONTACT TRK-000021: no update for 60 s |
| 14:10:35 |   575.0 s | C2 | CRITICAL: CLOSE TO SITE-01: TRK-000024 at 990 m |
| 14:10:36 |   576.5 s | TRUTH | **shahed_2** intercepted (closest approach to SITE-01: 5278.0 m) |
| 14:10:36 |   576.5 s | TRUTH | **INT-02** at the rendezvous point |
| 14:10:36 |   576.8 s | C2 | INT-02 → no contact (no C2 track within 500 m at its end) |
| 14:10:57 |   597.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000029 at 2448 m |
| 14:11:00 |   600.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000026 at 2971 m |
| 14:11:34 |   634.0 s | C2 | WARN: LOST CONTACT TRK-000023: no update for 60 s |
| 14:11:35 |   635.0 s | C2 | WARN: LOST CONTACT TRK-000024: no update for 60 s |
| 14:11:38 |   638.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000031 at 1182 m |
| 14:11:41 |   641.0 s | C2 | WARN: LOST CONTACT TRK-000019: no update for 60 s |
| 14:11:50 |   650.0 s | C2 | CRITICAL: CLOSE TO SITE-01: TRK-000031 at 992 m |
| 14:12:02 |   662.5 s | TRUTH | **shahed_1** reaches SITE-01 (22.1 m) |
| 14:12:13 |   673.0 s | C2 | WARN: LOST CONTACT TRK-000026: no update for 60 s |
| 14:12:27 |   687.0 s | TRUTH | **orlan_1** track ends |
| 14:12:53 |   713.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000033 at 2266 m |
| 14:12:58 |   718.0 s | C2 | WARN: LOST CONTACT TRK-000008: no update for 60 s |
| 14:13:02 |   722.0 s | C2 | WARN: LOST CONTACT TRK-000031: no update for 60 s |
| 14:13:22 |   742.0 s | C2 | WARN: LOST CONTACT TRK-000030: no update for 60 s |
| 14:13:27 |   747.0 s | C2 | WARN: LOST CONTACT TRK-000028: no update for 60 s |
| 14:13:38 |   758.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000034 at 2417 m |
| 14:14:08 |   788.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000035 at 1863 m |
| 14:14:13 |   793.0 s | C2 | WARN: LOST CONTACT TRK-000033: no update for 60 s |
| 14:15:01 |   841.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000036 at 2011 m |
| 14:15:15 |   855.0 s | C2 | WARN: LOST CONTACT TRK-000035: no update for 60 s |
| 14:15:27 |   867.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000038 at 2007 m |
| 14:15:48 |   888.0 s | C2 | WARN: LOST CONTACT TRK-000018: no update for 60 s |
| 14:16:38 |   938.0 s | TRUTH | **geese_1** track ends |
| 14:16:46 |   946.0 s | C2 | WARN: LOST CONTACT TRK-000037: no update for 60 s |
| 14:16:51 |   951.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000039 at 2368 m |
| 14:17:18 |   978.0 s | C2 | WARN: LOST CONTACT TRK-000038: no update for 60 s |
| 14:17:37 |   997.0 s | C2 | WARN: SENSOR SILENT ACOUSTIC-01: no detections since 2026-11-04T14:16:37.000Z (CAM-01, RADAR-01, RF-01, RF-02, RF-03 still reporting) |
| 14:18:23 |  1043.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000040 at 2220 m |
| 14:19:29 |  1109.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000041 at 2225 m |
| 14:20:07 |  1147.0 s | C2 | WARN: LOST CONTACT TRK-000040: no update for 60 s |
| 14:20:52 |  1192.0 s | C2 | WARN: APPROACHING SITE-01: TRK-000042 at 2340 m |
| 14:20:59 |  1199.5 s | C2 | ADT-01 → no contact (no C2 track within 500 m at its end) |
| 14:20:59 |  1199.5 s | C2 | ADB-01 → no contact (no C2 track within 500 m at its end) |

## Outcome per hostile

| hostile | airborne | first sensor record | first C2 alert | truth outcome |
|---|---|---|---|---|
| gerbera_1 | 14:04:31 | 14:04:31 (+0 s) | none | intercepted |
| orlan_1 | 14:06:06 | 14:06:06 (+0 s) | 14:06:06 (+0 s) | approached |
| shahed_1 | 14:09:27 | 14:09:33 (+6 s) | none | reached |
| shahed_2 | 14:08:30 | 14:08:32 (+2 s) | none | intercepted |
| gerbera_2 | 14:02:36 | never | none | reached |
| gerbera_3 | 14:08:52 | 14:09:02 (+10 s) | none | reached |

## Audit (independent physics checks)

**7 pass · 1 fail · 2 skip**

| check | status | value |
|---|---|---|
| Provenance | PASS | 0 |
| Clock sync | PASS | 0 |
| Bearing geometry | PASS | 0.9304 |
| Terrain shadow | PASS | 24.46 |
| Occlusion gaps | SKIP | — |
| Fix calibration | PASS | 0.4888 |
| Range law | FAIL | 8.757 |
| Acoustic delay | PASS | 0.0176 |
| Spoof visibility | SKIP | — |
| Cross-sensor time | PASS | 1.0 |
