# Mirror World: RF emitters, IQ synthesis, SigMF and TAK/CoT formats

Research notes for the Psylone "Mirror World" challenge. Compiled 18 Oct 2026.

**Status legend**
- **[V]**: verified against a primary source (vendor manual, source code, spec, peer-reviewed paper), or run here as code.
- **[S]**: secondary source (press, OSINT blog, Wikipedia, retailer copy of a vendor spec).
- **[A]**: our modelling assumption. Not a fact.
- **[U]**: unverified or conflicting. Treat with care.

The WebSearch budget for this session ran out partway through. The items marked [U] could not be cross-checked a second time.

**Working code in the scratchpad (all of it runs)**
- `rf_emitters/code/iq_synth_demo.py`: numpy IQ synthesis that writes a SigMF recording. It validated with `sigmf` 1.13.0.
- `rf_emitters/code/cot_demo.py`: builds the CoT examples and replays them with pytak 7.6.1. The UDP loopback self-test received 7 of 7 events.
- `rf_emitters/code/make_dp.py`: builds an ATAK data package with `pytak.TAKDataPackage`.
- `rf_emitters/out/`: sample outputs (`rf1_2440MHz_snap.sigmf-{data,meta}`, `scenario_events.cot`, `mirrorworld_demo_dp.zip`).

The full paths start with `scratch/research/`.

---

## 0. Decisions that matter most for the generator

