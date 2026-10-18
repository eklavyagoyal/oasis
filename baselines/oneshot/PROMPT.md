# One-shot LLM baseline: the exact prompt

Fairness matters: this is everything a careful human would hand an LLM — the scenario, the
sensor sites, the platform numbers, the exact file layout — plus the same requirement we hold
ourselves to ("physically realistic: terrain, bearings, signal strength"). Sent ONCE by
`make.py`; the answer is written into our own output layout and audited with the same checks.

---

You are an expert in RF direction finding, air-defence sensors and physical simulation.
Generate a synthetic but **physically realistic** sensor dataset for a drone-detection exercise
in the Ros river valley near Korsun-Shevchenkivskyi, Cherkasy, Ukraine (rolling farmland, a
river valley, two real comms masts on opposing ridges). Cover exactly the 10-minute dusk window
**14:07:00Z–14:17:00Z on Wed 4 Nov 2026**, i.e. `t = 18720..19320` seconds after the
08:55:00Z start. Only objects whose `start_s`/`end_s` overlap that window appear.

The scenario (object paths, times, receiver sites, platform numbers) is given below. Please make
the data physically realistic: **terrain, bearings, signal strength**. That means:

- bearings measured at a receiver are the true geometric bearing to the emitter, plus realistic
  DF error (a few degrees at high SNR, more when the signal is weak or reflected);
- signal strength follows distance and transmitter power — a drone behind a hill from a receiver
  must show markedly weaker power (or no detection at all), while the other receiver that sees it
  reports normal power;
- every timestamp is on one synchronized UTC clock, `t` and `time_utc` always agreeing;
- fixes are the least-squares crossing of the two receivers' bearings of the same emitter at the
  same second, with errors consistent with the bearing noise.

Files to produce (exact columns, compact CSV text, one row per detector report per second):

- `truth/tracks.csv` — `t,time_utc,object_id,lat,lon,alt_msl_m,alt_agl_m,x_m,y_m,z_m,vx,vy,vz,speed_mps,heading_deg,gnss_lat,gnss_lon,gnss_alt_msl_m`
  (`x_m`,`y_m` are metres east/north of the area centre 49.37 N, 31.20 E; `z_m` = `alt_msl_m`;
  `gnss_*` is what the object's own GNSS reports — honest here.)
- `sensors/RF1/detections.csv`, `sensors/RF2/detections.csv` — `record_id,time_utc,t,sensor_id,freq_mhz,bw_mhz,power_dbm,snr_db,bearing_deg,bearing_std_deg,sig_class,class_conf,emitter_id`
- `answer_key/RF1.csv`, `answer_key/RF2.csv` — `record_id,object_id,link,label,true_bearing_deg,true_range_m,los,path_loss_db,diffraction_db,shadow_db,fading_db,sinr_db,wild_bearing`
  (`link` is `<object_id>:<link name>` from the catalog, e.g. `mavic_1:video`; `label` is one of
  `target|friendly|clutter|false_alarm`, and `false_alarm` rows have empty `object_id`.)
- `fused/fixes.csv` — `fix_id,time_utc,t,lat,lon,hae_m,ce_m,cep50_m,semi_major_m,semi_minor_m,orient_deg,n_sensors,sig_class,freq_mhz,record_ids`
  (`record_ids` = the semicolon-joined detection ids crossed into the fix; `cep50_m` is the
  50%-containment radius you claim for the fix.)
- `answer_key/fused.csv` — `fix_id,object_id,label,error_m`

Conventions: `record_id` is `<sensor>-<n:06d>` counting each sensor's rows from 0; `time_utc` is
ISO 8601 with milliseconds and a `Z` (e.g. `2026-11-04T14:02:07.250Z`); bearings are degrees
true, clockwise from north, in [0, 360); power is dBm; ranges and heights are metres; frequencies
are MHz.

`sensors/RF1/site.json` and `sensors/RF2/site.json` are given and must not be included in your
answer (the receivers stand exactly where they say).

Answer with **one JSON object** mapping each of the seven file paths above to its complete CSV
text. No prose outside the JSON.

SCENARIO YAML:

{SCENARIO_YAML}

PLATFORM CATALOG (physical, RF and acoustic signature per object type):

{CATALOG_JSON}
