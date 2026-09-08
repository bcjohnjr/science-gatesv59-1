#!/usr/bin/env python3
from pathlib import Path
import json
import pandas as pd
OUT=Path('.')
req=['hector_paired_attribution.csv','hector_removal_on_long.csv','hector_removal_off_long.csv','hector_science_summary.json']
miss=[x for x in req if not (OUT/x).exists()]
if miss: raise SystemExit(f'Missing Hector science outputs: {miss}')
s=json.loads((OUT/'hector_science_summary.json').read_text())
assert s['model']=='Hector' and s['version']=='3.5.0'
df=pd.read_csv(OUT/'hector_paired_attribution.csv')
assert {'co2_on_ppm','co2_off_ppm','delta_co2_ppm','cumulative_cdr_gtco2','apparent_response_fraction'} <= set(df.columns)
assert len(df)>=250
print('Hector paired-output verification passed.')