1. **Model the drone and the pilot as separate emitters.** For almost every class, the downlink (video, DroneID, telemetry) leaves the airframe and the uplink (RC) leaves the pilot.
   - DF on the downlink places the drone. DF on the uplink places the pilot.
   - A DJI DroneID decode gives both GPS positions directly. It is unencrypted on OcuSync 2.0-era drones [V NDSS'23].
   - Fibre-optic FPV has no RF at all.
2. **Duty cycle and hopping drive what a sensor actually "hears".**
   - Analog FPV video is a 100% duty, fixed-frequency carrier. It is the easiest to detect and DF, and the video can be intercepted.
   - ELRS and Crossfire TX are hopping bursts at 75-93% airtime.
   - DJI RC uplink is short FHSS bursts.
   - DroneID is a 0.64 ms burst every 640 ms.
   - Shahed-class drones are mostly GNSS receive-only, plus LTE or mesh modem bursts on some variants.
3. **Emit IQ only as short snippets.** Use 1-20 ms windows around scheduled bursts, plus a few context windows. Drive them from the same emitter schedule that produces the CoT and JSON detections. Continuous IQ is not feasible: one hour at 30.72 MS/s in ci16 is about 442 GB.
4. **Record truth in every format.**
   - SigMF annotations: `signal:emitter.label` = object uid, `spatial:emitter_location` = true position, plus a custom `mirror:` namespace.
   - CoT: a strippable `<__truth object_uid=…/>` detail, and `opex="s-…"` (simulation) on every event.
   - Join everything through a `record_uid → object_uid` table.
5. **For ATAK display, use what stock ATAK actually renders** (checked in the ATAK-CIV source):
   - a marker for each track;
   - `u-rb-a` (Range & Bearing line) for each LOB;
   - a `<sensor>` detail on the sensor marker for the FOV wedge;
   - `u-d-c-e` for error ellipses;
   - `u-d-f` for polylines.

   TAK's own `__lob` DF detail exists in the TAK XSDs, but stock ATAK has no renderer for it. Include it alongside for DF-aware consumers.

---

## 1. RF emission profiles

### 1.1 Master table

Abbreviations: UL = uplink (pilot/GCS → drone). DL = downlink (drone → ground). EIRP limits are regional regulatory maxima, not measured values.

| Platform | Link | Band / centre freq | Bandwidth | EIRP | Duty cycle / hopping | Notes | Source |
|---|---|---|---|---|---|---|---|
| DJI OcuSync 2.0 (Mini 2, Air 2/2S, Mavic 2) | DL video | 2.400-2.4835 / 5.725-5.850 GHz. 2.4 GHz centres on a 1 MHz grid at x.5 MHz (10 MHz mode: 2405.5-2477.5; 20 MHz mode: 2410.5-2472.5) | 10 or 20 MHz OFDM (40 MHz on M300 only). Up to 23 / 46 / 80 Mbps | ≤26 dBm FCC; ≤20 dBm CE/SRRC/MIC (2.4). ≤26 FCC/SRRC; ≤14 CE (5.8) | Near-continuous TDD OFDM on one channel; changes channel or band on interference [A ~85-95% duty]. Adaptive QPSK / 16QAM / 64QAM | Air 2 / Air 2S: 20 MHz only. Manual vs auto channel selection | [V] DJI Mini 2 manual; [V] DJI MSDK OcuSyncLink; [S] RTU 2025 |
| DJI OcuSync 2/3/4 RC (RC-N1, RC 2) | UL control | Same bands | FHSS bursts. RFUAV measured per-hop BW: Mini 3 3.5 MHz, Mini 4 Pro 6.5 MHz, Mavic 3 Pro 4.8 MHz, Avata 2 7 MHz, DJI FPV 5 MHz | RC-N1: <26 dBm FCC, <20 CE/SRRC/MIC (2.4); <26 FCC, <23 SRRC, <14 CE (5.8) | Bursts of 0.40-1.7 ms. Repeat parameter ("FHSDC") 2-6 ms. Pattern period 20-60 ms | NDSS: "control uplink uses frequency hopping with narrower [bandwidth]". Internal waveform unknown | [V] NDSS'23; [S] RFUAV Table 4; [V] DJI RC-N1 spec |
| DJI DroneID (OcuSync 2.0; still seen on newer models) | DL broadcast | 2399.5, 2414.5, 2429.5, 2444.5, 2459.5, 2474.5 MHz; 5741.5-5831.5 MHz in 15 MHz steps. Independent of the video channel | 600 data subcarriers + DC at 15 kHz, about 9 MHz occupied. FFT 1024 at 15.36 MS/s | Same radio as video | One 643 µs burst (9 symbols; Mavic 2 and older: 8 symbols, about 576 µs) **every 640 ms** (about 0.1% duty). 12-20 bursts per centre, then it hops | CP 72 samples (80 on symbols 1 and 9). ZC sync on symbols 4 and 6 (roots 600 and 147). QPSK, Gold-scrambled, LTE turbo code. **Unencrypted.** Carries drone lat/lon/alt/height, velocity, home point, app/pilot lat/lon, serial | [V] NDSS'23; [V] Bender 2022; [U] RTU 2025 says "10 times per second" |
| DJI O3 (Mavic 3; O3 Air Unit; Avata) | DL video | Mavic 3: 2.4 / 5.8 GHz. O3 Air Unit: TX on 5.725-5.850 only, RX only on 2.4 | 10 / 20 / 40 MHz. Air Unit centres: 40 MHz at 5794.5; 20/10 MHz at 5768.5 / 5804.5 / 5839.5 | Mavic 3: ≤33 FCC, ≤20 CE (2.4); ≤33 FCC, ≤30 SRRC, ≤14 CE (5.8). O3 Air Unit: <33 FCC, <14 CE, <30 SRRC | As OcuSync | 33 dBm = 2 W EIRP in FCC mode. Users commonly force FCC mode [U] | [V] DJI Mavic 3 downloads page; [V] DJI O3 Air Unit page |
| DJI O4 (Mini 4 Pro, Air 3/3S, Mavic 4 Pro, O4 Air Unit, Avata 2) | DL video and UL | 2.400-2.4835, **5.170-5.250**, 5.725-5.850 GHz | Up to **60 MHz** (O4 Air Unit Pro with Goggles 3: 60 or 40 MHz on 1 channel at 5794.5; 20 or 10 MHz on 3 channels from 5768.5) | Mini 4 Pro: <33 FCC, <20 CE (2.4); <23 CE (5.1); <33 FCC, <30 SRRC, <14 CE (5.8) | As OcuSync. Wider spread and more adaptive than Lightbridge (RTU) | Mavic 4 Pro / Matrice 4T are reported on 2.4, 5.2 and 5.8 GHz | [S] DJI spec copies (Clifton, Betta, GetFPV); [S] Euromaidan 2025 |
| DJI Lightbridge (Phantom 4 Pro v1, Inspire 2, M200) | DL video and UL | 2.400-2.483 / 5.725-5.825 GHz | About 10 MHz observed (P4 within 2415-2425 MHz) [S] | RC: FCC 26, CE 17, SRRC 20 dBm (2.4); FCC 28, CE 14, SRRC 20 dBm (5.8) | "Fixed frequency hopping pattern", strong periodic peaks | Range 7 km FCC | [V] DJI P4 Pro manual; [S] RTU 2025 |
| DJI Wi-Fi drones (Spark, Mavic Air, Mini SE …) | DL | 2.4 / 5.8 GHz Wi-Fi | 802.11. DroneID beacons at 5 MHz width | — | Beacon frames | DroneID rides in a vendor-specific IE in the beacon. DJI MAC OUIs 60-60-1F, 34-D2-62, 48-1C-B9 | [V] Bender 2022 |
| Analog FPV VTX (5.8 GHz) | DL video | R band 5658/5695/5732/5769/5806/5843/5880/5917 MHz. Also A, B, E, F and L bands (5333-5945) | FM composite video. Channel allocation about 30 MHz. Video baseband 0-8 MHz; audio subcarrier 6.5 MHz. [A] 99% occupied BW about 17.5 MHz at 8 MHz peak deviation | 25 mW-2.5 W (hobby). Military VTXs are multi-watt; Chuyka range specs assume a **4 W** VTX | **Continuous (100%)**, fixed frequency, no hopping | Easiest target to detect and DF. Detectors show the intercepted video | [V] TBS manual band table; [S] Oscar Liang; [S] Lumenier spec; [S] Chuyka 4.0 |
| Analog FPV, non-standard bands | DL video | "1.2 GHz" (detectors cover 900-1800 or 1080-2200 MHz); "3.3 GHz" (2870-4080 / 2860-4500 MHz); 4.9 GHz (in the 4860-6060 sweep); **6-7.2 GHz** (Russian "Boomerang" FPV, Jul 2026); up to 8.8 GHz (Chuyka 4.0 band) | As above | As above | Continuous | Older detectors stop near 6 GHz. Newer ones add a 4th band up to ≥7.2 GHz | [S] BlueBird Chuyka 3.0; [S] FlashArmy Chuyka 4.0; [S] Militarnyi 2026; [U] militaeraktuell (6.7 and 7.2 GHz Ukrainian VTX) |
| ExpressLRS 900 MHz (SX127x / LR1121) | **UL control** (pilot) | FCC915: 903.5-926.9 MHz, 40 ch. EU868: 863.275-869.575 MHz, 13 ch. Also AU915 / IN866 / 433-MHz domains (US433W 423.5-438 MHz). Firmware is often modded off-band | LoRa BW 500 kHz: SF6 200 Hz, SF7 100 Hz, SF8 50 Hz, SF9 25 Hz. LR1121 adds GFSK 1000 Hz (300 kbps, ±100 kHz) | 10 / 25 / 50 / 100 / 250 / 500 / 1000 / 2000 mW | Time on air per packet: 4.38 of 5 ms (200 Hz, 88%), 8.77 of 10 ms, 18.56 of 20 ms, 29.95 of 40 ms. Hops every 4 packets (2 at 25 Hz) over a seeded permutation plus a sync channel | Seed comes from the binding phrase. Sensitivity -112 to -123 dBm | [V] ELRS `common.cpp`, `FHSS.cpp`, `POWERMGNT.h` |
| ExpressLRS 2.4 GHz (SX1280) | UL control | 2400.4-2479.4 MHz, 80 ch, 1 MHz spacing | LoRa BW 812.5 kHz: SF5 500 Hz, SF6 250 Hz, SF7 150 Hz, SF8 50 Hz. FLRC 650 kbps (BW 0.6 MHz) at 1000 / 500 Hz | As above | Time on air: 1.507 of 2 ms (500 Hz), 3.30 of 4 ms (250 Hz), 5.87 of 6.67 ms (150 Hz), 0.389 of 1 ms (F1000) | DVDA modes repeat each packet 2× or 4× | [V] ELRS source |
| ELRS / CRSF receiver telemetry | **DL** (drone) | Same channels (TDD slot) | Same modulation | Typically ≤100 mW [U] | 1 slot in N, with N = 2…128 (defaults 1:64 at 200/250 Hz, 1:8 at 25 Hz). The **"Disarmed"** setting means **no telemetry while armed** | So the drone is usually almost silent on the control link | [V] ELRS `common.h` |
| TBS Crossfire | UL and DL | 868 mode: 860.165-885.905 MHz. 915 mode: 902.165-927.905 MHz. CE mode: 863.093-868.581 MHz | 150 Hz mode: 2-FSK, 85.1 kBd, ±42.48 kHz. 50 Hz mode: LoRa. 4 Hz mode | TX 10 mW-2 W. RX telemetry 40 mW (Nano RX Pro up to 500 mW). CE mode: 25 mW with LBT | 6.666 ms frame: TX on channel N (23 B), RX replies on N+50 (13 B) within 2.6 ms. Sequence of 150 hops; 50+50 channels at 260 kHz. Falls back from 150 Hz to 50 Hz on poor link quality | **The drone transmits every frame**, so both ends can be DF'd | [V] TBS manual; [S] g3gg0 reverse engineering |
| Digital FPV: Walksnail / DJI-FPV style | DL video (+ goggle UL) | 5.725-5.850 GHz. FCC channels 5660 / 5695 / 5735 / 5770 / 5805 / 5878 / 5914 / 5839 | 20 MHz (25 Mbps) or 40 MHz (50 Mbps) | O3 / O4 as above | Continuous OFDM | With an O3 Air Unit the goggles transmit back on 2.4 GHz, so the pilot is visible | [S] Oscar Liang; [V] DJI O3 page |
| Digital FPV: HDZero | DL video | Raceband R1-R8 (+ F2, F4). CE uses a subset | 27 MHz standard; 17 MHz "narrow" (540p60) | Not found | Continuous, fixed frequency | Goggles are probably receive-only [U]. Control rides on ELRS or Crossfire | [S] Oscar Liang; [S] IntoFPV |
| Fibre-optic FPV (e.g. KVN) | none | No RF link | — | — | — | "No thermal or radio signature". RF detection "will not work" (Beskrestnov). Detect by acoustic, radar or EO only. Typical fibre 5-20 km, prototypes to 50 km. Residual or spurious emissions are undocumented [U]: model as silent | [S] Wikipedia; [S] Euromaidan 2025 |
| Orlan-10 | UL C2 and DL telemetry | 850-930 MHz (teardown: 902-928 MHz module, 915 MHz λ/4 dipole; spectrogram near 921-922 MHz). Trend toward 730-760 MHz and 430-600 MHz | Narrowband with pseudo-random hopping (TASS) | Not found | Continuous link | Also listed: 200-450, 867-872, 915-920, 860-1000 MHz, 1.08-1.30 GHz, 2.5-2.7 GHz (Armada) | [S] Wikipedia; [S] Armada 2024; [S] InformNapalm (via search) |
| Orlan-10 | DL imagery | "3, 4 and 8 GHz". Video board built on an AD9361 | 2-16 Mbit/s (TASS) | Not found | Continuous | Flies at 1-1.5 km altitude, ≤150 km/h, 16 h endurance, groups of 2-3, one aircraft acting as relay. Leer-3 EW variant | [S] Wikipedia; [S] Ampheo |
| ZALA Lancet | UL and DL C2 | 867-872 and 902-928 MHz: "two primary channels + a reserve" | Narrowband (Semtech XE1205 FSK transceiver) | Not found | Continuous | Video radio is wideband (AD9364); its band is unknown, Armada lists 2.2-2.4 GHz [U]. Sources conflict on relaying via Supercam | [S] Militarnyi; [S] Armada; [S] Ampheo |
| Supercam S350 | C2 / video | 976.5-1021.5, 1033.5-1115.05 and 1110.55-1222.25 MHz. Also 11.775 GHz (purpose unknown) | Not found | Not found | Continuous | C2 range 100 km; video 70-100 km; relays for loitering munitions | [S] Armada 2024; [S] TASS |
| Shahed-136 / Geran-2 | GNSS (receive only) | GLONASS/GPS through a "Kometa" CRPA (8 or 12 elements, 16 reported in 2025) | — | **0 (passive)** | — | Moped-like engine, about 185 km/h, low altitude | [S] Wikipedia; [S] GUR; [U] www1.ru |
| Shahed / Geran-2 | Cellular DL (UE uplink) | Ukrainian and Russian 2G/3G/4G bands, SIM-based (Kyivstar found in late 2023). "Almost all" carried 2G/3G/4G antennas by early 2026 | LTE UE | UE class, about 23 dBm [A] | Bursty, only while attached and reporting | Position reporting. Detectable by ESM | [S] TWZ; [S] Wikipedia |
| Shahed / Geran-2/5, Gerbera | Mesh DL/UL video and C2 | **XK-F358** COFDM mesh (since Jul 2025; serial fit by Sep 2025). Datasheet bands: UHF 430-950 MHz, L 1.0-1.5 GHz, S 1.6-2.9 GHz, C 4.4-6.0 GHz | 1.25 / 2.5 / 5 / 10 MHz (other listings up to 40 MHz) | 2 × 10 W (TPC) | "Full band adaptive frequency hopping", AES | Each drone relays for the others; 100-300 km line of sight per hop. **The band actually used on Gerans is unknown [U]** | [S] Euromaidan 2026; [S] Xingkai datasheet |
| Shahed / Geran-2 | Satcom | Starlink terminal (Sep 2024; Starlink control by Jan 2026). Ku-band user uplink about 14.0-14.5 GHz [U] | — | — | — | — | [S] Wikipedia |
| Gerbera decoy | Various | Recon variant: XK-F358 plus Topotek KHY10S90 camera. One find: 3G/4G modem with SIM | — | — | Many decoys likely RF-silent [A] | Plywood and foam; ≤160 km/h; ≤3,000 m; 300-600 km range. About half of launched drones were decoys (Nov 2024) | [S] Wikipedia; [S] GUR via search |
| UA interceptors (Sting, P1-SUN …) | UL / DL | **Not public.** Sting is flown with VR goggles or "Hornet Vision Control" remotely (up to 2,000 km over network backhaul). Some interceptor fleets depended on Starlink/Starshield (speed cap from 14 Oct 2026) | — | — | — | Sting: 315-343 km/h, 25 km range, Kurbas-640 thermal camera. **[A] Model as an FPV-class link**: ELRS/Crossfire-class control plus digital or analog video and a ground relay | [S] Wikipedia; [S] DroneXL 2026 |

### 1.2 Who emits what (DF implications)

| Class | Drone emits | Pilot / GCS emits | What a DF network can locate |
|---|---|---|---|
| DJI OcuSync / O3 / O4 | Video DL, 10-60 MHz, near-continuous; DroneID every 640 ms | RC UL hopping bursts of 3-7 MHz, 0.4-1.7 ms each | The drone from DL bearings, the pilot from UL bursts. A DroneID decode gives both from a single packet [V NDSS] |
| Analog FPV + ELRS | FM video, fixed frequency, 100% duty; ELRS telemetry rare or off | ELRS TX: 75-93% airtime, hopping 13-80 channels | The drone from the video carrier, the pilot from ELRS |
| Analog FPV + Crossfire | FM video plus 150 Hz Crossfire replies | Crossfire TX up to 2 W | Both |
| Digital FPV (DJI O3 / O4) | 5.8 GHz OFDM | Goggles / RC transmit (O3 air unit receives on 2.4 GHz) | Both |
| Fibre-optic FPV | Nothing | Nothing | Nothing in RF |
| Orlan / Supercam / Lancet | UHF C2 and telemetry plus wideband imagery | GCS UHF uplink, often tens of km away | The drone, and the GCS only within line of sight |
| Shahed / Gerbera | Nothing, or LTE bursts, mesh COFDM, or Starlink | Remote over network | The drone, intermittently, depending on variant |

### 1.3 Ukraine-specific notes
- **EW drives frequency changes** [S Euromaidan 2025].
  - One brigade's experience: a single 900 MHz jammer module stopped being enough by spring 2024.
  - By summer it took 4-5 modules, and by autumn 7. Russian control links spread over **750-1050 MHz**.
  - Fibre-optic FPV was the turning point by the end of 2024.
- **Detector band plans tell you where FPV video actually lives.**
  - Chuyka 3.0 sweeps 900-1800, 2870-4080 and 4860-6060 MHz in ≤10 MHz steps, with a 4-8 s full cycle.
  - Chuyka 4.0 adds 6040-8800 MHz [S].
  - In 2026, Russian "Boomerang" FPV moved video to 6-7.2 GHz, above most older detectors [S Militarnyi].
- **ELRS firmware ships 433 MHz domains** (US433W 423.5-438 MHz) [V]. Military users patch it to custom ranges [U].
- **Antenna patterns** [A]: pilot TX antennas are often directional (moxon or patch, 3-9 dBi) aimed at the drone. A DF site behind or beside the pilot sees a lower EIRP. Model the antenna pattern, not just the EIRP.

---

## 2. IQ synthesis with numpy

### 2.1 Architecture
For each scenario, keep one **emitter schedule** per (object, link): bursts with t_start, duration, f_c, bandwidth, EIRP, waveform id and a seed.

For each sensor and each chosen **window** (t0, fs, f_c, duration):
1. Pick the bursts that overlap the window and fall inside the instantaneous bandwidth (`|f - f_c| < fs/2`).
2. Generate the baseband waveform with a seeded RNG, so it is reproducible.
3. Scale it by the received power: P_rx = EIRP + G_rx(az, el) − PL(terrain) − fading.
4. Apply Doppler, CFO and multipath, mix to the offset (f − f_c), and add AWGN at the thermal floor.
5. Write SigMF with one annotation per burst.

The same schedule produces the detection records (CoT and JSON), so timestamps match by construction. The capture `core:datetime` plus `sample_start/fs` equals the burst time in the truth log.

**Noise floor**: N = −174 dBm/Hz + 10·log10(fs) + NF. Example: fs = 30.72 MS/s with NF = 6 dB gives −93.1 dBm. Normalise so that a mean sample power of 1.0 equals N. Then SNR = P_rx − N falls out physically, and SigMF `core:description` can state the scale.

### 2.2 Waveform recipes (implemented in `iq_synth_demo.py`; measured on our generator)

| Waveform | Construction | Measured duration | Measured 99% occupied BW |
|---|---|---|---|
| DJI DroneID [V params] | 9 OFDM symbols, FFT 1024·k at 15.36·k MS/s, CP [80, 72×7, 80]·k, 600 QPSK subcarriers ±300 around DC. Symbols 4 and 6 carry ZC root 600 and root 147 (length 601, middle element removed). A self-check correlation gave \|ρ\| = 1.000 | 0.643 ms (8-symbol variant: 0.571 ms) | 8.94 MHz |
| OcuSync video DL [A numerology] | LTE-like: 15 kHz spacing, 600 / 1200 / 2400 subcarriers for 10 / 20 / 40 MHz, 16 / 64QAM, normal CP | continuous | 8.94 MHz (10 MHz mode) |
| DJI RC UL hop [A internals; S params] | Short QPSK OFDM burst, 3-7 MHz wide, 0.4-1.7 ms long, hopping on an RFUAV-like cadence | 0.50 ms | 3.0 MHz |
| LoRa CSS (ELRS, Crossfire 50 Hz) [V params] | N = 2^SF chips, T_s = N/BW, f(t) = −BW/2 + BW·frac(k/N + t/T_s). Preamble of 8-14 upchirps, 2 sync symbols (8, 16), 2.25 downchirps, then payload length set to the ELRS time on air | 3.33 ms (SF6 / 812.5 kHz) | 0.89 MHz; 0.55 MHz for SF6 / 500 kHz |
| 2-FSK (Crossfire 150 Hz) [S params] | 85.1 kBd, ±42.48 kHz, 16-bit 0101 preamble plus 23 B | 2.54 ms | 182 kHz |
| Analog FPV FM [A deviation] | PAL-like composite: 64 µs line, 4.7 µs sync, black level 0.3, active video 0.3-1.0, plus a 6.5 MHz FM audio subcarrier, all FM-modulated at a peak deviation of 8 MHz | continuous | 17.4-17.7 MHz (6 MHz deviation gives 13 MHz; 10 MHz gives 22 MHz) |
| Wi-Fi 802.11a/g-like (clutter) | At 20 MS/s: STF-like (every 4th subcarrier, 10 × 0.8 µs), LTF-like (GI2 + 2 × 3.2 µs), 52-subcarrier 16QAM symbols with 0.8 µs GI. FFT-resampled to fs | 0.26 ms (60 symbols) | 16.45 MHz |

Other useful clutter:
- **Bluetooth Classic**: GFSK, 1 Msym/s, 79 × 1 MHz channels, 1600 hops/s.
- **BLE**: 40 × 2 MHz channels; advertising on 2402, 2426 and 2480 MHz.
- **Wi-Fi beacons**: every 102.4 ms.
- **LTE eNB / UE**.

(These are standard figures, not re-fetched here.)

**Channel and receiver effects** (all [A], standard engineering):
- **Doppler**: f_D = v·f/c. A DJI at 30 m/s and 2.44 GHz gives 244 Hz. A Shahed at 51 m/s and 5.8 GHz gives about 990 Hz. An interceptor at 95 m/s gives 1.8 kHz.
- **CFO**: ±10-20 ppm, i.e. ±24-49 kHz at 2.44 GHz. The RUB decoder logged an offset of −6.5 kHz on a real Mini 2.
- **Fading**: Rician for line of sight (K of 6-10 dB) and Rayleigh for NLOS. Add a 2-ray ground reflection for low-altitude links.
- **NLOS**: knife-edge or ITU-R P.526 diffraction loss from the terrain profile, plus a bearing bias toward the diffracting edge or reflector. This is the brief's "behind a hill" faithfulness test.
- **DF arrays**: write multichannel IQ, either `core:num_channels` = M interleaved or a SigMF Collection with the `spatial` extension. Apply a per-element steering vector a(θ), e.g. a uniform circular array with a_m = exp(j·2πr/λ·cos(θ − 2πm/M)). Then the bearing is recoverable from the IQ itself, not just stated in metadata.

### 2.3 Sample rates, durations and file sizes

- **Bytes per complex sample**:
  - `cf32_le`: 8 B (RFUAV, DroneDetect, our demo)
  - `ci16_le`: 4 B (USRP-style)
  - `ci8`: 2 B (HackRF native `.cs8`)
- **Sample rate per target**:
  - DroneID / OcuSync 10 MHz: ≥15.36 MS/s.
  - 20 MHz video: 30.72 MS/s.
  - 40 MHz: 61.44 MS/s (the AD9361 maximum).
  - The whole 2.4 GHz ISM band (83.5 MHz): 100 MS/s, as RFUAV and DroneRFa use. DroneRF used 2 × 40 MHz.
  - A single ELRS 900 channel: 1-2 MS/s. The whole FCC915 hop set (23 MHz): 25-30 MS/s.
  - Analog FPV: ≥25-30 MS/s.
- **Window lengths**:
  - DroneID needs ≥640 ms on the right centre frequency to catch one burst. The RUB receiver scanned each band for 1.3 s at 50 MS/s.
  - ELRS packets last 0.4-30 ms. Crossfire frames repeat every 6.67 ms. A 20 ms window catches several.
- **Measured sizes**:
  - 20 ms at 30.72 MS/s in cf32 = 4.92 MB (our demo).
  - 1 s at 100 MS/s in cf32 = 800 MB.
  - 1 h at 30.72 MS/s in ci16 = 442 GB, so continuous capture is not feasible.
- **Policy**: emit IQ snippets only.
  - Per sensor, one window every N seconds, plus "event" windows triggered by the schedule (first detection, a DroneID burst, a new hop set).
  - Seed each snippet as hash(scenario, sensor, window) so any snippet can be regenerated on demand.

### 2.4 SigMF essentials (spec v1.2.6) [V]

**Files**
- `.sigmf-meta` (UTF-8 JSON) plus `.sigmf-data` (raw samples, no header).
- `.sigmf` is a tar archive; `.sigmf-collection` groups several recordings, e.g. multichannel DF.

**`global`**
- Required: `core:datatype` (e.g. `cf32_le`, `ci16_le`, `cu8`; byte types take no endianness suffix) and `core:version`.
- Optional: `core:sample_rate`, `core:author`, `core:description`, `core:hw`, `core:num_channels`, `core:sha512`, `core:extensions`, `core:geolocation`, `core:recorder`, `core:license`, `core:collection`, `core:metadata_only`.

**`captures`**
- `core:sample_start` (required), `core:frequency` (Hz), `core:datetime` (RFC 3339, `Z` only), `core:global_index`, `core:geolocation`.
- Must be sorted by start sample. Keys do **not** carry over between segments.
- Geolocation is a GeoJSON Point, `[lon, lat, alt_m]`.

**`annotations`**
- `core:sample_start` (required), `core:sample_count`, `core:freq_lower_edge` and `core:freq_upper_edge` (both or neither), `core:label` (recommended ≤20 characters), `core:comment`, `core:generator`, `core:uuid`.
- Must be sorted by start sample.

**Extensions** are declared in `global.core:extensions` as `[{name, version, optional}]`. The useful canonical ones:
- **`signal` v1.0.0**:
  - `signal:detail` with `type`, `mod_class` (fm/psk/qam/fsk…), `standard`, `order`, `duplexing`, `multiplexing` (ofdm), `spreading` (fhss/css/dsss), `channel_bw`, `channel`.
  - `signal:emitter` with `seid`, **`label`**, `manufacturer`, `power_tx`, `power_eirp`, `geolocation`.
- **`spatial` v1.1.0**:
  - Captures: `aperture_azimuth`, `emitter_bearing`, `element_geometry`.
  - Annotations: **`signal_azimuth`**, `signal_bearing{azimuth, elevation, range, az_error…}`, **`emitter_location`** (GeoJSON).

**Labelling scheme for "which object":** per burst, set
- `core:label`, e.g. "DJI DroneID";
- `signal:emitter.label` = "uav-0007/droneid", plus `seid`;
- `spatial:emitter_location` = the true position;
- custom keys `mirror:object_uid`, `mirror:link` (uplink / downlink / clutter), `mirror:rx_power_dbm` and `mirror:snr_db`, with `{"name": "mirror", "version": "0.1.0", "optional": true}` declared.

`sigmf` 1.13.0 validated this with no complaints.

**Python package `sigmf`**:
- Version 1.13.0, released 2026-08-19. Requires Python ≥3.10. Implements spec v1.2.6. Installs as `SigMF`, `import sigmf`.
- API used and verified:

```python
from sigmf import SigMFFile, sigmffile
x.astype(np.complex64).tofile("snap.sigmf-data")            # cf32_le on x86/ARM
m = SigMFFile(data_file="snap.sigmf-data", global_info={
    "core:datatype": "cf32_le", "core:sample_rate": 30.72e6, "core:version": "1.2.6",
    "core:extensions": [{"name": "signal", "version": "1.0.0", "optional": True},
                        {"name": "spatial", "version": "1.1.0", "optional": True},
                        {"name": "mirror", "version": "0.1.0", "optional": True}]})
m.add_capture(0, metadata={"core:frequency": 2440e6, "core:datetime": "2026-10-18T07:32:10.000000Z"})
m.add_annotation(95232, 19760, metadata={
    "core:freq_lower_edge": 2440.0e6, "core:freq_upper_edge": 2449.0e6, "core:label": "DJI DroneID",
    "signal:emitter": {"seid": 7, "label": "uav-0007/droneid", "manufacturer": "DJI", "power_eirp": 20.0},
    "spatial:emitter_location": {"type": "Point", "coordinates": [31.1870, 49.3765, 250.0]},
    "mirror:object_uid": "uav-0007", "mirror:link": "downlink"})
m.tofile("snap.sigmf-meta", overwrite=True); m.validate()
r = sigmffile.fromfile("snap"); r.get_annotations(); r.read_samples(start_index=95232, count=19760)
```

### 2.5 Public drone RF datasets (realism references)

| Dataset | Year | Content | Receiver / rate | Format / size | Use for us |
|---|---|---|---|---|---|
| DroneRF [S] | 2019 | 3 drones (Parrot Bebop, Parrot AR, DJI Phantom 3) plus background; 4 flight modes | 2× NI USRP-2943R, 40 MHz each (80 MHz across the 2.4 GHz band), 14-bit | **Real amplitude** in CSV, 227 segments × 2 halves × 1 M samples, BUI-coded filenames, >40 GB | Lacks IQ, so use it only as a cautionary example |
| DroneDetect V2 [S] | 2021 | 7 drones (Mavic 2 Air S, Mavic Pro, Mavic Pro 2, Inspire 2, Mavic Mini, Phantom 4, Parrot Disco); clean / BT / Wi-Fi / BT+Wi-Fi subsets; on / hover / fly | Nuand BladeRF, fc 2.4375 GHz, 60 MS/s, 28 MHz BW | `.dat` interleaved float complex, 1.2e8 samples (2 s) per recording, 65.76 GB | Template for interference mixing |
| CardRF [S] | 2022 | UAVs, UAV controllers, Bluetooth, Wi-Fi (2.4 GHz) | 5 M points over 0.25 ms, about **20 GS/s** (oscilloscope) | `.mat`, 66 GB | Controller (uplink) fingerprints |
| DroneRFa [S] | 2024 | 24 UAV / controller types plus background; 915 MHz, 2.4 and 5.8 GHz; indoor hover and outdoor near/mid/far | USRP, **100 MS/s**, dual-channel; segments >1e8 samples | `.mat` likely [U]. J. Electron. Inf. Technol. 46(4):1147-1156 | Includes the 915 MHz band |
| RFUAV [S] | 2025 | 37 types (DJI Mini 3 / Mini 4 Pro / Mavic 3 Pro / FPV / Avata 2, Autel, Futaba, FrSky, FlySky, RadioMaster, SIYI, Skydroid, Herelink …) | 2× USRP X310, **100 MS/s**, SNR 10-48 dB | Interleaved fp32 IQ plus a USRP-settings XML, about 1.3 TB. **Table 4 gives per-drone hop BW, burst duration, pattern period and video BW** | Best parameter source for UL hopping |
| DRFF-R2 [S] | 2026 | 26 units, 8 DJI models, 7 scenarios (multi-drone, hopping, absorber, Wi-Fi mix) | 2× USRP-2943, 100 MS/s, 5.745 / 2.437 GHz | MAT with `RF0_I/RF0_Q/Fs/CenterFrequence/Gain/Distance/Height/FlightMode`, about 1.4e8 samples per segment | Multi-drone mixtures |

None of these are SigMF. Shipping ours as SigMF with per-burst object labels is a genuine differentiator.

---

## 3. TAK / Cursor-on-Target

### 3.1 Event schema essentials [V: MITRE base-event XSD and examples in TAK-Product-Center/atak-civ `takcot/`]

**`<event>` attributes**
- `version="2.0"`.
- `uid`: the latest event for a uid overwrites earlier ones.
- `type`.
- `how`.
- `time`, `start`, `stale`: xs:dateTime, UTC `…Z`.
- Optional: `opex` (`o`, `e` or `s`; e.g. `s-mirrorworld` marks the event as a simulation), `qos`, `access`.

**`<point>`**
- `lat` and `lon` (WGS-84), `hae` (m, height above ellipsoid).
- `ce` and `le`: 1-σ circular and linear error in metres. 9999999 means unknown.

**`<detail>`**: free-form. Common TAK details:
- `<contact callsign>`;
- `<remarks>`;
- `<track course speed>` (degrees true, m/s);
- `<link uid type relation>`;
- `<__video url>`;
- `<sensor …>`;
- `<color>`, `<strokeColor>`, `<strokeWeight>`, `<fillColor>` (signed ARGB int: −256 = opaque yellow, −65536 = red).

**`type` codes** (MITRE CoTtypes.xml; the second letter is the affiliation: `f` friend, `h` hostile, `u` unknown, `n` neutral, `a` assumed friend, `s` suspect, `p` pending, `j` joker, `k` faker):
- `a-.-A-M-F-Q`: Air / Mil / Fixed / **Drone, RPV, UAV**. Use for Shahed, Gerbera, Orlan, Lancet.
- `a-.-A-M-H-Q`: Air / Mil / Rotor / **Drone**. Use for DJI, FPV, interceptors.
- `a-.-A-C-F-q`: Air / Civ / fixed / RPV, drone, UAV (lower-case `q` is a CoT extension).
- `a-u-A`: generic unknown air, as in the brief's example.
- `a-.-A-W-M`: missile in flight.
- `a-.-G-U-C-V-U`: ground unit, unmanned aerial vehicle. Use for the **pilot / GCS** fix.
- `a-.-G-E-S`: ground equipment sensor. Use for **our RF / EO sensors**. Also `a-.-G-E-S-R` (radar).
- SIGINT bits: `b-r-.-I-A-S-C-O` (air signal intercept, comms, omni line of sight).

Examples:
- unknown DJI: `a-u-A-M-H-Q`
- hostile Shahed: `a-h-A-M-F-Q`
- friendly interceptor: `a-f-A-M-H-Q`

**`how` codes** (CoTtypes.xml):

| Code | Meaning |
|---|---|
| `h-e` | estimated |
| `h-c` | calculated |
| `h-t` | transcribed / retyped |
| `h-p` | pasted |
| `h-g-i-g-o` | GIGO |
| `m-g` | GPS |
| `m-g-n` | INS+GPS |
| `m-g-d` | DGPS |
| `m-i` | mensurated |
| `m-m` | magnetic |
| `m-n` | INS |
| `m-s` | **simulated** |
| `m-c` | configured |
| `m-r` | **radio** (the brief uses this for DF fixes) |
| `m-r-d` | doppler |
| `m-r-e` / `m-r-p` / `m-r-v` / `m-r-t` | EPLRS / PLRS / VHF / TADIL |
| `m-p` | passed / propagated |
| `m-f` | **fused** |
| `m-a` | tracker |

Suggested usage: DF fixes `m-r`, fused tracks `m-f`, ground truth `m-s`.

**`link` relations** (CoTtypes.xml):

| Code | Meaning |
|---|---|
| `p` | parent |
| `p-p` | **producer** |
| `p-o` | owner |
| `c` | child |
| `c-c` | correlated |
| `c-f` | **fused element** |
| `c-p` | composite |
| `r` | refinement |
| `t-…` | tasking |

Provenance pattern: a fix links its sensors with `p-p` and its LOBs with `c-f`.

### 3.2 What stock ATAK draws [V: ATAK-CIV source]

- **Line of bearing → `u-rb-a`** (`RangeAndBearingImporter`).
  - Start point = `<point>`.
  - The end point is computed as `pointAtDistance(anchor, bearing, range)`. `range` is always in **metres** and `bearing` in **degrees true**. `rangeUnits`, `bearingUnits` and `northRef` are display preferences only (range: 0 km, 1 m …; bearing: 0 degrees; north: 0 true).
  - Optional `inclination`, `color`.
  - **`anchorUID`** pins the line to an existing marker such as the sensor.
- **TAK DF schema `__lob`** (`takcot/xsd/details/__lob.xsd`).
  - Attributes: `azimuth` (degrees true, required), `family`, `deviceType`, `unitId` (all required), plus `rssi` (dBm), `elevationAngle`, `sourceTxPower`, `confidence`, `deviceTime`.
  - Children: `signalInfo` (e.g. `<__rf frequency="Hz" rssi>`; also `__wifi`, `__lte`, `__gsm`, `__radar`, `__identifiedRadio`, with an optional `__targetLocation` and `errorRadius`) and `__startLocation`.
  - **No renderer in core ATAK-CIV** (only the XSD turned up in the repo), so carry it **inside** the `u-rb-a` event.
- **Sensor / camera FOV → `<sensor>` detail on a marker** (`SensorDetailHandler`).
  - Draws a wedge only if `azimuth`, `fov` **and** `range` are all present.
  - **Include `elevation`**: ground range = range·cos(elevation), and the default for a missing elevation is NaN.
  - Optional: `vfov`, `roll`, `model`, `rangeLines`, `fovRed` / `fovGreen` / `fovBlue` / `fovAlpha` (0-1), `strokeColor`, `strokeWeight`, `hideFov`, `displayMagneticReference`.
  - Maximum range 60,000 m.
- **Polyline → `u-d-f`** with ≥2 `<link point="lat,lon"/>`. Repeating the first point gives a closed polygon.
- **Ellipse → `u-d-c-e`**: `<shape><ellipse major minor angle/></shape>`.
  - The importer halves major and minor, so they are **full axis lengths in metres**.
  - Circle `u-d-c-c` uses `minor` as the radius.
  - Angle convention not tested on a device [U].
- **Video**: `<__video url="rtsp://…"/>` on a marker.

### 3.3 Minimal valid XML (generated by `cot_demo.py`, round-tripped through `defusedxml`)

Timestamps below are T0 = 2026-10-18T07:32:10Z plus offsets. Re-stamp them on replay (see 3.4).

```xml
<!-- RF sensor with FOV wedge -->
<event version="2.0" uid="sensor-RF1" type="a-f-G-E-S" how="h-e" time="2026-10-18T07:32:10.000Z" start="2026-10-18T07:32:10.000Z" stale="2026-10-18T08:32:10.000Z" opex="s-mirrorworld">
  <point lat="49.3600000" lon="31.1800000" hae="180.0" ce="5.0" le="5.0"/>
  <detail><contact callsign="RF1"/>
    <sensor azimuth="10.0" fov="90.0" range="8000" elevation="0" fovRed="0" fovGreen="1" fovBlue="1" fovAlpha="0.15"/></detail>
</event>

<!-- Line of bearing: drawn by stock ATAK; __lob for DF-aware tools; __signal = brief; __truth = strip for blind eval -->
<event version="2.0" uid="lob-RF1-0001" type="u-rb-a" how="m-r" time="2026-10-18T07:32:13.100Z" start="2026-10-18T07:32:13.100Z" stale="2026-10-18T07:32:28.100Z" opex="s-mirrorworld">
  <point lat="49.3600000" lon="31.1800000" hae="180.0" ce="9999999.0" le="9999999.0"/>
  <detail><range value="8000"/><bearing value="16.3"/><inclination value="0"/><anchorUID value="sensor-RF1"/>
    <rangeUnits value="1"/><bearingUnits value="0"/><northRef value="0"/><color value="-256"/><strokeColor value="-256"/><strokeWeight value="2.0"/>
    <contact callsign="LOB 2444.5 MHz"/>
    <__lob azimuth="16.3" rssi="-80.6" confidence="80" family="mirror-world" deviceType="RF-DF 4-ch" unitId="sensor-RF1">
      <__rf frequency="2444500000" rssi="-80.6"/><__startLocation lat="49.36" lon="31.18" hae="180" ce="5" le="5"/></__lob>
    <__signal sensor="sensor-RF1" freq_mhz="2444.5" power_dbm="-80.6" bearing_deg="16.3"/>
    <__truth object_uid="uav-0007" link="downlink"/></detail>
</event>

<!-- DF fix from crossed bearings (brief format + provenance links) -->
<event version="2.0" uid="sig-0007" type="a-u-A" how="m-r" time="2026-10-18T07:32:13.400Z" start="2026-10-18T07:32:13.400Z" stale="2026-10-18T07:32:43.400Z" opex="s-mirrorworld">
  <point lat="49.3765000" lon="31.1870000" hae="250.0" ce="150.0" le="50.0"/>
  <detail><contact callsign="Unknown drone, 2.4 GHz"/><remarks>Heard by sensor-RF1 and sensor-RF2, position from crossed bearings</remarks>
    <link uid="sensor-RF1" type="a-f-G-E-S" relation="p-p"/><link uid="lob-RF1-0001" type="u-rb-a" relation="c-f"/>
    <__signal sensor="sensor-RF1" freq_mhz="2444.5" power_dbm="-80.6" bearing_deg="16.3"/>
    <__signal sensor="sensor-RF2" freq_mhz="2444.5" power_dbm="-84.2" bearing_deg="290.8"/></detail>
</event>

<!-- Ground truth (simulated) -->
<event version="2.0" uid="truth-uav-0007" type="a-h-A-M-H-Q" how="m-s" time="2026-10-18T07:32:13.100Z" start="2026-10-18T07:32:13.100Z" stale="2026-10-18T07:32:23.100Z" opex="s-mirrorworld">
  <point lat="49.3765000" lon="31.1870000" hae="250.0" ce="0.0" le="0.0"/>
  <detail><contact callsign="TRUTH uav-0007"/><track course="275.0" speed="12.0"/></detail>
</event>
```

Not generated by the script, but schema-checked against the ATAK importers:

```xml
<!-- Pilot / GCS fix from UL bursts -->
<event version="2.0" uid="sig-0008-gcs" type="a-u-G-U-C-V-U" how="m-r" time="…" start="…" stale="…"><point lat="49.3655" lon="31.1702" hae="120" ce="300" le="9999999"/><detail><contact callsign="Probable pilot (OcuSync UL 2452 MHz)"/></detail></event>
<!-- 2-sigma error ellipse (major/minor = full axes, m) -->
<event version="2.0" uid="sig-0007-ell" type="u-d-c-e" how="m-f" time="…" start="…" stale="…"><point lat="49.3765" lon="31.1870" hae="250" ce="9999999" le="9999999"/><detail><shape><ellipse major="600" minor="250" angle="35"/></shape><strokeColor value="-256"/><strokeWeight value="2"/><contact callsign="sig-0007 2σ"/></detail></event>
<!-- LOB as plain polyline (fallback) -->
<event version="2.0" uid="lob-RF1-0001-line" type="u-d-f" how="m-r" time="…" start="…" stale="…"><point lat="49.3600" lon="31.1800" hae="180" ce="9999999" le="9999999"/><detail><link point="49.3600,31.1800"/><link point="49.4290,31.2050"/><strokeColor value="-256"/><strokeWeight value="2"/><contact callsign="LOB RF1"/></detail></event>
```

The bearings are consistent with the geometry. The true bearing from RF1 to the drone is 15.44° at 1.90 km, and from RF2 it is 292.35° at 3.37 km. The measured values are truth plus N(0, 3°).

### 3.4 Replay [V]

**pytak** 7.6.1 (released 2026-08-23, Python ≥3.6). Defaults from `pytak.constants`:
- `DEFAULT_COT_URL = udp+wo://239.2.3.1:6969`: SA multicast, read by ATAK on the same LAN with no server.
- ATAK unicast UDP input: port **4242**.
- TAK Server: plain TCP **8087**, TLS **8089**.
- `DEFAULT_COT_STALE = 120` s.

`COT_URL` schemes: `udp://`, `udp+wo://` (write-only; plain `udp://` also binds a reader on that port), `tcp://`, `tls://`, `log://stdout`, `file://`, `tak://` (enrollment).

Minimal replayer (verified via loopback, 7 of 7 events received):

```python
import asyncio, configparser, pytak
class Replayer(pytak.QueueWorker):
    async def handle_data(self, data): await self.put_queue(data)
    async def run(self, _=-1):                     # Worker.run(self, _=-1) in 7.6.1
        last = events[0][0]
        for t, ev in events:                       # time-ordered (t_rel_s, ElementTree event)
            await asyncio.sleep((t - last) / SPEED); last = t
            retime(ev, utcnow())                   # time=start=now, stale=now+(stale-start)
            await self.handle_data(ET.tostring(ev))
async def main():
    cfg = configparser.ConfigParser(); cfg["mw"] = {"COT_URL": "tcp://takserver:8087", "PYTAK_NO_HELLO": "1"}
    tool = pytak.CLITool(cfg["mw"]); await tool.setup()
    tool.add_tasks({Replayer(tool.tx_queue, cfg["mw"])}); await tool.run()
asyncio.run(main())
```

**Gotcha: re-stamp on replay.** Historical events whose `stale` is already in the past are shown as stale or dropped. `cot_demo.retime()` shifts time, start and stale to wall-clock time while keeping the validity window.

**Data packages** (`pytak.TAKDataPackage`):
- A zip of `.cot` files plus `MANIFEST/manifest.xml`.
- Format: `<MissionPackageManifest version="2"><Configuration><Parameter name="uid|name|onReceiveDelete"…/></Configuration><Contents><Content ignore="false" zipEntry="x.cot"/></Contents>`.
- A data package is a **static snapshot**: the same uid overwrites, so it is not time-animated. Use it for sensor layouts and an end-state picture. Use streaming for playback.

**Servers**:
- FreeTAKServer advertises "CoT recording in a database".
- OpenTAKServer advertises TCP/SSL CoT streaming, data packages and the Mission API.
- Neither documents a replay feature. Port numbers for these two were not verified [U]; TAK Server's 8087/8089 are the de facto defaults.

---

## 4. Ukrainian RF drone-detection practice

### 4.1 Fielded or announced devices

| Device (maker) | Side | Bands / method | Output to operator | Source |
|---|---|---|---|---|
| **Chuyka 2.0 / 3.0 / 4.0** (BlueBird Tech, Odesa) | UA | Passive analog-video scanner. 3.0: 900-1800, 2870-4080, 4860-6060 MHz, ≤10 MHz steps, 4-8 s full cycle, up to 4 km. 4.0 adds 6040-8800 MHz (3-3.5 km) | Audio and visual alarm; small screen with **signal level and number of emissions**; optional large screen showing the **intercepted FPV video**. 6 h battery, 650 g. No DF, no data export | [S] blue-bird.tech; [S] flasharmy.com.ua |
| **ZORKO** (Stinex, Dec 2025) | UA | 1.2 / 3.3 / 5.8 GHz video scanning | Adjustable audio alarm; 2 screens; real-time video interception; 6-8 h; IP54 | [S] Militarnyi |
| **Obriy 1.3** (Kara Dag) | UA | Wearable; scans 1.2 / 2.4 / 5.8 GHz (Janes says 4.8); DJI and FPV; 2.5-4 km | Vibrating alert, **direction of approach**, AI classification. Obriy 2.0 (networked, sharing data in real time) in development | [S] Janes / defence-blog via search |
| **Eter** (Falcons) | UA | Multi-antenna DF workstation | **Direction and movement of multiple drones; possible point of origin of operators** | [S] Defense One 2023 |
| Drone Spices "Candy" / "Salt" / "Cinnamon" | UA | Detect Orlan / Russian cell signals / DJI (<$100 each) | Alert | [S] Defense One |
| Infozahyst **Plastun-RP3000**, Khortytsia-M, **Pluton** | UA | Man-portable DF 25 MHz-3 GHz, about 15 km (Khortytsia-M about 45 km); Pluton is a UAV detection and warning system | Bearings / SIGINT; UAV warning | [S] defence-ua, defence-blog |
| **SeekLevel** (DETECT GROUP, 2025-26) | UA | UAV-mounted DF, 1.5-6 GHz, 2 antennas, −94 dBm | Azimuth and signal strength overlaid on the FPV video OSD; ArduPilot / Betaflight | [S] LB.ua 2026 |
| DJI AeroScope / DIY DroneID receivers | both | DroneID decode (2× HackRF prototype at 1.2 km; AeroScope claimed up to 30 mi) | Drone and **pilot** GPS, serial | [V] Bender; [V] NDSS |
| Acoustic network (Sky Fortress / Zvook-type) | UA | About 9,500-10,000 pole-mounted phone-plus-microphone sensors at $400-500 each; central fusion | **Route of flight** sent to mobile fire teams on iPads | [S] TWZ 2024 |
| *Bulat* (3MX) | **RU** | v4: 300-6200 MHz, 1.5-3 km; firmware extended to 7.2 GHz (2025); v6 adds FPV video display (production Q1 2027) | Alarm / identification of DJI, Autel, Walksnail, FPV | [S] www1.ru; [S] militaeraktuell |

Correction to the brief: **Chuyka is Ukrainian, Bulat is Russian.** Both are passive band scanners. Neither is a DF network.

### 4.2 What operators care about (use these as output fields)
- **Early warning time.** "If an Orlan spots you, you have three minutes."
- **Direction or approach vector.**
- **Band and type**: FPV vs Mavic vs Orlan vs Lancet. Intercepted video reveals the target.
- **Count**: swarms.
- **Friend vs foe.** Detectors keep a memory of friendly emitters to cut fratricide.
- **Operator location.**
- **Staying passive**: no emissions.
- **Coverage above 6 GHz** (2026).
- **Scan cycle** (4-8 s) and **battery life** (6-8 h).

**Suggested record schemas** [A]:
- Handheld scanner alert (Chuyka-like):
  `{t, device_id, band, freq_mhz_est (10 MHz quantised), level_bars|rssi_dbm, n_emissions, video_ref, alarm}`
- DF network report:
  `{t, sensor_id, f_c, bw, burst_dur, n_bursts, rssi_dbm, snr_db, bearing_deg_true, bearing_sigma_deg, class_guess, confidence, record_uid}`

  Keep `object_uid` and `link` in a separate truth table, or in `__truth`.

### 4.3 Public data formats
- No public standard output format was found for Ukrainian detectors. They are UI-centric and proprietary.
- **Delta** (the Ukrainian battle-management system) ingests drones and sensor networks, but its integration interfaces are undisclosed.
- For interoperability, use:
  - CoT, including TAK's `__lob` / `__signalInfo` schema, for the map;
  - SigMF for IQ;
  - JSONL for alerts;
  - optionally **SAPIENT** (BSI Flex 335), the UK/NATO counter-UAS sensor ICD. A teammate is researching it [U].

---

## 5. Unverified or conflicting items

1. **OcuSync video numerology and duty cycle.** We assume it is LTE-like, by analogy with DroneID (NDSS says the protocols "use similar modulation techniques and parameters as LTE"). DJI does not publish it.
2. **OcuSync uplink waveform.** Hop bandwidth and burst timing are RFUAV measurements, and the meaning of their "FHSDC" column is unclear.
3. **DroneID rate.** NDSS measured 640 ms. RTU 2025 says "10 per second". Whether O3/O4 still broadcast DroneID unencrypted was not verified.
4. **Analog FM deviation** is our assumption, tuned to occupied bandwidth.
5. **Military UAS frequencies** are OSINT and conflict with each other (Orlan 850-930 vs 902-928 vs Armada's list). Lancet's video band is unknown. Armada's GNSS bands are receive-only, not emissions.
6. **XK-F358.** The datasheet ranges are marketing; the band actually used on Gerans is unknown. The Starlink Ku uplink band comes from general knowledge.
7. **Interceptor radio links** are not public. Our model is an assumption.
8. **Fibre-optic residual emissions** are undocumented.
9. **ELRS receiver telemetry power** of ≤100 mW is unverified.
10. **ATAK details.** `__lob` rendering, the `u-d-c-e` angle convention, and the FreeTAKServer / OpenTAKServer ports were not tested on a device or server.
11. **Dataset details.** The DroneRFa file format and the CardRF oscilloscope model are unverified.
12. **Leer-3 GSM spoofing.** It is widely reported, but the Wikipedia page fetched here does not state it.

---

## 6. Sources

**DJI**
- NDSS'23 DroneID paper: https://www.ndss-symposium.org/wp-content/uploads/2023-217-paper.pdf
- RUB DroneSecurity receiver: https://github.com/RUB-SysSec/DroneSecurity
- Bender 2022, "DJI drone IDs are not encrypted": https://arxiv.org/pdf/2207.10795
- DJI MSDK OcuSyncLink: https://developer.dji.com/api-reference/android-api/Components/OcuSyncLink/DJIOcuSyncLink.html
- DJI Mini 2 manual: https://dl.djicdn.com/downloads/DJI_Mini_2/DJI_Mini_2_User_Manual-EN.pdf
- Phantom 4 Pro manual: https://dl.djicdn.com/downloads/phantom_4_pro/20170719/Phantom_4_Pro_Pro_Plus_User_Manual_EN.pdf
- Mavic 3 downloads: https://www.dji.com/au/mavic-3/downloads
- O3 Air Unit: https://www.dji.com/ae/support/product/o3-air-unit
- O4 Air Unit specs: https://dji.com/o4-air-unit/specs
- O4 Air Unit Pro (GetFPV): https://www.getfpv.com/distribution/dji/dji-o4-air-unit-pro.html
- Mini 4 Pro spec copy: https://www.cliftoncameras.co.uk/uploads/specifications/DJI%20Mini%204%20Pro.pdf
- RTU 2025 DJI signal analysis: https://archive-journals.rtu.lv/etr/article/download/5282/5222

**FPV and control links**
- RFUAV: https://arxiv.org/html/2503.09033v1
- Oscar Liang channel chart: https://oscarliang.com/fpv-channels/
- Lumenier VTX spec: https://www.getfpv.com/lumenier-tx5g2r-mini-200mw-5-8ghz-fpv-transmitter-with-raceband.html
- TBS Crossfire manual: https://www.team-blacksheep.com/media/files/tbs-crossfire-manual.pdf
- g3gg0 Crossfire analysis: https://www.g3gg0.de/wordpress/fpv/fpv-analysis-of-tbs-crossfire/
- ExpressLRS `common.cpp`: https://github.com/ExpressLRS/ExpressLRS/blob/master/src/src/common.cpp
- ExpressLRS `FHSS.cpp`: https://github.com/ExpressLRS/ExpressLRS/blob/master/src/lib/FHSS/FHSS.cpp
- ExpressLRS `common.h`: https://github.com/ExpressLRS/ExpressLRS/blob/master/src/include/common.h
- ExpressLRS `POWERMGNT.h`: https://github.com/ExpressLRS/ExpressLRS/blob/master/src/lib/POWERMGNT/POWERMGNT.h
- HDZero narrow mode: https://intofpv.com/t-hdzero-freestyle-v2-vtx?page=2

**Ukraine context and military UAS**
- Chuyka 3.0: https://www.blue-bird.tech/en/products/chuyka-3-0/
- Chuyka 4.0: https://flasharmy.com.ua/en/prystrii-radioelektronnoi-rozvidky-chuika-40
- Boomerang FPV frequency shift: https://militarnyi.com/en/news/russian-boomerang-fpv-drones-shifted-to-frequencies-unavailable-to-most-detectors/
- ZORKO: https://militarnyi.com/en/news/ukraine-introduces-zorko-detector-that-allows-fpv-drone-video-interception/
- Euromaidan 2025 (EW and fibre): https://euromaidanpress.com/2025/06/26/ukraine-jamming-fails-fiber-drones-russia/
- Armada 2024, Russian UAV frequencies: https://www.armadainternational.com/2024/12/russian-uav-operating-frequencies-electronic-warfare/
- Orlan-10: https://en.wikipedia.org/wiki/STC_Orlan-10
- Lancet (Militarnyi): https://militarnyi.com/en/articles/zala-lancet-engagement-and-countereffort/
- Ampheo RF chips blog: https://www.ampheo.com/blog/what-rf-chips-and-antennas-have-been-used-in-drones-in-the-russia-ukraine-war
- Shahed 136: https://en.wikipedia.org/wiki/HESA_Shahed_136
- Shahed cellular modem (TWZ): https://www.twz.com/shahed-136-with-cellular-modem-found-in-ukraine-what-it-means
- XK-F358 on Russian drones: https://euromaidanpress.com/2026/08/11/russias-jam-resistant-drones-run-on-a-chinese-modem-no-one-has-sanctioned/
- XK-F358 datasheet: https://xingkaitech.com/cofdm-wireless-transmission/mimo-mesh-xk-f358/
- Kometa (GUR): https://war-sanctions.gur.gov.ua/en/components/3821
- Gerbera: https://en.wikipedia.org/wiki/Gerbera_(drone)
- Sting: https://en.wikipedia.org/wiki/Sting_(drone)
- Starshield speed cap: https://dronexl.co/2026/10/16/starshield-cap-ukraine-interceptor-drones-white-house/
- Fibre-optic drones: https://en.wikipedia.org/wiki/Fiber_optic_drone

**Formats**
- SigMF spec: https://sigmf.org/
- SigMF `signal` extension: https://github.com/sigmf/SigMF/blob/main/extensions/signal.sigmf-ext.md
- SigMF `spatial` extension: https://github.com/sigmf/SigMF/blob/main/extensions/spatial.sigmf-ext.md
- SigMF on PyPI: https://pypi.org/project/SigMF/
- pytak on PyPI: https://pypi.org/project/pytak/
- pytak repo: https://github.com/snstac/pytak
- CoTtypes.xml (MITRE): https://github.com/dB-SPL/cot-types/blob/main/CoTtypes.xml
- TAK CoT schemas: https://github.com/TAK-Product-Center/atak-civ/tree/main/takcot
- ATAK importers (`RangeAndBearingImporter`, `SensorDetailHandler`, `DrawingShapeImporter`, `DrawingEllipseImporter`, `DrawingCircleImporter`): https://github.com/TAK-Product-Center/atak-civ/tree/main/atak/ATAK/app/src/main/java/com/atakmap/android

**Datasets**
- DroneRF: https://pmc.ncbi.nlm.nih.gov/articles/PMC6727013/
- DroneDetect: https://ieee-dataport.org/open-access/dronedetect-dataset-radio-frequency-dataset-unmanned-aerial-system-uas-signals-machine
- CardRF: https://ieee-dataport.org/documents/cardinal-rf-cardrf-outdoor-uavuas-rf-signals-bluetooth-and-wifi-signals-dataset
- DroneRFa (described in): https://arxiv.org/html/2508.12689
- DRFF-R2: https://arxiv.org/html/2603.00106v1

**Detection practice**
- Defense One 2023: https://www.defenseone.com/threats/2023/12/ukraines-soldiers-use-cheap-tech-hide-russias-deadly-drones/392957/
- SeekLevel (LB.ua): https://en.lb.ua/news/2026/08/25/40456_ukraine_develops_direction.html
- Acoustic network (TWZ): https://www.twz.com/air/ukraines-acoustic-drone-detection-network-eyed-by-u-s-as-low-cost-air-defense-option
- Bulat v6: https://www1.ru/en/news/2026/06/06/detektor-bulat-naucilsia-pokazyvat-video-s-obnaruzennyx-vrazeskix-fpv-dronov.html
- Delta: https://en.wikipedia.org/wiki/Delta_(situational_awareness_system)
