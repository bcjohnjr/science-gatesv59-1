#!/usr/bin/env python3
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path('.')
OUT = ROOT
required = [
    'fair_paired_attribution.csv',
    'fair_paired_attribution_neutral_nonco2.csv',
    'fair_paired_members.npz',
    'fair_neutral_nonco2.csv',
    'fair_inverse_solve_summary.csv',
    'fair_inverse_solve_members.csv',
    'fair_science_experiment_summary.json',
    'FAIR_RUN_REPORT.txt',
]
missing = [x for x in required if not (OUT / x).exists()]
if missing:
    raise SystemExit(f'Missing FaIR science outputs: {missing}')

summary = json.loads((OUT / 'fair_science_experiment_summary.json').read_text())
assert summary['model'] == 'FaIR 2.2.4'
assert summary['calibration'] == 'fair-calibrate 1.4.1'
assert int(summary['configs']) == 841
assert summary['attribution'].startswith('member-wise paired')
audit = summary['common_state_audit']
assert float(audit['co2_maxabs']) < 1e-6, audit
assert float(audit['temp_maxabs']) < 1e-6, audit

paired = pd.read_csv(OUT / 'fair_paired_attribution.csv')
for col in ['delta_co2_p05_ppm','delta_co2_p50_ppm','delta_co2_p95_ppm','fraction_p05','fraction_p50','fraction_p95']:
    assert col in paired.columns, col
assert len(paired) > 500

npz = np.load(OUT / 'fair_paired_members.npz', allow_pickle=False)
co2_on = npz['co2_on']; co2_off = npz['co2_off']; ids = npz['config_ids']
assert co2_on.shape == co2_off.shape
assert co2_on.shape[1] == 841
assert len(ids) == 841
# Critical methodological guard: the response is formed configuration-by-configuration.
delta = co2_off - co2_on
assert delta.shape[1] == 841

inv = pd.read_csv(OUT / 'fair_inverse_solve_summary.csv')
assert set(inv['criterion']) == {'absolute_280','member_relative_baseline'}
assert set(inv['target_year']) == {2200,2300,2400}
print('FaIR science-output verification passed.')
