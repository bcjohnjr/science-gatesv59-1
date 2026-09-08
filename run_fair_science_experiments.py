#!/usr/bin/env python3
from copy import deepcopy
from pathlib import Path
import os
import json, math, time
import numpy as np
import pandas as pd
from fair import FAIR
from fair.interface import fill, initialise
from fair.io import read_properties

ROOT=Path('.')
FREP=Path(os.environ.get('FAIR_SOURCE_DIR', 'FAIR-v2.2.4'))
D=FREP/'examples/data/calibrated_constrained_ensemble'
PAR=D/'calibrated_constrained_parameters_calibration1.4.1.csv'
SP=D/'species_configs_properties_calibration1.4.1.csv'
EM=D/'extensions_1750-2500.csv'
FO=D/'volcanic_solar.csv'
TR=ROOT/'external_validation_net_co2_trajectory.csv'
OUT=ROOT
cfg=pd.read_csv(PAR,index_col=0)
assert len(cfg)==841
ids=np.asarray(cfg.index.astype(str)); base=np.asarray(cfg['baseline_concentration[CO2]'],float)
conv=2.124*(44.009/12.011)
can=pd.read_csv(TR).sort_values('year').reset_index(drop=True)
req=['year','gross_co2_gtco2','permafrost_co2_gtco2','stored_carbon_reversal_gtco2','cdr_gtco2','net_co2_gtco2']
assert all(c in can for c in req) and int(can.year.iloc[0])==2026 and int(can.year.iloc[-1])==2183
chk=can.gross_co2_gtco2+can.permafrost_co2_gtco2+can.stored_carbon_reversal_gtco2-can.cdr_gtco2
assert float(np.max(np.abs(chk-can.net_co2_gtco2)))<1e-9
last=can.iloc[-1]
CAN_CDR=float(can.cdr_gtco2.sum()); PEAK=float(can.cdr_gtco2.max())
LC=float(last.cdr_gtco2); LG=float(last.gross_co2_gtco2); LP=float(last.permafrost_co2_gtco2); LR=float(last.stored_carbon_reversal_gtco2)

def q(x): return [float(v) for v in np.quantile(np.asarray(x,float),[.05,.5,.95])]
def ix(f,y): return int(np.argmin(np.abs(np.asarray(f.timebounds,float)-float(y))))
def paths(extra=0.0,end=2400):
    on={};off={};cdr={}
    for r in can.itertuples(index=False):
        y=int(r.year); on[y]=float(r.net_co2_gtco2); off[y]=float(r.gross_co2_gtco2+r.permafrost_co2_gtco2+r.stored_carbon_reversal_gtco2); cdr[y]=float(r.cdr_gtco2)
    for y in range(2184,end+1):
        on[y]=LG+LP+LR-LC-extra; off[y]=LG+LP+LR; cdr[y]=LC+extra
    return on,off,cdr

def make(end=2400,propfn=None):
    f=FAIR(ch4_method='Thornhill2021'); f.define_time(1750,end,1); f.define_scenarios(['medium-extension']); f.define_configs(cfg.index)
    species,props=read_properties(filename=SP)
    if propfn: props=propfn(species,props)
    f.define_species(species,props); f.allocate(); return f,species,props

def init(f):
    f.fill_species_configs(SP); f.override_defaults(PAR)
    initialise(f.concentration,f.species_configs['baseline_concentration']); initialise(f.forcing,0); initialise(f.temperature,0)
    initialise(f.cumulative_emissions,0); initialise(f.airborne_emissions,0); initialise(f.ocean_heat_content_change,0)

def std(net,end=2400):
    f,_,_=make(end); f.fill_from_csv(emissions_file=EM,forcing_file=FO)
    fill(f.forcing,f.forcing.sel(specie='Volcanic')*cfg['forcing_scale[Volcanic]'].values.squeeze(),specie='Volcanic')
    fill(f.forcing,f.forcing.sel(specie='Solar')*cfg['forcing_scale[Solar]'].values.squeeze(),specie='Solar')
    init(f)
    ffi=f.emissions.loc[dict(scenario='medium-extension',specie='CO2 FFI')]; af=f.emissions.loc[dict(scenario='medium-extension',specie='CO2 AFOLU')]
    for i,tp in enumerate(f.timepoints):
        y=int(np.floor(float(tp)))
        if y in net: ffi[i,:]=net[y]; af[i,:]=0.0
    f.emissions.loc[dict(scenario='medium-extension',specie='CO2 FFI')]=ffi; f.emissions.loc[dict(scenario='medium-extension',specie='CO2 AFOLU')]=af
    f.run(progress=False); return f

