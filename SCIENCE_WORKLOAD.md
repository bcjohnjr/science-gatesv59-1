# Scientific workload — V59.1 external carbon-cycle gates

This workload is deliberately **flat**. All scripts and the trajectory input are stored in the repository root. No `science_workload/` or `data/` upload directory is used.

The repository remains **Planetary Restoration Model V59.1**. Running these experiments does not close any scientific gate until the outputs complete successfully and are inspected.

## Gate A — paired FaIR attribution

Runs all 841 constrained FaIR 2.2.4 / fair-calibrate 1.4.1 configurations twice from the same setup and non-CO2 background:

- removal on: canonical gross + permafrost + reversal − CDR;
- removal off: identical trajectory with anthropogenic CDR removed.

The atmospheric response is calculated configuration-by-configuration before p05/p50/p95 are formed.

## Gate B — common-state / non-CO2 control

FaIR reruns the pair with future non-CO2 forcing neutralized after the common 2026 state and asserts identical CO2 and temperature at the splice before accepting the experiment. Hector separately runs a removal-on/removal-off pair under one identical SSP2-4.5 background.

A surviving Hector/FaIR divergence still requires a cross-model prescribed common non-CO2 forcing protocol; this workload does not falsely mark that question resolved.

## Gate C — inverse FaIR solve

Additional constant CDR after 2183 is solved for target years 2200, 2300 and 2400 against two definitions:

- absolute atmospheric CO2 <= 280 ppm;
- median member-relative CO2 <= each configuration's preindustrial baseline.

The output reports required additional removal and the fraction of configurations meeting each target.

## Gate D — additional external validation

OSCAR, or an explicitly justified revision of that predeclared validation gate, remains separate and open.

## Flat output files

FaIR produces root-level files beginning with `fair_` plus `FAIR_RUN_REPORT.txt`. Hector produces root-level files beginning with `hector_`.

The official FaIR v2.2.4 source/calibration repository is cloned by GitHub Actions into `/tmp/FAIR-v2.2.4`; it is not added to this repository.

**Do not update manuscript headline values until the Action completes successfully and the output artifacts have been inspected.**
