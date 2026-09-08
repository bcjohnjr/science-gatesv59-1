# Hector / FaIR common-background reconciliation

The GitHub workload deliberately does **not** declare the Hector/FaIR divergence resolved merely because both models run.

The automated Hector job standardizes the carbon bookkeeping and creates a true removal-on/removal-off pair inside Hector: identical SSP2-4.5 non-CO2 background in both runs, explicit gross carbon input, and explicit DACCS removal. The FaIR job creates an analogous paired attribution and additionally runs a neutral-future-non-CO2 control from the same pre-divergence state.

After the first Actions run, compare:

1. FaIR paired standard background;
2. FaIR paired neutral-future-non-CO2 background;
3. Hector paired SSP2-4.5 background;
4. the archived Hector trajectory.

If the Hector/FaIR divergence remains after carbon-bookkeeping alignment, the next experiment is a **cross-model prescribed common non-CO2 forcing protocol**. That protocol should be implemented only after checking which Hector forcing inputs can be prescribed without inadvertently constraining CO2 forcing itself. Until that additional control is run, the cross-model common-background gate remains open.

This is intentional: the repository must not replace an unresolved scientific gate with an untested forcing hack.