def neutral_props(species,props):
    p=deepcopy(props)
    for s in species:
        if s in ('CO2 FFI','CO2 AFOLU','CO2'): continue
        if p[s]['type'] in ('ch4','n2o'):
            p[s].update(input_mode='concentration',greenhouse_gas=True,aerosol_chemistry_from_emissions=False,aerosol_chemistry_from_concentration=False)
        else:
            p[s].update(input_mode='forcing',greenhouse_gas=False,aerosol_chemistry_from_emissions=False,aerosol_chemistry_from_concentration=False)
    return p

def neutral(ref,net,end=2400):
    f,species,props=make(end,neutral_props); init(f)
    for s in ('CO2 FFI','CO2 AFOLU'):
        f.emissions.loc[dict(scenario='medium-extension',specie=s)]=np.asarray(ref.emissions.loc[dict(scenario='medium-extension',specie=s)]).copy()
    ffi=f.emissions.loc[dict(scenario='medium-extension',specie='CO2 FFI')]; af=f.emissions.loc[dict(scenario='medium-extension',specie='CO2 AFOLU')]
    for i,tp in enumerate(f.timepoints):
        y=int(np.floor(float(tp)))
        if y in net: ffi[i,:]=net[y]; af[i,:]=0.0
    f.emissions.loc[dict(scenario='medium-extension',specie='CO2 FFI')]=ffi; f.emissions.loc[dict(scenario='medium-extension',specie='CO2 AFOLU')]=af
    tbs=np.asarray(f.timebounds,float)
    for s in species:
        if s in ('CO2 FFI','CO2 AFOLU','CO2'): continue
        if props[s]['type'] in ('ch4','n2o'):
            src=np.asarray(ref.concentration.loc[dict(scenario='medium-extension',specie=s)]); arr=np.empty_like(src,float); b=np.asarray(f.species_configs['baseline_concentration'].loc[dict(specie=s)],float)
            for i,t in enumerate(tbs): arr[i,:]=src[i,:] if t<=2026 else b
            f.concentration.loc[dict(scenario='medium-extension',specie=s)]=arr
        else:
            src=np.asarray(ref.forcing.loc[dict(scenario='medium-extension',specie=s)]); arr=np.zeros_like(src,float)
            arr[tbs<=2026,:]=src[tbs<=2026,:]; f.forcing.loc[dict(scenario='medium-extension',specie=s)]=arr
    f.run(progress=False); return f

def co2(f): return np.asarray(f.concentration.loc[dict(scenario='medium-extension',specie='CO2')],float)
def temp(f): return np.asarray(f.temperature.loc[dict(scenario='medium-extension',layer=0)],float)
def stats(f,y):
    i=ix(f,y); c=co2(f)[i]; t=temp(f)[i]
    return {'c':c,'t':t,'cq':q(c),'tq':q(t),'bq':q(c-base),'f280':float(np.mean(c<=280)),'fbase':float(np.mean(c<=base))}

def attr(a,b,cdr,label):
    rows=[]; aa=co2(a); bb=co2(b)
    for i,t in enumerate(np.asarray(a.timebounds,float)):
        cy=sum(v for y,v in cdr.items() if y<=int(round(t))-1); d=bb[i]-aa[i]; fq=q(d*conv/cy) if cy>0 else [math.nan]*3; dq=q(d)
        rows.append([label,t,cy,*dq,*fq])
    return pd.DataFrame(rows,columns=['experiment','timebound_year','cumulative_cdr_gtco2','delta_co2_p05_ppm','delta_co2_p50_ppm','delta_co2_p95_ppm','fraction_p05','fraction_p50','fraction_p95'])

on,off,cdr=paths(); print('paired standard',flush=True); fon=std(on); foff=std(off)
a=attr(fon,foff,cdr,'medium-extension'); a.to_csv(OUT/'fair_paired_attribution.csv',index=False)
np.savez_compressed(OUT/'fair_paired_members.npz',years=np.asarray(fon.timebounds,float),config_ids=ids,co2_on=co2(fon),co2_off=co2(foff),temp_on=temp(fon),temp_off=temp(foff))
print('paired neutral non-CO2',flush=True); fzon=neutral(fon,on); fzoff=neutral(fon,off)
i26=ix(fon,2026); audit={'co2_maxabs':float(np.max(np.abs(co2(fon)[i26]-co2(fzon)[i26]))),'temp_maxabs':float(np.max(np.abs(temp(fon)[i26]-temp(fzon)[i26])))}
assert audit['co2_maxabs']<1e-6 and audit['temp_maxabs']<1e-6, audit
az=attr(fzon,fzoff,cdr,'neutral-future-nonco2'); az.to_csv(OUT/'fair_paired_attribution_neutral_nonco2.csv',index=False)
bg=[]
for y in [2026,2040,2100,2156,2184,2200,2300,2400]:
    s=stats(fon,y); z=stats(fzon,y); dz=q(z['c']-s['c']); bg.append([y,*s['cq'],*z['cq'],*dz,s['tq'][1],z['tq'][1]])
