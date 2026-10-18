# Mirror World: real-world geo context spike (Korsun-Shevchenkivskyi / Ros valley)

Spike run 2026-10-18 from this Mac with no credentials. The aim was to show that every piece of real-world context the scenario generator needs can be fetched with Python 3 + numpy (+ rasterio, pystac-client, skyfield, requests), and to measure each source's timing, data size, gotchas and licence.

* Spike root: `scratch/geo-spike`
* Scripts: `scratch/geo-spike/scripts/` (full versions). The minimal versions quoted below come from `snippets.py`, which was run end to end.
* Outputs: `scratch/geo-spike/data/` (52 MB, of which 17 MB is the JPL ephemeris)

Reproduce:

```bash
cd scratch/geo-spike
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python numpy rasterio pystac-client skyfield requests pillow matplotlib pyproj
.venv/bin/python -I scripts/snippets.py            # ~45 s; every network call is bounded by a timeout
.venv/bin/python -I scripts/dem.py [lat lon half_km tag]   && .venv/bin/python -I scripts/worldcover.py [...] \
  && .venv/bin/python -I scripts/terrain_los.py [tag]      && .venv/bin/python -I scripts/canopy_tracks.py [tag]
.venv/bin/python -I scripts/s2.py; .venv/bin/python -I scripts/sats.py 2026-11-03 3; .venv/bin/python -I scripts/weather.py; .venv/bin/python -I scripts/osm.py
```

Versions: Python 3.12.7, numpy 2.5.4, rasterio 1.5.2 (GDAL 3.12.2), pystac-client 0.9.0, skyfield 1.55, requests 2.34.2, pyproj 3.8.0.

---

## 0. Status table

| # | Source | Works? | Wall time | Bytes on the wire | Licence |
|---|---|---|---|---|---|
| 1 | Copernicus GLO-30 DSM COG (AWS, public HTTPS) | yes | open 0.3 s + window 0.5 s (4-tile mosaic 1.8 s) | 2.7 MB for 12x12 km (2 GETs) | Copernicus WorldDEM-30 licence (free, attribution) |
| 2 | ESA WorldCover 2021 v200 COG (AWS) | yes | 0.3-0.5 s | 0.29 MB | CC BY 4.0 |
| 3 | Sentinel-2 L2A via Earth Search STAC v1 | yes | search 0.3-0.5 s; TCI window 1.7-4.4 s; 4 bands 7.3 s | ~7 MB per TCI window; 46 MB for the whole run | Copernicus Sentinel data (free, attribution) |
| 3b | S2 MSI inter-band time offsets | researched | - | - | ESA table (via CNES/ISPRS 2022, CC BY 4.0 paper) |
| 4 | skyfield + CelesTrak GP (TLE) + JPL DE421 | yes | TLE 0.7-0.9 s each; DE421 3.5 s once; passes 0.2 s | 170 B per TLE; DE421 16.8 MB | CelesTrak: free, strict usage rules; DE421 public |
| 5 | Open-Meteo (ERA5 archive, historical-forecast, ensemble, seasonal, climate) | yes, with gaps | 0.1-0.5 s per call | 2-45 KB | CC BY 4.0, **non-commercial free tier** |
| 6 | OSM Overpass + Nominatim | yes, but Overpass flaky | Overpass 35-52 s (queueing + 1 retry); Nominatim 0.2 s per call | 0.9 MB JSON (1,453 elements) | ODbL 1.0 |
| 7 | Alternative strong-relief sites | done | 0.5-1.8 s per DEM | 3-5 MB | as #1/#2 |

Things that **failed or were partial**. None of them blocks the plan.
* Overpass main instance (`overpass-api.de`, `z.`) returned **502 "at capacity"**. `overpass.kumi.systems` and `overpass.private.coffee` returned **Apache 500**. `lz4.overpass-api.de`, and later the main instance, answered after about 30-35 s of queueing.
* Open-Meteo **forecast API does not cover 2026-11-03 yet** (HTTP 400; its 16-day horizon ends 2026-11-02 today). The **ECMWF ensemble returns HTTP 200 with every value null**, which is a silent-failure trap. The GFS ensemble (35 d), seasonal (daily) and CMIP6 climate (daily) APIs do cover the date.
* Open-Meteo ERA5 archive has **no visibility and no pressure-level winds** (all null). The historical-forecast API provides both.
* **No Sentinel-2 pass covers the point on 2026-11-03 itself.** S2C covers it on 11-02 and S2A on 11-04.
* OpenAerialMap: **0 images** in the 12 km box, both in the legacy API and the new HOT STAC. The same is true of Maxar and Vantor open data, so the brief's 30 cm aerial can't be reproduced for this spot from open catalogues.
* `download.geofabrik.de` (offline OSM extract) timed out twice (20 s, 30 s), so it is untested.
* `sentinel.esa.int` didn't resolve through the fetch tool. The ESA band-timing table was taken from two peer-reviewed reproductions (section 3b).

---

## Key findings that affect the design

