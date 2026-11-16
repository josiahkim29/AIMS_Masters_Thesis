import xarray as xr, numpy as np, sys, warnings
warnings.filterwarnings("ignore")
OUT = sys.argv[1]
so = {"token": "anon"}
paths = {
 "graphcast": "gs://weatherbench2/datasets/graphcast_hres_init/2020/date_range_2019-11-16_2021-02-01_12_hours-64x32_equiangular_conservative.zarr",
 "pangu": "gs://weatherbench2/datasets/pangu_hres_init/2020_0012_64x32_equiangular_conservative.zarr",
 "neuralgcm": "gs://weatherbench2/datasets/neuralgcm_deterministic/2020-64x32_equiangular_conservative.zarr",
 "ifshres": "gs://weatherbench2/datasets/hres/2016-2022-0012-64x32_equiangular_conservative.zarr",
}
leads = np.array([24*k for k in range(1, 11)], dtype="timedelta64[h]")
fc = {}
for k, p in paths.items():
    z = xr.open_zarr(p, storage_options=so)["geopotential"].sel(level=500)
    z = z.sel(time=slice("2020-01-01T00", "2020-12-31T12"), prediction_timedelta=leads).load()
    z = z.transpose("time", "prediction_timedelta", "latitude", "longitude")
    print(k, z.shape, int(z.isnull().sum()), flush=True)
    fc[k] = z.drop_vars("level", errors="ignore")
ds = xr.Dataset(fc)
ds.to_netcdf(f"{OUT}/forecasts_z500_2020.nc")
era = xr.open_zarr("gs://weatherbench2/datasets/era5/1959-2023_01_10-6h-64x32_equiangular_conservative.zarr", storage_options=so)["geopotential"].sel(level=500)
era = era.sel(time=slice("2019-10-01T00", "2021-01-12T00")).load()
era = era.transpose("time", "latitude", "longitude").drop_vars("level", errors="ignore")
print("era5", era.shape, flush=True)
era.to_dataset(name="era5").to_netcdf(f"{OUT}/era5_z500.nc")
clim = xr.open_zarr("gs://weatherbench2/datasets/era5-hourly-climatology/1990-2019_6h_64x32_equiangular_conservative.zarr", storage_options=so)["geopotential"].sel(level=500).load()
clim = clim.drop_vars("level", errors="ignore")
print("clim", dict(clim.sizes), flush=True)
clim.to_dataset(name="clim").to_netcdf(f"{OUT}/clim_z500.nc")
