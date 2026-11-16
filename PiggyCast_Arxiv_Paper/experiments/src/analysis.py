import sys, numpy as np, pandas as pd, xarray as xr
S=sys.argv[1]; rng=np.random.default_rng(0)
LEADS=[24*k for k in range(1,11)]
pairs=[("lin_clim","neuralgcm"),("mmm","neuralgcm"),("xgb_orig","neuralgcm"),("xgb_orig","mmm"),("lin_clim","mmm"),("xgb_resid","mmm"),("lin","mmm"),("xgb_orig","lin_clim")]
rows=[]
for L in LEADS:
    z=np.load(f"{S}/res/mse_series_gapsafe_{L}.npz")
    n=len(z["times"]); B=10; nb=int(np.ceil(n/B))
    starts=rng.integers(0,n-B+1,size=(2000,nb))
    idx=(starts[...,None]+np.arange(B)).reshape(2000,-1)[:, :n]
    for a,b in pairs:
        ra=np.sqrt(z[a].mean()); rb=np.sqrt(z[b].mean())
        da=np.sqrt(z[a][idx].mean(1))-np.sqrt(z[b][idx].mean(1))
        lo,hi=np.percentile(da,[2.5,97.5])
        rows.append(dict(lead=L,a=a,b=b,diff=ra-rb,pct=100*(ra-rb)/rb,lo=lo,hi=hi,sig=(hi<0) or (lo>0)))
df=pd.DataFrame(rows); df.to_csv(f"{S}/res/bootstrap.csv",index=False)
pd.set_option("display.width",200)
print(df.assign(ci=lambda d: d.lo.round(1).astype(str)+".."+d.hi.round(1).astype(str)).pivot(index="lead",columns=["a","b"],values="pct").round(1).to_string())
print(df[~df.sig][["lead","a","b","diff","lo","hi"]].round(2).to_string())
# error correlation between base models (area-weighted, on full common window)
fc=xr.open_dataset(f"{S}/data/forecasts_z500_2020.nc"); era=xr.open_dataset(f"{S}/data/era5_z500.nc")["era5"]
V=pd.date_range("2020-01-11T00","2021-01-01T12",freq="12h")
w=np.cos(np.deg2rad(fc.latitude.values))[:,None]*np.ones(64)[None]; w=(w/w.sum()).ravel()
M=["neuralgcm","graphcast","ifshres","pangu"]; out={}
y=era.sel(time=V.values).values.reshape(len(V),-1)
for L in [72,240]:
    E=[]
    for m in M:
        f=fc[m].sel(prediction_timedelta=np.timedelta64(L,"h")).sel(time=(V-pd.Timedelta(hours=L)).values).transpose("time","latitude","longitude").values.reshape(len(V),-1)
        e=f-y; e=e-(e*w).sum(1,keepdims=True)*0  # raw errors
        E.append(e)
    C=np.zeros((4,4))
    for i in range(4):
        for j in range(4):
            C[i,j]=(E[i]*E[j]*w).sum()/np.sqrt((E[i]**2*w).sum()*(E[j]**2*w).sum())
    print(L, pd.DataFrame(C,index=M,columns=M).round(2).to_string(), sep="\n")
    np.save(f"{S}/res/errcorr_{L}.npy",C)