pd.DataFrame(bg,columns=['year','std_p05','std_p50','std_p95','neutral_p05','neutral_p50','neutral_p95','difference_p05','difference_p50','difference_p95','std_temp_p50','neutral_temp_p50']).to_csv(OUT/'fair_neutral_nonco2.csv',index=False)

print('inverse solve',flush=True); targets=[2200,2300,2400]; cache={}
def ev(r):
    k=round(float(r),10)
    if k not in cache:
        t=time.time(); p,_,_=paths(float(r)); f=std(p); cache[k]={y:stats(f,y) for y in targets}; print('rate',r,'sec',round(time.time()-t,1),flush=True)
    return cache[k]
def metric(r,y,kind):
    s=ev(r)[y]; return float(np.median(s['c'])-280) if kind=='absolute_280' else float(np.median(s['c']-base))
def solve(y,kind):
    lo=0.; flo=metric(lo,y,kind)
    if flo<=0:return 0.,'already_met',0.,0.
    hi=1.; fhi=metric(hi,y,kind)
    while fhi>0 and hi<512: hi*=2; fhi=metric(hi,y,kind)
    if fhi>0:return None,'not_bracketed',lo,hi
    for _ in range(14):
        mid=(lo+hi)/2
        if metric(mid,y,kind)>0:lo=mid
        else:hi=mid
    return hi,'solved',lo,hi
rows=[]; members=[]
for y in targets:
  for kind in ['absolute_280','member_relative_baseline']:
    r,status,lo,hi=solve(y,kind); row={'target_year':y,'criterion':kind,'status':status,'rate':r,'low':lo,'high':hi}
    if r is not None:
      s=ev(r)[y]; n=y-2184; row.update(extra_cdr_rate_gtco2_per_year=r,cumulative_extra_cdr_gtco2=r*n,total_post2183_cdr_rate_gtco2_per_year=LC+r,canonical_cdr_2026_2183_gtco2=CAN_CDR,historical_program_peak_cdr_gtco2_per_year=PEAK,exceeds_historical_program_peak=bool(LC+r>PEAK),co2_p05=s['cq'][0],co2_p50=s['cq'][1],co2_p95=s['cq'][2],co2_minus_baseline_p05=s['bq'][0],co2_minus_baseline_p50=s['bq'][1],co2_minus_baseline_p95=s['bq'][2],fraction_le_280=s['f280'],fraction_le_own_baseline=s['fbase'],temp_p05=s['tq'][0],temp_p50=s['tq'][1],temp_p95=s['tq'][2])
      for cid,c,t,b in zip(ids,s['c'],s['t'],base):members.append([y,kind,r,cid,b,c,c-b,t,c<=280,c<=b])
    rows.append(row)
pd.DataFrame(rows).to_csv(OUT/'fair_inverse_solve_summary.csv',index=False)
pd.DataFrame(members,columns=['target_year','criterion','extra_rate','config','baseline_co2','co2','co2_minus_baseline','temperature','le_280','le_own_baseline']).to_csv(OUT/'fair_inverse_solve_members.csv',index=False)
sel=a[a.timebound_year.isin([2040.,2100.,2156.,2184.,2200.,2300.,2400.])]; sel.to_csv(OUT/'fair_paired_attribution_selected.csv',index=False)
summary={'model':'FaIR 2.2.4','calibration':'fair-calibrate 1.4.1','configs':841,'canonical_cdr_gtco2':CAN_CDR,'peak_cdr_gtco2_per_year':PEAK,'gtco2_per_ppm':conv,'common_state_audit':audit,'attribution':'member-wise paired removal-off minus removal-on, then quantiles','inverse_control':'constant additional CDR from 2184; absolute-280 and member-relative-baseline criteria','inverse':rows,'hector_status':'SEPARATE_GITHUB_ACTION_JOB: see Hector paired science artifact for the same carbon pathway decomposition.'}
(OUT/'fair_science_experiment_summary.json').write_text(json.dumps(summary,indent=2))
with (OUT/'FAIR_RUN_REPORT.txt').open('w') as h:
    h.write('FaIR 2.2.4 science experiments\n'); h.write(json.dumps(summary,indent=2)); h.write('\n')
print(json.dumps(summary,indent=2),flush=True)
