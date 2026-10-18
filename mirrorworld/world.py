"""Real terrain: Copernicus GLO-30 DEM, resampled onto a local equirectangular frame.

Local frame: x east, y north of (cfg.area.lat, cfg.area.lon), metres via config.M_PER_DEG.
Grid: 30 m spacing covering the area square plus a 1 km margin.
"""
import math
from pathlib import Path

import numpy as np
import rasterio
from rasterio.merge import merge

from .config import M_PER_DEG, Scenario

K_REFRACT = 4.0 / 3.0  # earth-radius factor for standard refraction
R_EARTH = 6371e3
CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"
DEM_TILE = (
    "https://copernicus-dem-30m.s3.amazonaws.com/"
    "Copernicus_DSM_COG_10_N{lat:02d}_00_E{lon:03d}_00_DEM/"
    "Copernicus_DSM_COG_10_N{lat:02d}_00_E{lon:03d}_00_DEM.tif"
)


class World:
    def __init__(self, cfg: Scenario):
        self.lat0, self.lon0 = cfg.area.lat, cfg.area.lon
        self.cos0 = math.cos(math.radians(self.lat0))
        half = cfg.area.size_km * 500.0 + 1000.0  # area square + 1 km margin
        self.spacing = 30.0
        self.n = int(math.floor(2 * half / self.spacing)) + 1
        self.x0 = self.y0 = -self.spacing * (self.n - 1) / 2.0  # symmetric about the centre

        cache = CACHE_DIR / f"dem_{cfg.area.lat:g}_{cfg.area.lon:g}_{cfg.area.size_km:g}.npz"
        if cache.exists():
            with np.load(cache) as z:
                if z["grid"].shape == (self.n, self.n):
                    self.grid = z["grid"]
                    self.sources = [str(u) for u in z["sources"]]
                    return
        self.grid, self.sources = self._fetch(half)
        CACHE_DIR.mkdir(exist_ok=True)
        np.savez_compressed(cache, grid=self.grid, sources=np.array(self.sources))

    # --- frame -----------------------------------------------------------
    def to_xy(self, lat, lon):
        lat = np.asarray(lat, dtype=np.float64)
        lon = np.asarray(lon, dtype=np.float64)
        x = (lon - self.lon0) * M_PER_DEG * self.cos0
        y = (lat - self.lat0) * M_PER_DEG
        return x, y

    def to_ll(self, x, y):
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        lat = self.lat0 + y / M_PER_DEG
        lon = self.lon0 + x / (M_PER_DEG * self.cos0)
        return lat, lon

    # --- terrain ---------------------------------------------------------
    def height(self, x, y):
        """Bilinear height on the grid; ValueError if any point is outside it."""
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        fi = (x - self.x0) / self.spacing
        fj = (y - self.y0) / self.spacing
        if ((fi < 0) | (fi > self.n - 1) | (fj < 0) | (fj > self.n - 1)).any():
            raise ValueError("point outside the DEM grid")
        ci = np.floor(fi).astype(np.intp)
        cj = np.floor(fj).astype(np.intp)
        i0 = np.clip(ci, 0, self.n - 2)
        j0 = np.clip(cj, 0, self.n - 2)
        di, dj = fi - ci, fj - cj
        g = self.grid
        return (
            g[j0, i0] * (1 - di) * (1 - dj)
            + g[j0, i0 + 1] * di * (1 - dj)
            + g[j0 + 1, i0] * (1 - di) * dj
            + g[j0 + 1, i0 + 1] * di * dj
        )

    def profile(self, xa, ya, xb, yb, n):
        """Heights at n evenly spaced points a->b inclusive; output shape (..., n)."""
        xa, ya, xb, yb = np.broadcast_arrays(
            np.asarray(xa, float), np.asarray(ya, float),
            np.asarray(xb, float), np.asarray(yb, float),
        )
        ts = np.linspace(0.0, 1.0, n)
        return self.height(
            xa[..., None] + (xb - xa)[..., None] * ts,
            ya[..., None] + (yb - ya)[..., None] * ts,
        )

    def los(self, a, b):
        """True when the ray a->b (x, y, z MSL) clears terrain strictly between the
        endpoints, with the earth-curvature bulge d1*d2/(2*k*R) added to terrain."""
        a, b = np.broadcast_arrays(np.asarray(a, float), np.asarray(b, float))
        if a.shape[-1] != 3:
            raise ValueError("los expects (..., 3) arrays of x, y, z")
        dx, dy, dz = b[..., 0] - a[..., 0], b[..., 1] - a[..., 1], b[..., 2] - a[..., 2]
        dist = np.hypot(dx, dy)
        n = int(np.clip((dist.max() if dist.size else 0.0) / 30.0, 16, 512))
        ts = np.linspace(0.0, 1.0, n + 2)[1:-1]  # n samples strictly between endpoints
        xs = a[..., 0, None] + dx[..., None] * ts
        ys = a[..., 1, None] + dy[..., None] * ts
        zs = a[..., 2, None] + dz[..., None] * ts
        d1 = dist[..., None] * ts  # horizontal distance from a and to b
        d2 = dist[..., None] * (1.0 - ts)
        bulge = d1 * d2 / (2 * K_REFRACT * R_EARTH)
        return bool((zs > (self.height(xs, ys) + bulge)).all(axis=-1)) if a.ndim == 1 \
            else (zs > (self.height(xs, ys) + bulge)).all(axis=-1)

    def min_visible_agl(self, site, x, y, chunk=3000):
        """Lowest height above ground at which each (x, y) has a clear ray to `site` (x, y, z MSL).
        A per-sensor terrain-shadow map: route drones through it, overlay it in the viewer."""
        x, y = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float))
        out = np.empty(x.size)
        for a in range(0, x.size, chunk):
            xs, ys = x.flat[a:a + chunk], y.flat[a:a + chunk]
            D = np.maximum(np.hypot(xs - site[0], ys - site[1]), 1.0)
            n = max(int(np.ceil(D.max() / 30.0)) + 1, 16)
            h = self.profile(np.full(xs.shape, site[0]), np.full(xs.shape, site[1]), xs, ys, n)
            di = D[:, None] * np.linspace(0.0, 1.0, n)[1:-1]
            hi = h[:, 1:-1] + di * (D[:, None] - di) / (2 * K_REFRACT * R_EARTH)
            z_need = (site[2] + (hi - site[2]) * D[:, None] / di).max(axis=1)
            out[a:a + chunk] = np.maximum(z_need - h[:, -1], 0.0)
        return out.reshape(x.shape)

    # --- DEM fetch -------------------------------------------------------
    def _fetch(self, half):
        lon_h = half / (M_PER_DEG * self.cos0)
        lat_h = half / M_PER_DEG
        lon_min, lon_max = self.lon0 - lon_h, self.lon0 + lon_h
        lat_min, lat_max = self.lat0 - lat_h, self.lat0 + lat_h
        urls = [
            DEM_TILE.format(lat=la, lon=lo)
            for la in range(math.floor(lat_min), math.floor(lat_max) + 1)
            for lo in range(math.floor(lon_min), math.floor(lon_max) + 1)
        ]
        env = {"GDAL_HTTP_TIMEOUT": "20", "GDAL_HTTP_MAX_RETRY": "3", "GDAL_HTTP_RETRY_DELAY": "2"}
        srcs = []
        try:
            with rasterio.Env(**env):
                for url in urls:
                    try:
                        srcs.append(rasterio.open("/vsicurl/" + url))
                    except Exception as e:
                        raise RuntimeError(f"DEM fetch failed for {url}: {e}") from e
                try:
                    merged, transform = merge(srcs, bounds=(lon_min, lat_min, lon_max, lat_max), masked=True)
                except Exception as e:
                    raise RuntimeError(f"DEM merge failed for {urls}: {e}") from e
        finally:
            for s in srcs:
                s.close()

        src = np.ma.filled(merged[0].astype(np.float32), np.nan)
        # Local grid points map affinely to lat/lon, so bilinear resample is separable.
        axes = self.x0 + self.spacing * np.arange(self.n)
        lons = self.lon0 + axes / (M_PER_DEG * self.cos0)
        lats = self.lat0 + axes / M_PER_DEG
        col = (lons - transform.c) / transform.a - 0.5  # pixel centres
        row = (lats - transform.f) / transform.e - 0.5
        c0 = np.floor(col).astype(np.intp)
        r0 = np.floor(row).astype(np.intp)
        dc, dr = col - c0, row - r0
        i0 = np.clip(c0, 0, src.shape[1] - 2)
        j0 = np.clip(r0, 0, src.shape[0] - 2)
        grid = (
            src[np.ix_(j0, i0)] * ((1 - dr)[:, None] * (1 - dc)[None, :])
            + src[np.ix_(j0, i0 + 1)] * ((1 - dr)[:, None] * dc[None, :])
            + src[np.ix_(j0 + 1, i0)] * (dr[:, None] * (1 - dc)[None, :])
            + src[np.ix_(j0 + 1, i0 + 1)] * (dr[:, None] * dc[None, :])
        ).astype(np.float32)
        if not np.isfinite(grid).all():
            raise RuntimeError(f"DEM has voids in tiles {urls} near ({self.lat0}, {self.lon0})")
        return grid, urls
