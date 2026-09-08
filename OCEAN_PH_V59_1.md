# Ocean pH treatment — V59.1

V59.1 retains the FaIR-driven surface-ocean chemistry screen but narrows its interpretation.

Current fixed-T/S diagnostic:
- minimum pH: 8.0453 in 2033;
- endpoint pH: 8.1563;
- maximum OAE pH increment: 0.0018 in 2147;
- peak OAE alkalinity anomaly: 14.3 µmol/kg.

Publication-facing precision is limited to **two decimal places** because temperature and salinity are fixed in the compact carbonate solve.

Exact pH 8.10 / 8.15 / 8.17 crossing years remain diagnostic-only.

Modern carbonate-system calculations should use temperature- and salinity-dependent equilibria, e.g. PyCO2SYS:
https://gmd.copernicus.org/articles/15/15/2022/gmd-15-15-2022.html

Classic seawater measurements report a pH temperature coefficient of roughly 0.0114 pH units per °C:
https://doi.org/10.4319/lo.1969.14.5.0679

This temperature dependence is materially larger than the modeled OAE pH increment in V59.1, which is why four-decimal pH and exact threshold years are withheld from publication claims.