1. **Where the brief's point is.** 49.3754 N, 31.1882 E reverse-geocodes to *Steblivska selyshchna hromada, Zvenyhorodka Raion, Cherkasy Oblast*. It is **6.8 km SW of Korsun-Shevchenkivskyi** (town centre 49.4180 N, 31.2557 E, population 18,266). It sits on a dissected plateau between the Sokovytsia stream valley (W) and the Zubra/Pohan valley (E), about 4 km S of the **Ros river**, which crosses the north of the box W to E at about 99 m. Korsun is on the Ros in the NE corner of the box. This matches the brief's "farmland and a river valley in central Ukraine": 49% cropland, 38% forest.
2. **Terrain occlusion here is real but only at low altitude.** I modelled two receivers on open high ground 6.5 km apart with 10 m masts. Share of the 12 km box hidden from both: **47% at 10 m AGL, 20% at 30 m, 2% at 60 m, 0% at 120 m.** Share seen by exactly one receiver: 35%, 37%, 22%, 0%. On random straight 4 km tracks, an occlusion of at least 1 km from one receiver, while the other still sees the drone, happens on **11% of tracks at 30 m AGL and 7% at 60 m AGL**. At 10 m/s that is about 100 s, roughly the brief's "two minutes". The brief's ridge scenario is achievable here, but the generator should **search for the geometry** (choose track and receivers) rather than sample at random. For stronger relief, **Kaniv hills (49.72 N, 31.50 E), about 40 km NE in the same oblast**, give 55% hidden-from-both at 30 m AGL and still 26% at 60 m (section 7).
3. **GLO-30 is a DSM** (confirmed in the official README and licence). Canopy is embedded, but partially and inconsistently. All 8 highest points in the box are forest. Plateau forest edges show 10-15 m steps, but a statistical estimate at flat forest edges gives a median of only 2.9 m. X-band radar only partly penetrates canopy, the DEM is smoothed to 30 m, and the TanDEM-X radar data (roughly 2010-2015, going by the licence's copyright years; exact window not re-verified) predate the 2021 land cover. Recommendation: model forest explicitly (WorldCover tree mask plus an assumed canopy height) and don't trust DSM "peaks" as hills.
4. **Satellite timing.** Sentinel-2, WorldView-3 and Pléiades Neo all pass this point at **about 08:45-09:25 UTC** (mid-morning local), and Sentinel-2 always at **about 09:06 UTC**. SkySat-C1 passes around 05:30-06:00 UTC with the sun only 6-9° up. On 2026-11-03, sunset is **14:30:35 UTC** and civil dusk ends **15:04:14 UTC**, so a dusk scenario's "satellite pass that day" is a morning pass about 5.5 h earlier, unless SAR or other platforms are added.
5. **November optical imagery is usually cloudy.** Across 18 S2 acquisition dates in Oct-Nov 2025, only 2 were under 50% cloud. Cloud should be a realism knob for the satellite sensor.
6. **Moving aircraft smear across S2 bands** because each band sees a ground point at a different time: B02 at t=0, B08 at +0.264 s, B03 at +0.527 s, B04 at +1.005 s. The order reverses on alternate detectors. Elevated objects add an along-track parallax of about 8.5-9.5 m per km of height for B02 to B04. Formula and examples are in section 3b.
7. **Weather.** ERA5 via Open-Meteo gives real hourly analogue weather for any past date in 0.1 s, but **the free tier is non-commercial only**. Confirm that a company-run defence hackathon qualifies, or budget for the paid API.
8. **OSM gives real sensor sites.** The 58 m comms mast at Stebliv (49.3926 N, 31.1109 E, ground about 180 m) sees **84% of the box at 30 m AGL** in our LOS model. The public Overpass service is overloaded and now explicitly asks automated users to run their own instance, so **fetch once per region at build time and cache**.

---

## 1. Copernicus DEM GLO-30 (AWS open data)

**URL verified** (HTTP 200, 43,027,743 B, Last-Modified 2022-05-09). The regional endpoint `copernicus-dem-30m.s3.eu-central-1.amazonaws.com` also works.
`https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N49_00_E031_00_DEM/Copernicus_DSM_COG_10_N49_00_E031_00_DEM.tif`

```python
import math, rasterio
from rasterio.windows import from_bounds
ENV = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
           GDAL_HTTP_TIMEOUT="30", GDAL_HTTP_CONNECTTIMEOUT="10", GDAL_HTTP_MAX_RETRY="3",
           GDAL_HTTP_RETRY_DELAY="1", GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES", VSI_CACHE="TRUE")

def bbox(lat, lon, half_km=6.0):
    dlat, dlon = half_km / 111.32, half_km / (111.32 * math.cos(math.radians(lat)))
    return lon - dlon, lat - dlat, lon + dlon, lat + dlat          # W, S, E, N

def glo30(lat, lon, half_km=6.0):                                   # N/E hemisphere, single tile
    t = f"Copernicus_DSM_COG_10_N{int(lat):02d}_00_E{int(lon):03d}_00_DEM"
    with rasterio.Env(**ENV), rasterio.open(f"/vsicurl/https://copernicus-dem-30m.s3.amazonaws.com/{t}/{t}.tif") as ds:
        win = from_bounds(*bbox(lat, lon, half_km), ds.transform).round_offsets().round_lengths()
        return ds.read(1, window=win), ds.window_transform(win)      # float32 m (EGM2008), no nodata
```

The full version is `scripts/dem.py`. It adds a multi-tile mosaic via `rasterio.merge`, stats, peak and valley finding, a GeoTIFF and a hillshade PNG. `scripts/terrain_los.py` and `scripts/canopy_tracks.py` handle viewsheds, canopy and track occlusion.

**File facts.** float32, 3600x3600 px, EPSG:4326, 1"x1" (0.000278 deg), DEFLATE with predictor 3, 1024x1024 internal tiles, overviews 2/4/8, `AREA_OR_POINT=Point`, `nodata=None`. Tile bounds are 30.99986-31.99986 E and 49.00014-50.00014 N; the half-pixel shift is because pixels are point-registered. Window around the brief point: **388x596 px, 20.1 m (E-W) x 30.7 m (N-S) per pixel.**

**Timing and size.** Open 0.30 s, window read 0.53 s. On the wire: 1 HEAD + 2 GETs, **2.69 MB**, measured with `CPL_VSIL_SHOW_NETWORK_STATS=YES`, which is a cheap way to observe bytes per read. The saved window GeoTIFF is 0.78 MB. A cross-tile window at 49.97 N (4 tiles) mosaics in 1.8 s.

**Elevation stats (12x12 km, DSM):**

| min | p1 | p5 | p25 | median | mean | p75 | p95 | p99 | max | std |
|---|---|---|---|---|---|---|---|---|---|---|
| 56.3* | 99.5 | 105.8 | 130.9 | 153.3 | 152.2 | 171.9 | 196.4 | 211.5 | 232.2** | 27.4 m |

\* 56.3 m at 49.4183 N, 31.2197 E is the **"Syvach" granite quarry pit** (OSM `landuse=quarry`, `name=Сивач`, `resource=stone`, 49.4188 N, 31.2195 E). It is about 43 m below the river.
\** The maximum is forest canopy (see below).

Slope: mean 4.9°, p95 14.0°, max 42.4°. Local relief (max minus min within 1 km blocks): median 52 m, p90 70 m, max 101 m. DSM at the truth point is 128.6 m; the point is on a ravine (balka) slope, and the surface is 156.7 m about 50 m to the north.

**River valley (Ros, W to E across the north):** the lowest pixel per ~1 km column is the water surface, flattened in the edited DEM.
(49.4086, 31.1056) 103 m, (49.4258, 31.1333) 99.5, (49.4239, 31.1611) 99.5, (49.4131, 31.1889) 99.0, (49.4008, 31.2306) 99.0, (49.4131, 31.2583) 98.5. Below the Korsun HPP dam (49.4121, 31.2634) it drops to **88 m** at (49.4147, 31.2683). The Stebliv HPP dam is on the west edge (49.4073, 31.1085). Tributaries from OSM, clipped to the box: Sokovytsia runs N-S along lon 31.14-31.18 (49.33 to 49.41, 11.7 km). Zubra/Pohan runs along lon 31.23-31.27 (49.34 to 49.40, 8.8 km). There are 9 pond dams.

**High ground.** The southern plateau, 49.32-49.35 N, is 190-230 m. DSM peaks, which are **all forest** (89-100% tree cover within 100 m):
232.2 m (49.3319, 31.2047), 226.8 (49.3694, 31.2700), 220.1 (49.3258, 31.1064), 219.4 (49.3472, 31.1969), 218.5 (49.3831, 31.2683), 210.3 (49.3689, 31.1200), 207.0 (49.3361, 31.1850), 203.7 (49.3386, 31.1142).
**Open-ground high points** (crop, grass or bare in a full 3x3 neighbourhood; these are receiver candidates):
230.3 m (49.3308, 31.1975, next to forest, so suspect canopy), 215.1 (49.3442, 31.2047), 202.1 (49.3319, 31.1083), 202.1 (49.3711, 31.2058), 200.9 (49.3306, 31.2156), 199.2 (49.3606, 31.1986), 199.1 (49.3711, 31.1081), 198.7 (49.3614, 31.1147).

**Viewshed and occlusion test.** Geometric LOS on the DSM, 4/3-Earth curvature, 10 m masts, no diffraction. Receivers: A at 49.3308, 31.1975 (230 m) and B at 49.3319, 31.1083 (202 m), 6.46 km apart.

| target AGL | hidden from A | hidden from B | hidden from both | seen by exactly one |
|---|---|---|---|---|
| 10 m | 50.6% | 78.6% | 47.0% | 35.2% |
| 30 m | 21.7% | 55.6% | 20.3% | 36.8% |
| 60 m | 3.5% | 22.7% | 2.2% | 21.8% |
| 120 m | 0% | 0% | 0% | 0% |

The longest single-receiver occlusion on 388 random 4 km straight tracks: at 30 m AGL, at least 1 km on 11%, at least 2.4 km on 2%, p90 1,036 m. At 60 m AGL: 7%, 1%, p90 786 m. Real OSM masts as sites (heights assumed where OSM has none):

| site | share of box seen at 30 m AGL | at 60 m AGL |
|---|---|---|
| 58 m Stebliv mast (ground 180 m) | **84%** | 97% |
| 52 m Selyshche mast (ground 153 m) | 57% | 76% |
| Korsun water tower (+25 m) | 53% | 77% |

**Is it a DSM?** Yes. The AWS README says: "*The Copernicus DEM is a Digital Surface Model (DSM) which represents the surface of the Earth including buildings, infrastructure and vegetation.*" The licence defines WorldDEM-30 as "*a Digital Surface Model ... derived from the TanDEM-X Mission data*". Google Earth Engine's catalogue adds: "*derived from an edited DSM, i.e. flattening of water bodies and consistent flow of rivers*". Empirical check in this box:
* All 8 DSM peaks are in WorldCover tree cover.
* Plateau forest edges show steps: 219 to 208 m at 49.345 N, 31.206 E; 209 to 194 m over about 80 m at 49.335 N, 31.217-31.218 E.
* A flat-edge statistic (3,861 pairs) gives a median step of only **2.9 m** (IQR -1.2 to 7.3).

So the canopy is in the DSM, but under-represented and inconsistent. Causes: X-band only partly penetrates canopy, which underestimates height; the 30 m smoothing; and the roughly 2010-2015 TanDEM-X epoch against 2021 land cover (clear-cuts, regrowth). **Gotcha:** "receiver on the highest point" picks a treetop. Choose open ground (WorldCover 30/40/60) and treat forest as an explicit obstacle or attenuation volume.

**Other gotchas**
* **Vertical datum is EGM2008.** Geoid undulation here is **N = +25.2 m**, fetched credential-free from the PROJ CDN with `pyproj`, `PROJ_NETWORK=ON`, `EPSG:4326+3855 -> EPSG:4979`. Add it to get WGS84 ellipsoidal heights for satellite and GNSS geometry.
* **North of 50 N, tiles have 1.5" longitude spacing** (2400 px wide); this affects Kyiv, Chernihiv, Sumy and Kharkiv. Mosaicking across that line needs resampling.
* `rasterio.merge.merge(bounds=...)` **left the last output row empty**. Fixed by padding 3 px and cropping; the script raises on any remaining hole rather than writing zeros.
* All of Ukraine is in GLO-30 Public. In `tileList.txt`, the only gaps in the 44-52 N, 22-40 E box are Black Sea tiles.
* Set `GDAL_DISABLE_READDIR_ON_OPEN=EMPTY_DIR`. Otherwise GDAL LISTs the S3 prefix on every open.

**Licence (verbatim, Copernicus WorldDEM-30 licence, Art. 6).** Free, worldwide, perpetual rights to reproduce, distribute, communicate and adapt.
* Unmodified: "© DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved."
* Modified (our case): "produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved"
* Must be added to any redistribution: "The organisations in charge of the Copernicus programme by law or by delegation do not incur any liability for any use of the Copernicus WorldDEM-30".
* Do not imply endorsement by Airbus, the EU or ESA.

Bare-earth alternatives, not tested: FABDEM (Copernicus with forests and buildings removed; licence CC BY-NC-SA 4.0 from memory, so non-commercial, verify) and Meta/WRI 1 m global canopy height on AWS (from memory, verify).

Outputs:
* `scratch/geo-spike/data/hillshade_korsun.png`
* `scratch/geo-spike/data/dem_korsun.tif`
* `scratch/geo-spike/data/viewshed30_korsun.png`
* `scratch/geo-spike/data/terrain_los_korsun.json`

---

## 2. ESA WorldCover 10 m 2021 (v200)

URL pattern: tiles are 3x3 degrees, named by their SW corner in multiples of 3. Verified 200, 72,139,802 B.
`https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_N48E030_Map.tif`

```python
def worldcover(lat, lon, half_km=6.0):
    la, lo = 3 * (int(lat) // 3), 3 * (int(lon) // 3)
    url = ("/vsicurl/https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/"
           f"ESA_WorldCover_10m_2021_v200_N{la:02d}E{lo:03d}_Map.tif")
    with rasterio.Env(**ENV), rasterio.open(url) as ds:
        win = from_bounds(*bbox(lat, lon, half_km), ds.transform).round_offsets().round_lengths()
        return ds.read(1, window=win), ds.window_transform(win)      # uint8 class codes 10..100
```

**File facts.** uint8, 36000x36000 px, EPSG:4326, pixel 0.0000833 deg (6.0 m E-W x 9.3 m N-S at this latitude), 1024 tiles, overviews 2-64, nodata 0. The legend, licence and copyright are embedded in the GeoTIFF tags. Window: 1294x1987 px. Read time 0.47 s; **294 KB** on the wire.

**Class histogram (12x12 km):**

| class | share |
|---|---|
| Cropland | 49.45% |
| Tree cover | 37.70% |
| Grassland | 8.03% |
| Built-up | 2.13% |
| Permanent water | 1.86% |
| Herbaceous wetland | 0.81% |
| Bare/sparse | 0.04% |

Forest sits mostly in ravines and on the southern plateau. The Ros floodplain is grassland and wetland.

**Gotchas**
* The map is from 2021. It won't show later clear-cuts, war damage or new buildings.
* The 2020 v100 product uses a different algorithm; don't mix the two years.
* Classes are per 10 m pixel. Shelterbelts are often "tree", which matters for camera LOS and less for the 30 m DSM.

**Licence: CC BY 4.0.** Required copyright (from the file tag): "**© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium**". Cite Zanaga, D. et al. (2022) *ESA WorldCover 10 m 2021 v200*, doi:10.5281/zenodo.7254221.

Outputs:
* `scratch/geo-spike/data/worldcover_korsun.png`
* `scratch/geo-spike/data/worldcover_korsun.tif`

---

## 3. Sentinel-2 L2A via Element84 Earth Search STAC v1

Collections at `https://earth-search.aws.element84.com/v1`: `sentinel-2-c1-l2a`, `sentinel-2-l2a`, `sentinel-2-pre-c1-l2a`, `sentinel-2-l1c`, `sentinel-1-grd`, `landsat-c2-l2`, `cop-dem-glo-30`, `cop-dem-glo-90`, `naip`. The `query` and `sortby` extensions are supported; no CQL2 `filter` conformance is advertised. No auth is needed. I found no published SLA or rate limit, so be gentle and cache.

```python
from pystac_client import Client
from rasterio.warp import transform_bounds

def s2_true_colour(lat, lon, date_range="2017-01-01/2026-10-17", tile="MGRS-36UUV"):
    cat = Client.open("https://earth-search.aws.element84.com/v1", timeout=(10, 60))
    items = cat.search(collections=["sentinel-2-c1-l2a"], intersects={"type": "Point", "coordinates": [lon, lat]},
                       datetime=date_range, max_items=3,
                       query={"eo:cloud_cover": {"lt": 5}, "grid:code": {"eq": tile}},   # native UTM-zone tile
                       sortby=[{"field": "properties.eo:cloud_cover", "direction": "asc"}]).item_collection()
    it = items[0]
    with rasterio.Env(**ENV), rasterio.open(it.assets["visual"].href) as ds:   # TCI: 3x uint8, 10 m, UTM
        win = from_bounds(*transform_bounds("EPSG:4326", ds.crs, *bbox(lat, lon), densify_pts=21),
                          ds.transform).round_offsets().round_lengths()
        rgb = ds.read(window=win)
        if rgb.shape[1:] != (win.height, win.width):
            raise RuntimeError("window clipped at MGRS tile edge - pick another grid:code")
    return it, rgb
```

The full version is `scripts/s2.py`. It also does the Oct-Nov per-year search, lists all scenes for Oct-Nov 2025, finds the brief's scene, and writes a 4-band B02/B03/B04/B08 GeoTIFF.

**Results**
* **The point lies in the overlap of MGRS 35UQQ and 36UUV**, so each acquisition appears twice. Reading from 35UQQ (UTM 35, about 4 deg outside its zone) **silently clipped about 570 m off the east edge**; rasterio returns a smaller array without raising. Use **36UUV (EPSG:32636)**. The script now checks the shape.
* **Only one relative orbit images this point.** Every acquisition is stamped 09:06:3x-09:06:5x UTC (11:06 EET).
* **Lowest cloud, any season** (eo:cloud_cover in %): S2B 2023-08-15 09:06:47 (0), S2B 2023-09-24 (0), S2B 2025-09-23 (1e-5), S2A 2023-05-02 (2e-5), S2B 2020-08-30 (2e-5).
* **Lowest cloud, Oct-Nov 2017-2025:**

| scene | cloud % | sun elevation | sun azimuth |
|---|---|---|---|
| **S2B 2024-11-07 09:06:35** | 0.0004 | 24.0° | 170.8° |
| S2A 2024-10-23 | 0.0007 | 28.8° | |
| S2A 2020-10-14 | 0.003 | | |
| **S2B 2023-11-03 09:06:42** (same calendar day as the scenario) | 0.011 | 25.4° | |
| S2B 2023-10-14 | 0.04 | | |

* **Oct-Nov 2025 reality:** 18 acquisition dates (S2A, S2B and S2C). Cloud by date on tile 36UUV:

| date (2025) | cloud % |
|---|---|
| Oct 3 | 34 |
| Oct 8 | 100 |
| Oct 10 | 100 |
| Oct 13 | 94 |
| Oct 18 | 96 |
| Oct 20 | 80 |
| Oct 23 | 65 |
| Oct 28 | 69 |
| Oct 30 | 73 |
| Nov 2 | 23 |
| Nov 7, 9, 12, 17 | 100 |
| Nov 19 | 87 |
| Nov 22, 27, 29 | 100 |

Only 2 of the 18 dates were under 50%.
* **The brief's scene is verified:** `S2B_T36UUV_20250903T090123_L2A` (and `..._T35UQQ_...`), 2025-09-03 **09:06:39-41 UTC**, cloud 0.001%, sun elevation 47.0°, processing baseline 05.11.
* **Constellation now:** S2A, S2B and S2C are all acquiring here (Aug-Oct 2026). At query time the newest item was S2A 2026-10-15; the next acquisition (S2B, 2026-10-18) was not listed yet.

**Timing and size.** Searches take 0.26-0.5 s; 9 per-year searches take 2.6 s. A TCI window (1231x1227x3 uint8) takes **1.7-4.4 s and about 7 MB** (assets are in us-west-2). B02, B03, B04 and B08 together (uint16, 4 COGs) take **7.3 s**. The 4-band window GeoTIFF is 9.7 MB. The whole run moved 46 MB.

**Reflectance:** DN x 0.0001 - 0.1. The `raster:bands` scale/offset metadata carries the baseline >= 04.00 BOA offset; don't hard-code it. Prefer `sentinel-2-c1-l2a`, which is uniformly reprocessed to baseline >= 05.

Outputs (all from 36UUV, true colour):
* `scratch/geo-spike/data/s2_best_rgb.png` (2023-08-15)
* `scratch/geo-spike/data/s2_octnov_rgb.png` (2024-11-07, autumn: bare fields, green winter wheat, brown forest)
* `scratch/geo-spike/data/s2_20250903_rgb.png`
* `scratch/geo-spike/data/s2_20250903_B02B03B04B08.tif`

**Licence.** Copernicus Sentinel data are free and open under the EU Legal Notice (Reg. 377/2014, 1159/2013). Attribution: "**Copernicus Sentinel data [year]**", or "**Contains modified Copernicus Sentinel data [year]**" for our renders and synthetic insertions.

### 3b. MSI inter-band acquisition offsets (why moving aircraft show colour fringes)

**Mechanism.** The MSI is a push-broom imager. Each band's detector line sits at a different along-track position in the focal plane, so its line of sight points at a slightly different along-track angle. A ground point is therefore imaged by different bands at different times as the satellite moves.

The swath is covered by **12 staggered detectors**, and "*the spectral filters sort order is inversed between even and odd detectors*". The **sign of the offset flips detector by detector** across the 290 km swath.

The ESA handbook values are means. Real delays vary by **up to ±2%** (altitude, latitude) and **3.2% across-track** (optical distortion). CNES gives a method to compute per-detector delays from L1C metadata to within 1%. Adjacent detectors' blue bands see their narrow overlap strip **2.32 s** apart.

Sources: Binet, Bergsma & Poulain 2022, *Accurate Sentinel-2 inter-band time delays*, ISPRS Annals V-1-2022-57 (Table 2 reproduces the ESA table); Krauß 2021, ISPRS Annals V-1-2021-17 (Table 1).

| band | Δt after B02 (s) | GSD |
|---|---|---|
| B02 blue | 0.000 | 10 m |
| **B08 NIR** | **0.264** | 10 m |
| **B03 green** | **0.527** | 10 m |
| B10 cirrus | 0.851 | 60 m |
| **B04 red** | **1.005** | 10 m |
| B05 | 1.269 | 20 m |
| B11 | 1.468 | 20 m |
| B06 | 1.525 | 20 m |
| B07 | 1.790 | 20 m |
| B8A | 2.055 | 20 m |
| B12 | 2.085 | 20 m |
| B01 | 2.314 | 60 m |
| B09 | 2.586 | 60 m |

So the acquisition order is B02, B08, B03, B10, B04, B05, B11, B06, B07, B8A, B12, B01, B09. B03 to B04 is 0.478 s.

**Model for the simulator.** Measured here: the S2C pass of 2026-11-02 has ground-track heading 195.5° (SSW), ground speed 6.71 km/s and satellite height 797 km. For an object moving at velocity **v** at height *h* above the orthorectification surface, band *i* is displaced relative to B02 by:

    d_i ≈ Δt_i · v  +  Δt_i · k · h · û_track ,   k ≈ 0.0084–0.0095 s⁻¹

The sign of the second term depends on detector parity. Krauß gives 1 px (10 m) of B02 to B04 shift per **1053 m** of height. Pure ground-speed geometry gives about 10 m per 1180 m.

Worked examples for B02 to B04 (1.005 s):

| object | speed | height | motion shift | parallax shift |
|---|---|---|---|---|
| Quadcopter | 15 m/s | 100 m | 15 m (1.5 px) | 0.1 m |
| Shahed-class drone | 50 m/s | low | 50 m (5 px); B02 to B03 is 26 m | small |
| Light aircraft | 60 m/s | 1 km | 60 m | +9.5 m |
| Airliner | 230 m/s | 10 km | 231 m | +95 m (about 33 px total) |

To render: shift each band's sprite by d_i before compositing B04/B03/B02. NIR (B08) falls between B02 and B03, so CIR composites fringe too.

The same effect is used in published work for moving trucks (MDPI *Remote Sensing* 14(7):1595, 2022), aircraft detection and velocity (Heiselberg 2019; Liu et al. 2020, both cited by CNES), cloud heights (Krauß 2021) and wave bathymetry (Bergsma et al.).

---

## 4. Satellite passes (skyfield + CelesTrak GP) and sun geometry

NORAD IDs were verified against CelesTrak names on 2026-10-18; all TLE epochs are 2026-10-18.

| satellite | NORAD ID | COSPAR |
|---|---|---|
| Sentinel-2A | 40697 | 2015-028A |
| Sentinel-2B | 42063 | 2017-013A |
| Sentinel-2C | 60989 | 2024-157A |
| WorldView-3 | 40115 | |
| Pléiades Neo 3 | 48268 | |
| Pléiades Neo 4 | 49070 | |
| SkySat-C1 | 41601 | |

`NAME=SKYSAT` returns 14 SkySats, for example SkySat-A 39418 and SkySat-B 40072.

```python
import requests, time, os, math
from skyfield.api import load, wgs84
def get_cached(url, path, max_age_s=7200, timeout=(10, 60)):
    """CelesTrak: GP updates every 2 h - download once per update; STOP on any non-200 (no retry loop)."""
    if not (os.path.exists(path) and time.time() - os.path.getmtime(path) < max_age_s):
        r = requests.get(url, headers=UA, timeout=timeout); r.raise_for_status()
        open(path, "wb").write(r.content)
    return path

ts = load.timescale()                                   # built-in leap seconds, no download
sat = load.tle_file(get_cached("https://celestrak.org/NORAD/elements/gp.php?CATNR=60989&FORMAT=TLE", "60989.tle"))[0]
site = wgs84.latlon(49.3754, 31.1882, elevation_m=130)
for t, ev in zip(*sat.find_events(site, ts.utc(2026, 10, 31), ts.utc(2026, 11, 7), altitude_degrees=60.0)):
    if ev == 1:                                         # culmination = closest approach
        alt, az, rng = (sat - site).at(t).altaz()
        sub = wgs84.subpoint_of(sat.at(t))              # cross-track distance site<->sub-point <= 145 km => inside 290 km S2 swath
```

The full version is `scripts/sats.py`. It adds off-nadir angle, ascending or descending node, sun elevation at the pass, and the sun table and twilight. DE421 (16.8 MB, JPL) is fetched once with `requests` and a timeout, because skyfield's own downloader has no timeout knob.

**Validation against reality.** For the 5 S2 acquisitions over this point in Oct 2026, skyfield's closest-approach time was **3.5-7.3 s earlier than the STAC item `datetime`**, with TLE ages of 2-14 days. Pass timing from a 2-week-old TLE is good to seconds. The STAC time is a per-tile reference, not per-pixel.

**Passes 2026-10-31 to 2026-11-06.** Sentinel-2 counts as "in swath" when the cross-track distance is at most 145 km. Agile satellites are listed when off-nadir is at most 30° and the sun is up.

| satellite | UTC | max elev | cross-track | off-nadir | sun elev | covers point? |
|---|---|---|---|---|---|---|
| **S2C** | **2026-11-02 09:06:31** | 88.6° | 17 km | 1.2° | 25.4° | **yes** |
| **S2A** | **2026-11-04 09:06:39** | 88.6° | 18 km | 1.3° | 24.8° | **yes** |
| S2A | 2026-11-01 08:56:43 | 77.3° | 158 km | 11.2° | 25.5° | no (adjacent orbit) |
| S2B | 2026-11-04 08:56:42 | 77.4° | 158 km | 11.2° | 24.5° | no |
| S2B / S2C | 10-31 09:16:34 / 11-05 09:16:26 | 74.7° | 191-193 km | 13.5° | 25-26° | no |
| **WorldView-3** | **2026-11-03 09:22:24** | 57.5° | 354 km | 29.4° | 25.4° | only VHR access on 11-03 |
| WorldView-3 | 11-02 09:07:21 / 11-01 08:52:17 | 80.9° / 72.5° | 90 / 178 km | 8.3° / 15.9° | 25° | yes |
| Pléiades Neo 3 | 11-02 09:09:09 / 11-01 08:50:39 / 11-06 08:46:56 | | | 10.9° / 18.0° / 23.2° | 24-26° | yes |
| Pléiades Neo 4 | 11-04 08:57:56 / 10-31 09:20:09 / 11-05 09:16:24 | | | 6.9° / 26.3° / 21.4° | 25-26° | yes |
| SkySat-C1 | 11-02 05:34:53 / 11-04 05:58:18 | | | 19.5° / 29.2° | 6.4° / 9.1° | marginal light |

* **No Sentinel-2 pass covers the point on 2026-11-03.** S2B's covering passes fall on 2026-10-28 and 2026-11-07. That is inferred from its 10-day repeat (STAC: 2026-10-08), not computed in this window.
* Night ascending passes around 19:30-20:00 UTC fly over the point (for example S2C 10-31 19:48), but **MSI doesn't image the night side** (sun at -48°).
* The brief's "satellite passes once that day" fits **S2 on 2026-11-02 or 11-04, or WV-3 on 11-03 at 09:22 UTC**. Each is a mid-morning pass.

**Sun at 49.3754 N, 31.1882 E on 2026-11-03.** Local time is EET = UTC+2.

| UTC | elevation | azimuth |
|---|---|---|
| 13:30 | 7.83° | 235.5° |
| 13:40 | 6.47° | 237.5° |
| 13:50 | 5.08° | 239.5° |
| 14:00 | 3.66° | 241.5° |
| 14:10 | 2.22° | 243.4° |
| 14:20 | 0.75° | 245.3° |
| 14:30 | -0.75° | 247.2° |
| 14:40 | -2.26° | 249.1° |
| 14:50 | -3.79° | 251.0° |
| 15:00 | -5.34° | 252.8° |
| 15:10 | -6.90° | 254.7° |
| 15:20 | -8.48° | 256.5° |
| 15:30 | -10.07° | 258.4° |

Sunrise is 04:46:21 UTC. **Sunset is 14:30:35 UTC (16:30 local), at azimuth about 247° (WSW). Civil dusk ends at 15:04:14 UTC (17:04 local).** Nautical dusk ends at 15:42:02 and astronomical at 16:19:05 UTC. With a westerly wind scenario, west-looking cameras face the sunset glare.

**CelesTrak usage policy** (page updated 2026-05-22):
* "*For GP data, updates are once every 2 hours. ... only download data once per update.*"
* "*M2M software should immediately stop querying when it receives any non-HTTP 200 responses*". 50x means stop immediately.
* "*Repeatedly ignoring them will end up sending your IP address to the firewall.*"
* The page states no licence or attribution. The GP data derive from the US Space Force public catalogue, so credit "Orbital data: CelesTrak".
* Implementation consequence: **no retry loop** for CelesTrak, a 2 h cache, and raising on error. `scripts/sats.py` does exactly this.

skyfield and sgp4 are MIT-licensed. JPL DE421 is public.

Output: `scratch/geo-spike/data/sats_2026-11-03.json`

---

## 5. Weather (Open-Meteo)

```python
def open_meteo(day="2025-11-03"):
    common = dict(latitude=49.3754, longitude=31.1882, start_date=day, end_date=day, wind_speed_unit="ms", timezone="GMT")
    era5 = requests.get("https://archive-api.open-meteo.com/v1/archive", timeout=(5, 30), headers=UA, params=dict(
        common, models="era5", hourly="temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,"
                                      "wind_speed_100m,wind_direction_100m,cloud_cover,precipitation,boundary_layer_height"))
    era5.raise_for_status()
    pl = requests.get("https://historical-forecast-api.open-meteo.com/v1/forecast", timeout=(5, 30), headers=UA, params=dict(
        common, hourly="visibility,wind_speed_925hPa,wind_direction_925hPa,wind_speed_850hPa,wind_direction_850hPa"))
    pl.raise_for_status()
    e, p = era5.json()["hourly"], pl.json()["hourly"]
    if all(v is None for v in e["wind_speed_10m"]):          # out-of-horizon requests can return 200 + nulls
        raise RuntimeError("Open-Meteo returned only nulls")
    return {k: v[14] for k, v in e.items()}, {k: v[14] for k, v in p.items()}   # 14:00 UTC (~sunset)
```

The full version is `scripts/weather.py` (8 calls in total). It adds bounded retry on 429/5xx with exponential backoff and jitter, and raises with the API's `reason` on 4xx.

**ERA5 (archive-api, `models=era5`), 2025-11-03.** The grid cell is 49.50 N, 31.25 E (0.25°), elevation 191 m.

| UTC | T °C | RH % | wind 10 m | gust | wind 100 m | cloud (low) % | precip | BLH |
|---|---|---|---|---|---|---|---|---|
| 12:00 | 13.2 | 68 | 4.7 m/s from 172° | 9.9 | 7.0 m/s from 173° | 37 (11) | 0 | 685 m |
| 13:00 | 13.3 | 67 | 4.0 from 167° | 8.2 | 6.6 from 169° | 34 (16) | 0 | 700 m |
| 14:00 | 11.1 | 75 | 3.7 from 162° | 6.9 | 6.8 from 165° | 27 (8) | 0 | 655 m |
| 15:00 | 11.2 | 75 | 3.5 from 160° | 6.4 | 6.9 from 165° | 33 (9) | 0 | 480 m |
| 16:00 | 11.2 | 75 | 3.4 from 159° | 6.2 | 7.0 from 164° | 79 (13) | 0 | 390 m |

The collapsing boundary-layer height at dusk is useful for the acoustic and microphone model (stable layer, wind shear).

**Upper air and visibility (historical-forecast API, archived operational runs).** The grid point is 49.343 N, 31.220 E. At 14:00 UTC: **visibility 41.6 km**. Wind at 180 m: 8.5 m/s from 163°. At 925 hPa: **12.3 m/s from 196°**. At 850 hPa: **11.0 m/s from 214°**, geopotential 1506 m. At 700 hPa: 13.3 m/s from 217°. Levels 1000/925/850/700 hPa and 80/120/180 m are all available. **The ERA5 archive returns visibility and every pressure-level variable as null.**

**Matching the brief's "light westerly at dusk".** 2025-11-03 was SSE. Days in Nov 2025 with ERA5 14:00 UTC 10 m wind from 225-315° at 1.5-5.5 m/s:

| date | wind | cloud | notes |
|---|---|---|---|
| Nov 1 | 1.6 m/s from 313° | 99% | |
| Nov 12 | 3.1 m/s from 306° | 100% | 0.2 mm |
| Nov 15 | 3.0 m/s from 288° | 100% | |
| Nov 18 | 2.8 m/s from 284° | 93% | |
| Nov 24 | 2.2 m/s from 238° | 74% | 2.6 °C |

So a realistic November dusk is overcast.

**Coverage for 2026-11-03** (asked today, 2026-10-18):

| API | covers 2026-11-03? | detail |
|---|---|---|
| Forecast (`api.open-meteo.com/v1/forecast`) | **No** | HTTP 400 "*out of allowed range from 2026-07-17 to 2026-11-02*". 16-day horizon; the date comes into range from 2026-10-19. |
| Ensemble GFS (`gfs_seamless`, 31 members, about 35 d) | Yes | 744/744 values non-null. 14 UTC 10 m wind: median 3.7 m/s, range 1.2-9.7, directions all round the compass, so no skill yet. |
| Ensemble ECMWF IFS 0.25 | **No** | **HTTP 200 but 1224/1224 values null.** Silent failure: always count non-nulls. |
| Seasonal (daily, 51 members) | Yes | `six_hourly` returned an empty body. |
| Climate API (CMIP6 HighResMIP, **daily only**) | Yes | EC_Earth3P_HR: 9.8 °C, wind 6.7 m/s mean, cloud 100%. A synthetic climate draw, not a forecast. |

**Recommendation.** Drive scenarios from a **real analogue day** (ERA5 surface plus historical-forecast upper air) chosen to match the requested conditions. It is reproducible, has hourly data and costs one call. Use the forecast API only for a live demo inside 16 days.

**Terms (open-meteo.com/en/terms, /en/licence)**
* Free tier: "*You may only use the free API services for non-commercial purposes*". Limits are **<10,000 calls/day, 5,000/h, 600/min (300,000/month)**.
* Data are **CC BY 4.0**. Attribution: `<a href="https://open-meteo.com/">Weather data by Open-Meteo.com</a>`, placed next to wherever the data are displayed.
* Upstream: reanalysis comes from Copernicus C3S under the Copernicus licence. Add "Contains modified Copernicus Climate Change Service information [year]"; this is the standard C3S wording, not re-verified on Open-Meteo's page.
* Commercial use needs a paid plan. **Flag this for the team:** check whether a Psylone-run hackathon is "commercial".

Output: `scratch/geo-spike/data/weather.json`

---

## 6. OpenStreetMap: Overpass + Nominatim

```python
def overpass_masts(lat, lon, half_km=6.0):
    w, s, e, n = bbox(lat, lon, half_km)
    q = (f'[out:json][timeout:60][bbox:{s:.4f},{w:.4f},{n:.4f},{e:.4f}];'
         'nwr[man_made~"^(mast|tower|communications_tower|water_tower)$"];out tags center;')
    for k, url in enumerate(["https://overpass-api.de/api/interpreter", "https://lz4.overpass-api.de/api/interpreter",
                             "https://overpass-api.de/api/interpreter"]):
        r = requests.post(url, data={"data": q}, headers=UA, timeout=(10, 75))
        if r.status_code == 200:
            return [(el["tags"].get("man_made"), el["tags"].get("height"), el.get("lat") or el["center"]["lat"],
                     el.get("lon") or el["center"]["lon"]) for el in r.json()["elements"]]
        if r.status_code not in (429, 500, 502, 503, 504):
            r.raise_for_status()
        time.sleep(2 ** k * (0.5 + np.random.rand()))         # exp backoff + jitter, bounded attempts
    raise RuntimeError(f"Overpass unavailable: HTTP {r.status_code}")

def nominatim(q="Korsun-Shevchenkivskyi"):
    r = requests.get("https://nominatim.openstreetmap.org/search", headers=UA, timeout=(5, 20),
                     params=dict(q=q, format="jsonv2", limit=1))
    r.raise_for_status()                                       # policy: <=1 req/s, identify UA, cache results
    j = r.json()[0]
    return j["display_name"], float(j["lat"]), float(j["lon"])
```

The full query in `scripts/osm.py` fetches places, roads, rail, bridges, power, man_made towers, worship, quarries, waterways, water, aeroway and military with `out tags geom qt;`. It returned **1,453 elements and 921 KB of JSON in 52 s**, including one 502 and a backoff before `lz4.` answered. The OSM data timestamp is 2026-10-18T09:59:36Z.

**What's in the 12 km box (S 49.3215, W 31.1054, N 49.4293, E 31.2710)**

*Places*
* Towns: **Korsun-Shevchenkivskyi** (pop. 18,266; 49.4180, 31.2557) and **Stebliv** (49.4019, 31.0956, just west).
* Villages: Yablunivka (517), Datsky (351), Lystvyna (549), Petrushky (452), Prutyltsi (194), **Peremozhyntsi** (357; 2.2 km S of the point), Tarashcha (351), Selyshche (1,576), Huta-Selytska (211), Kvitky, Hlushky.
* Several villages appear twice in OSM (as both a node and an area), so deduplicate by name.

*Roads* (lengths clipped to the box): residential 140.6 km, track 135.0, tertiary 51.9, service 21.6, secondary 19.6, unclassified 5.8, primary 5.1.

*Bridges* (32 in total):
* Primary-road Ros bridge, 272 m, at 49.4057, 31.2478 (Korsun)
* Secondary bridge at 49.4100, 31.1802 (Yablunivka)
* Korsun street bridges at 49.4115, 31.2569 and 49.4212, 31.2589

*Power*
* 33 lines: **35 kV, 39.2 km** and **110 kV, 17.5 km** clipped to the box. Un-clipped way lengths total 177 km, so clip before reporting.
* 175 pylons and 9 substations.
* Hydro plants: **Stebliv HPP** (dam at 49.4073, 31.1085) and **Korsun-Shevchenkivska HPP** (1.8 MW, 49.4121, 31.2634).

*Tall structures* (sensor-site candidates):

| structure | lat, lon | notes |
|---|---|---|
| Comms mast | 49.3926, 31.1109 | **58 m**, near Stebliv; ground about 180 m |
| Comms mast | 49.3311, 31.1597 | **52 m**, Selyshche |
| Comms mast | 49.4187, 31.2456 | Korsun |
| Comms mast | 49.4136, 31.2506 | Korsun |
| Comms mast | 49.4188, 31.2557 | Korsun |
| Water tower | 49.4168, 31.2526 | Korsun |
| Water tower | 49.4076, 31.1119 | Stebliv |
| Chimney | 49.3321, 31.1522 | |
| Chimney | 49.4234, 31.2620 | |

*Churches* (7 places of worship):
* Korsun: cathedral 49.4154, 31.2534; Transfiguration 49.4160, 31.2624; St Elijah 49.4199, 31.2618; chapel 49.4086, 31.2408
* Selyshche church: 49.3281, 31.1506
* Adventist church: 49.4223, 31.2624

*Other*
* **Small aerodrome "Корсунь-Шевченківський"** with a runway at about 49.4249, 31.2303, useful for light-aircraft tracks.
* 5 quarries, including the Syvach granite pit and a sand pit at 49.3946, 31.2470.
* 9 pond dams. No `military=*` objects.

**Nominatim.** "Korsun-Shevchenkivskyi" resolves to `relation/3629084`, **49.4180370 N, 31.2556741 E**, type town, Cherkasy Raion, Cherkasy Oblast, postcode 19400-19408, bbox 49.392-49.450 N, 31.221-31.333 E. Reverse geocoding the truth point gives *Steblivska selyshchna hromada, Zvenyhorodka Raion*. Three calls took 3.1 s with 1.1 s spacing. Distance from the truth point to Korsun is 6.81 km.

**Usage policies**
* **Nominatim:** "*an absolute maximum of 1 request per second*". "*Provide a valid HTTP Referer or User-Agent identifying the application*". "*Results must be cached on your side*". Bulk geocoding is discouraged and client-side autocomplete is forbidden. Violations get you banned.
* **Overpass** (dev.overpass-api.de commons): "*a maximum of about 10000 requests per day*", "*download volume below about 1 GB per day*", 429 when rate-limited, and queued requests wait up to 15 s for a slot. It lists "*setting up an app for more than just OSM mappers and relying on the public instances as backend*" as problematic. Today the main instance's 502 page said "*This public endpoint is intended for browser-based and human-operated tools. For automated or high-volume use, run a local Overpass API instance*".
* Therefore: **fetch once per scenario region at build time, store the JSON with the scenario (S3), and never call Overpass at scenario-generation time.** The offline alternative, Geofabrik `ukraine-latest.osm.pbf` plus pyosmium, is untested because the host timed out.

**Licence: ODbL 1.0.** Attribution is "**© OpenStreetMap contributors**", linked to https://www.openstreetmap.org/copyright. Derived *databases* (for example our extracted sensor-site table) are share-alike if publicly used. *Produced works* (rendered maps, scenario outputs) need only the attribution.

Outputs:
* `scratch/geo-spike/data/osm_korsun.json` (raw)
* `scratch/geo-spike/data/osm_korsun_summary.json`

---

## 7. Alternative Ukrainian sites with stronger relief

All windows are 12x12 km on the GLO-30 DSM (`scripts/dem.py`, `worldcover.py`, `terrain_los.py`). The viewshed uses two auto-picked open-ground high points about 6 km apart with 10 m masts. "Hidden" means the share of the box hidden from **both** receivers.

| site (centre) | DSM min-max (m) | std | 1 km relief median / p90 / max | slope p95 | land cover | hidden at 30 / 60 / 120 m AGL |
|---|---|---|---|---|---|---|
| Brief: Korsun / Ros (49.3754, 31.1882) | 56*-232 (river 99) | 27.4 | 52 / 70 / 101 | 14.0° | crop 49, tree 38 | 20 / 2 / 0% |
| **Kaniv hills**, Dnipro right bank, Cherkasy Oblast (**49.7200, 31.5000**) | 78-273 | 56.6 | 64 / 99 / 153 | 19.3° | tree 65, crop 12, grass 10, water 9.5 | **55 / 26 / 2%**; seen by exactly one receiver 43 / 63 / 49% |
| **Dniester canyon at Zalishchyky**, Ternopil Oblast (**48.6400, 25.7400**) | 138-331 | 43.9 | 50 / **137** / 159 | 18.6° | crop 63, tree 24 | 14 / 9 / 0.5%; receiver B still 9.7% hidden at 120 m |
| **Yaremche, Prut valley, Carpathians**, Ivano-Frankivsk Oblast (**48.4500, 24.5600**) | 424-1462 | 189 | 271 / 356 / 483 | 32.0° | tree 83, grass 14 | 69 / 60 / **44%** |
| Rzhyshchiv, Dnipro right bank, Kyiv Oblast (49.9700, 31.0500) | 89-204 | 35.5 | 52 / 86 / 102 | 13.7° | tree 36, crop 30, water 16 | 14 / 2 / 0% |

\* 56 m is the quarry pit.

Recommendation, in order:
1. **Kaniv hills.** This is the drop-in upgrade: same oblast, about 40 km NE, the same farmland, forest and river character, plus the Dnipro (Kremenchuk reservoir, about 80 m) and the Kaniv dam just north of the box. The relief is heavily dissected ravines rising about 190 m above the water. Even at 60 m AGL, a quarter of the box is hidden from both receivers. The random-track search found **131 s** single-receiver occlusions at 60 m AGL and 20 m/s. Hillshade: `scratch/geo-spike/data/hillshade_kaniv.png`
2. **Dniester canyon.** A flat plateau at about 300 m cut by a meandering canyon about 150-190 m deep. It is the cleanest "drone flies up a canyon, invisible to plateau sensors" story.
3. **Carpathians at Yaremche.** Extreme masking that persists to 120 m AGL. Receiver siting matters a lot: our auto-pick put receiver A on the far side of a ridge, and it sees only 2-3% of the box. The DSM is dominated by forest canopy (83% tree), and the area is not farmland.

Rzhyshchiv gives little over Korsun. It is still useful as a test of a cross-tile mosaic straddling 50 N, where the longitude spacing changes.

---

## 8. Cross-cutting engineering notes

* **Silent-failure traps found:**
  * S2 window clipped at the MGRS tile edge (smaller array, no error).
  * `rasterio.merge` left the edge row empty.
  * Open-Meteo returns HTTP 200 with all-null arrays beyond a model's horizon.
  * ERA5 archive returns null visibility and pressure levels.
  * Nominatim reverse at zoom 17 returns the nearest street, not the quarry polygon.

  Each script now checks shape, holes or nulls and raises.
* **Every network call is bounded:**
  * GDAL: `GDAL_HTTP_TIMEOUT=30`, `CONNECTTIMEOUT=10`, `MAX_RETRY=3` with GDAL's own backoff.
  * requests: `(connect, read)` timeouts on every call.
  * Overpass: server-side `[timeout:]` plus a client timeout.
  * Retries are bounded, use exponential backoff with jitter, and only fire on 429/5xx or timeouts.
  * CelesTrak: no retry, stop on any non-200 (policy).
  * Nominatim: 1.1 s spacing.
* **Cache and provenance.** Fetch context once per scenario region at build time. Store the DEM and WorldCover windows (about 1 MB), S2 bands (about 10 MB), OSM JSON (about 1 MB), weather JSON and TLE in the scenario bundle (S3), with the source URL, fetch time, STAC item ID, TLE epoch and licence string. Generation is then offline, deterministic and reproducible, and survives Overpass or Open-Meteo outages. Log fetch failures as warnings or errors with source name, HTTP status, retry count and timeout cause.
* **Cost.** All S3 sources are AWS Open Data with free egress. Earth Search assets for C1 are in us-west-2, at about 2-4 s per window from here.
* **What feeds which sensor:**
  * RF: DEM plus explicit forest for LOS and diffraction; masts from OSM.
  * Camera: S2 background, sun azimuth and elevation, visibility, canopy occlusion.
  * Microphone: wind and temperature profile, boundary-layer height, terrain.
  * Radar: DEM masking, WorldCover clutter class, power lines and pylons as clutter.
  * Satellite: pass time and geometry from skyfield, swath test, cloud, inter-band offsets.

## 9. Attribution block (copy into the app and dataset README)

* produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved. The organisations in charge of the Copernicus programme by law or by delegation do not incur any liability for any use of the Copernicus WorldDEM-30.
* © ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium (CC BY 4.0).
* Contains modified Copernicus Sentinel data [year of scene] (Sentinel-2 L2A via Element 84 Earth Search).
* Weather data by Open-Meteo.com (CC BY 4.0); contains modified Copernicus Climate Change Service information [year].
* © OpenStreetMap contributors (ODbL 1.0), https://www.openstreetmap.org/copyright.
* Orbital elements: CelesTrak (celestrak.org). Ephemeris: JPL DE421. Propagation: skyfield/SGP4.

## 10. Sources

* Copernicus DEM README on AWS: https://copernicus-dem-30m.s3.amazonaws.com/readme.html. Licence PDF: https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/DEM/resources/license/License-COPDEM-30.pdf
* Copernicus DEM GLO-30 on GEE (EGM2008, edited DSM): https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_DEM_GLO30_2024_1
* X-band partial canopy penetration: search summary of TanDEM-X vegetation-bias literature, for example https://earthbridge.eu/is-tandem-x-a-dtm-or-dsm/
* ESA WorldCover v200 (CC BY 4.0, Zanaga et al. 2022, doi:10.5281/zenodo.7254221): https://developers.google.com/earth-engine/datasets/catalog/ESA_WorldCover_v200
* Earth Search v1: https://element84.com/blog/introducing-earth-search-v1-new-datasets-now-available
* Copernicus Sentinel data legal notice: https://sentinel.esa.int/documents/247904/690755/Sentinel_Data_Legal_Notice and https://ewds.climate.copernicus.eu/licences/ec-sentinel
* Binet, Bergsma, Poulain (2022), Accurate Sentinel-2 inter-band time delays, ISPRS Annals V-1-2022-57: https://isprs-annals.copernicus.org/articles/V-1-2022/57/2022/
* Krauß (2021), Extraction of cloud heights from Sentinel-2 multispectral images, ISPRS Annals V-1-2021-17: https://isprs-annals.copernicus.org/articles/V-1-2021/17/2021/isprs-annals-V-1-2021-17-2021.pdf
* Moving trucks via S2 inter-band offset, MDPI Remote Sensing 14(7):1595 (2022): https://www.mdpi.com/2072-4292/14/7/1595
* CelesTrak usage policy: https://celestrak.org/usage-policy.php
* Open-Meteo terms and licence: https://open-meteo.com/en/terms, https://open-meteo.com/en/licence
* Nominatim policy: https://operations.osmfoundation.org/policies/nominatim/. Overpass commons: https://dev.overpass-api.de/overpass-doc/en/preface/commons.html
* HOT OpenAerialMap STAC: https://api.imagery.hotosm.org/stac

## 11. File inventory (all under the spike root)

Scripts (`.../geo-spike/scripts/`):
* `common.py`: AOI, GDAL env, timing
* `dem.py`: item 1
* `worldcover.py`: item 2
* `terrain_los.py`: viewshed and receiver pick
* `canopy_tracks.py`: canopy step and occlusion runs
* `s2.py`: item 3
* `sats.py`: item 4
* `weather.py`: item 5
* `osm.py`: item 6
* `snippets.py`: tested minimal versions
* `summ_dem.py`

Data (`.../geo-spike/data/`):
* `dem_<site>.tif/.json`
* `hillshade_<site>.png`
* `worldcover_<site>.tif/.png/.json`
* `viewshed30_<site>.png`
* `terrain_los_<site>.json`
* `s2_*.png`
* `s2_20250903_B02B03B04B08.tif`
* `s2.json`
* `sats_2026-11-03.json`
* `tle/*.tle`
* `de421.bsp`
* `weather.json`
* `osm_korsun.json`
* `osm_korsun_summary.json`
* `docs/` (licence and paper copies)

Sites are `korsun`, `kaniv`, `rzhyshchiv`, `dniester_zalishchyky` and `yaremche`.
