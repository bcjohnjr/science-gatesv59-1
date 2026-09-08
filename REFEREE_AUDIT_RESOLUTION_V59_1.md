# Referee audit resolution — V59.1

V59.1 is a maintenance release. It adds no new planetary subsystem.

## Packaging and reproducibility

- Removed all `__pycache__` directories and `.pyc` files.
- `SHA256SUMS.txt` is regenerated from distributable source/data/document artifacts only.
- Historical V56/V57/V58 root duplicates were removed from the current root.
- V59.0 and V58 release material is retained under `previous_version/` for audit.
- The stale JSON `submission_status` string is replaced with the current V59.1 gate.

## Sink-response presentation

The early apparent atmospheric-response ratio can exceed 1 because the numerator is total atmospheric stock decline while the denominator counts only anthropogenic net removal after the first net-negative year. Natural land/ocean uptake from the prior elevated-CO2 state initially continues in parallel. The ratio is therefore not a bounded physical efficiency.

The archived p05/p50/p95 concentration curves imply an endpoint apparent-response envelope of approximately
**56.8%–58.7%**.
This is explicitly labelled an aggregate percentile-curve envelope, not configuration-level response quantiles. A proper response-fraction uncertainty distribution still requires a FaIR rerun that archives each configuration trajectory.

## Sea level

The paper-facing result is now restricted to the archived FaIR horizon:

- central additional GMSL since 2026: **30.9 cm in 2100**;
- **65.9 cm in 2300**;
- **70.5 cm in 2400**;
- still rising at **0.281 mm/yr in 2400**.

The millennial post-2400 dates are removed from the headline and manuscript scope and retained only inside an explicitly paper-excluded diagnostic subtree.

AR6 calibration screen:
- the V59 three-case screen is broadly compatible with low-emissions AR6 at 2100;
- all three cases lie inside the very broad AR6 SSP1-2.6 assessed 2300 range of 0.3–3.1 m;
- but the V59 high case reaches only about 1.33 m relative to 1995–2014 by 2300, so the simple emulator materially under-disperses long-run ice-sheet uncertainty.

Therefore low/central/high must not be described as calibrated p05/p50/p95 sea-level uncertainty.

## Ocean pH / OAE

OAE's maximum modeled surface-pH increment is **0.0018 in 2147**, at a peak alkalinity anomaly of **14.3 µmol/kg**. That peak increment is about **1.6%** of the modeled minimum-to-endpoint pH recovery. The almost-zero OAE increment near 2400 is no longer surfaced as the OAE headline.

Because the inherited carbonate calculation fixes temperature and salinity, V59.1:
- limits publication-facing pH to **two decimals**;
- withholds exact 8.10/8.15/8.17 threshold-crossing years from publication headlines;
- keeps those exact years only as diagnostics;
- requires temperature-coupled CO2SYS/PyCO2SYS before stronger ocean-chemistry claims.

## Scope freeze

No V60/new module should be created before the external carbon-cycle critical path is completed.
