# Planetary Restoration Model V59.1

**Scope-freeze maintenance release. No new planetary subsystem is added.**

## Current physical result

The current financed pathway does not return the archived external carbon-cycle models to 280 ppm within their modeled horizons. The main scientific task is now to quantify the state-dependent loss of atmospheric removal effectiveness and solve the inverse problem: what additional removal trajectory is required for a chosen CO2 target under the calibrated external models?

The canonical FaIR median apparent atmospheric-response fraction is **58.1%** at the end of the financed 2026–2183 pathway. The archived concentration percentile curves imply an aggregate endpoint envelope of approximately **56.8%–58.7%**, but this is not a substitute for configuration-level uncertainty.

Early values above 100% do not mean removal is more than perfectly efficient: natural land and ocean sinks are still drawing down CO2 in parallel with anthropogenic net removal during the early transient.

## Sea-level result kept in main-paper scope

The simple sea-level emulator is useful for one limited point: **sea-level rise persists long after surface warming peaks and even after more than a century of net-negative CO2**.

Central screening output, additional global-mean sea level relative to 2026:
- 2100: **0.309 m**
- 2300: **0.659 m**
- 2400: **0.705 m**
- 2400 rate: **0.281 mm/yr**

The post-2400 peak/return/restoration dates from V59.0 are excluded from manuscript scope. The simple three-case emulator does not span the AR6 upper 2300 uncertainty range and must not be presented as a calibrated sea-level uncertainty distribution.

## Ocean pH retained, but narrowed

The FaIR-driven fixed-T/S surface-ocean screen remains in the package, but publication precision is now limited to two decimals:
- modeled minimum: **8.05**
- endpoint near the FaIR 2400 horizon: **8.16**

OAE's maximum modeled pH increment is only **0.0018 in 2147**, so most modeled pH recovery is driven by atmospheric CO2 decline rather than the current OAE surface-retention parameterization.

Exact pH threshold years remain diagnostic only until temperature-coupled CO2SYS/PyCO2SYS is run.

## Submission gate

**NOT SUBMISSION READY.** Scope is frozen. Remaining critical work:
1. common-state / splice-correct FaIR restart;
2. zero-background-non-CO2 FaIR experiment;
3. inverse FaIR target solve;
4. OSCAR or an explicit justified revision to that predeclared validation gate.

See `NOVELTY_BENCHMARK_V59_1.md` and `MANUSCRIPT_SCOPE_FREEZE_V59_1.md`.
