"""Download multi-year Z500 forecasts (5.625 deg) for the more-data side experiment.

Writes data/multiyear_z500.nc with one variable per source, each [time(init), lead, lat, lon],
00/12 UTC initialisations only, leads 24..240 h:
  ifshres      IFS HRES                          2017-12-01 .. 2022-12-31
  pangu_hres   Pangu-Weather, HRES-initialised   2020-01-01 .. 2022-12-31  (same source as the paper)
  pangu_era5   Pangu-Weather, ERA5-initialised   2018-01-01 .. 2022-12-31
  gc_era5      GraphCast (v2), ERA5-initialised  2018, 2020, 2022 files (gaps in 2019 and 2021)
and data/era5_z500_multiyear.nc (ERA5 Z500, 2017-12-01 .. 2023-01-10).
Usage: python src/download_multiyear.py <data dir>
"""
import sys, warnings
import numpy as np, pandas as pd, xarray as xr

warnings.filterwarnings("ignore")
OUT = sys.argv[1]
so = {"token": "anon"}
B = "gs://weatherbench2/datasets/"
SRC = {
    "ifshres": ["hres/2016-2022-0012-64x32_equiangular_conservative.zarr"],
    "pangu_hres": [f"pangu_hres_init/{y}_0012_64x32_equiangular_conservative.zarr" for y in (2020, 2021, 2022)],
    "pangu_era5": ["pangu/2018-2022_0012_64x32_equiangular_conservative.zarr"],
    "gc_era5": [f"graphcast_v2/{y}-64x32_equiangular_conservative.zarr" for y in (2018, 2020, 2022)],
}
leads = np.array([24 * k for k in range(1, 11)], dtype="timedelta64[h]")
T0, T1 = "2017-12-01T00", "2022-12-31T12"

fc = {}
for name, paths in SRC.items():
    parts = []
    for p in paths:
        z = xr.open_zarr(B + p, storage_options=so, decode_timedelta=True)["geopotential"].sel(level=500)
        t = pd.DatetimeIndex(z.time.values)
        keep = t[(t.hour % 12 == 0) & (t >= T0) & (t <= T1)]
        z = z.sel(time=keep, prediction_timedelta=leads).load()
        z.attrs = {}
        for v in z.coords:
            z[v].attrs = {}
        parts.append(z.transpose("time", "prediction_timedelta", "latitude", "longitude").drop_vars("level", errors="ignore"))
        print(name, p.split("/")[-1], z.shape, str(keep[0])[:13], str(keep[-1])[:13], int(z.isnull().sum()), flush=True)
    a = xr.concat(parts, "time")
    a = a.isel(time=~pd.DatetimeIndex(a.time.values).duplicated())
    fc[name] = a.sortby("time")
ds = xr.Dataset(fc).astype("float32")
ds.attrs = {}
ds.to_netcdf(f"{OUT}/multiyear_z500.nc")

era = xr.open_zarr(B + "era5/1959-2023_01_10-6h-64x32_equiangular_conservative.zarr", storage_options=so)["geopotential"].sel(level=500)
era = era.sel(time=slice(T0, "2023-01-10T12")).load().transpose("time", "latitude", "longitude").drop_vars("level", errors="ignore")
print("era5", era.shape, flush=True)
era.to_dataset(name="era5").to_netcdf(f"{OUT}/era5_z500_multiyear.nc")
