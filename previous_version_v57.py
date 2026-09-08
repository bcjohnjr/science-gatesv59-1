#!/usr/bin/env python3
"""Planetary Restoration Model V57 — attribution and seaweed-accounting correction.

V57 acts on the V56 referee audit without hiding the adverse result.  It keeps
archived FaIR 2.2.4 and Hector 3.5.0 as the external carbon-cycle evidence and
adds a formal attribution layer that can be computed from the archived outputs.
It also removes live superseded V55 derived values from the current JSON,
clarifies FaIR/internal time indexing, separates seaweed area-vs-yield
constructions, restores cultivation/farmgate economics, closes the ash mass
balance as a screened recovery stream, and reports seaweed food as digestible
protein rather than converting an invalid gross-energy number into hunger claims.

Two external attribution experiments remain execution-open in this build:
(1) a FaIR CO2-only / zero-background-non-CO2 experiment and
(2) a FaIR inverse removal-schedule solution.  The package includes a protocol
and prepared inputs, but this runtime cannot install the official FaIR package or
its calibration repository because outbound package/repository access is blocked.
No unexecuted experiment is presented as a result.
"""
from __future__ import annotations

import argparse
import copy
import csv
import importlib.util
import json
import math
import sys
import zipfile
from pathlib import Path
from typing import Dict, List, Mapping, Sequence

HERE = Path(__file__).resolve().parent
MODEL_VERSION = "57.0"
RELEASE_LABEL = "Planetary Restoration Model Version 57.0 — Attribution + Seaweed Accounting"
RELEASE_STATUS = "REFRAMED_EXTERNAL_RESULT_ATTRIBUTION_PARTIAL_NOT_SUBMISSION_READY_NONCO2_INVERSION_OSCAR_OPEN"

# Observational anchor already used in V53.1 as START_CO2_PPM.
# NOAA global monthly mean, May 2026.
OBSERVED_2026_ANCHOR_PPM = 428.73
OBSERVED_2026_SOURCE = "https://www.gml.noaa.gov/ccgg/trends/global.html"

# Seaweed engineering/economic screens.
TARGET_PRODUCTIVE_YIELD_T_DRY_HA_YR = 25.0
FARMGATE_COST_LOW_USD_T_DRY = 100.0
FARMGATE_COST_CENTRAL_USD_T_DRY = 275.0
FARMGATE_COST_STRESS_USD_T_DRY = 880.0
FARMGATE_COST_SOURCE_2025 = "https://doi.org/10.1111/jwas.70017"
FARMGATE_COST_SOURCE_GLOBAL = "https://doi.org/10.1038/s41477-022-01305-9"

# Ash handling is an explicit engineering SCREEN, not a literature-derived constant.
ASH_RECOVERY_FRACTION_LOW = 0.50
ASH_RECOVERY_FRACTION_CENTRAL = 0.80
ASH_RECOVERY_FRACTION_HIGH = 0.95
ASH_HANDLING_KWH_T_LOW = 10.0
ASH_HANDLING_KWH_T_CENTRAL = 25.0
ASH_HANDLING_KWH_T_HIGH = 50.0
ASH_FATE_SOURCE_HTL = "https://doi.org/10.1016/j.biortech.2011.01.031"
ASH_FATE_SOURCE_MINERALS = "https://pmc.ncbi.nlm.nih.gov/articles/PMC6266857/"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


v56 = _load_module("prm_v56_dependency", HERE / "previous_version_v56.py")


def _zip_csv_rows(path: Path, member: str) -> List[Dict[str, str]]:
    with zipfile.ZipFile(path) as z:
        return list(csv.DictReader(z.read(member).decode("utf-8").splitlines()))


def _nearest(rows: Sequence[Mapping], year: int, key: str = "year") -> Mapping:
    return min(rows, key=lambda r: abs(float(r[key]) - year))


def _trajectory_rows() -> List[Dict[str, float]]:
    rows=[]
    with (HERE / "data" / "external_validation_net_co2_trajectory.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({k: (int(v) if k=="year" else float(v)) for k,v in r.items()})
    return rows


def _fair_timeseries() -> List[Dict[str, float]]:
    rows=[]
    for r in _zip_csv_rows(HERE / "external_validation_results" / "fair-v2.2.4-results.zip", "fair_v2_2_4_timeseries.csv"):
        rows.append({k: float(v) for k,v in r.items()})
    return rows


def _hector_timeseries() -> List[Dict[str, float]]:
    with zipfile.ZipFile(HERE / "external_validation_results" / "hector-v3.5.0-results.zip") as z:
        member=next(n for n in z.namelist() if n.lower().endswith(".csv") and "time" in n.lower())
        text=z.read(member).decode("utf-8")
    out=[]
    for r in csv.DictReader(text.splitlines()):
        if r.get("variable") == "CO2_concentration":
            out.append({"year":int(float(r["year"])),"co2_ppm":float(r["value"])})
    return out


def attribution_v57(base: Dict) -> Dict:
    fair=_fair_timeseries()
    hector=_hector_timeseries()
    traj=_trajectory_rows()
    fair_by={int(round(r["year"])):r for r in fair}
    hector_by={int(r["year"]):r["co2_ppm"] for r in hector}
    internal_by={int(r["year"]):float(r["joos_diagnostic_co2_ppm"]) for r in traj}

    # Important indexing correction:
    # internal row Y is AFTER applying annual flux Y; FaIR emissions at Y+0.5
    # change concentration from timebound Y to Y+1.  Therefore internal 2155
    # should be compared to FaIR timebound 2156, not FaIR timebound 2155.
    fair_start=float(fair_by[2026]["co2_p50_ppm"])
    fair_after_2026=float(fair_by[2027]["co2_p50_ppm"])
    internal_initial=OBSERVED_2026_ANCHOR_PPM
    internal_after_2026=float(internal_by[2026])
    fair_after_internal_2155=float(fair_by[2156]["co2_p50_ppm"])
    internal_after_2155=float(internal_by[2155])

    prior_misaligned_gap = float(base["external_validation_v56"]["attribution_diagnostics"]["initial_condition_offset_internal_minus_fair_p50_ppm"])
    fair_historical_offset = internal_initial - fair_start
    after_2026_gap = internal_after_2026 - fair_after_2026
    response_gap_2155 = (fair_after_internal_2155 - fair_start) - (internal_after_2155 - internal_initial)
    aligned_fair_2156 = fair_after_internal_2155 + fair_historical_offset

    # No-extension attribution is causal from the archived run: future values
    # after the final supplied emissions year cannot alter prior FaIR states.
    # The 2183 annual flux is applied over 2183->2184, so 2184 is the post-2183 state.
    fair_pre_extension_timebound_2183=float(fair_by[2183]["co2_p50_ppm"])
    fair_after_last_canonical_flux_2184=float(fair_by[2184]["co2_p50_ppm"])

    # Exact raw Hector-vs-internal crossing under the archived time labels.
    cross=None
    prev=None
    for y in sorted(set(internal_by).intersection(hector_by)):
        d=hector_by[y]-internal_by[y]
        if prev is not None and d*prev[1] < 0:
            cross={"between_years":[prev[0],y],"difference_ppm_before":prev[1],"difference_ppm_after":d}
            break
        prev=(y,d)

    # Extend the canonical net-CO2 schedule exactly as the archived FaIR benchmark did.
    net={int(r["year"]):float(r["net_co2_gtco2"]) for r in traj}
    last=net[max(net)]
    for y in range(max(net)+1,2400):
        net[y]=last

    # Apparent atmospheric response = atmospheric mass decrease / cumulative
    # net negative emissions over each interval.  This is a pathwise diagnostic,
    # not a local derivative and not a universal carbon-removal efficiency.
    intervals=[]
    for a,b in [(2039,2100),(2101,2155),(2156,2183),(2184,2300),(2301,2399)]:
        removal=-sum(net[y] for y in range(a,b+1))
        ppm_drop=float(fair_by[a]["co2_p50_ppm"])-float(fair_by[b+1]["co2_p50_ppm"])
        atmospheric_gtco2=ppm_drop*7.77
        intervals.append({
            "emissions_year_start":a,"emissions_year_end":b,
            "cumulative_net_removal_gtco2":removal,
            "fair_p50_ppm_drop":ppm_drop,
            "atmospheric_mass_decrease_gtco2_equivalent":atmospheric_gtco2,
            "pathwise_apparent_atmospheric_response_fraction":atmospheric_gtco2/removal if removal else None,
        })

    late=intervals[-1]
    gap2400=float(fair_by[2400]["co2_p50_ppm"])-280.0
    atm_gap2400=gap2400*7.77
    local_linear_extra=atm_gap2400/late["pathwise_apparent_atmospheric_response_fraction"]

    return {
        "classification":"ATTRIBUTION_STUDY_PARTIAL_ARCHIVED_OUTPUT_DIAGNOSTICS_PLUS_TWO_OPEN_OFFICIAL_FAIR_EXPERIMENTS",
        "primary_scientific_result":"Under the archived removal pathway, state-dependent carbon-sink response becomes a binding physical constraint: FaIR and Hector do not reproduce the internal 280-ppm return, and the divergence grows after deep drawdown rather than behaving as a constant concentration bias.",
        "initial_condition_and_time_index":{
            "status":"CLOSED_AS_DIAGNOSTIC_NOT_OFFICIAL_FAIR_RESTART",
            "observed_anchor_ppm":OBSERVED_2026_ANCHOR_PPM,
            "observed_anchor_date_basis":"NOAA global monthly mean, May 2026",
            "observed_anchor_source":OBSERVED_2026_SOURCE,
            "internal_initial_before_2026_flux_ppm":internal_initial,
            "internal_row_2026_after_2026_flux_ppm":internal_after_2026,
            "fair_timebound_2026_before_2026_override_flux_p50_ppm":fair_start,
            "fair_timebound_2027_after_2026_override_flux_p50_ppm":fair_after_2026,
            "prior_v56_misaligned_internal_row2026_minus_fair_timebound2026_gap_ppm":prior_misaligned_gap,
            "correct_fair_historical_p50_offset_vs_noaa_start_ppm":fair_historical_offset,
            "post_2026_same_step_internal_minus_fair_gap_ppm":after_2026_gap,
            "matched_step_fair_2156_minus_internal_2155_raw_gap_ppm":fair_after_internal_2155-internal_after_2155,
            "matched_start_response_gap_by_internal_2155_ppm":response_gap_2155,
            "start_aligned_fair_p50_at_matched_2155_step_ppm":aligned_fair_2156,
            "interpretation":"The earlier 6.23-ppm 'initial-condition offset' compared different time conventions. Correcting the indexing and removing the constant starting bias does not explain the disagreement; it increases the response-only gap to about 35.9 ppm at the internal 2155 milestone.",
        },
        "no_extension_test":{
            "status":"CLOSED_CAUSALLY_FROM_ARCHIVED_RUN",
            "canonical_last_input_year":2183,
            "fair_p50_timebound_2183_ppm":fair_pre_extension_timebound_2183,
            "fair_p50_after_2183_flux_timebound_2184_ppm":fair_after_last_canonical_flux_2184,
            "interpretation":"A future constant-flux extension cannot affect FaIR states before it begins. Therefore a run terminated immediately after the 2183 canonical flux would still be about 311.4 ppm p50. The extension explains post-2183 evolution, not the failure of the canonical programme to approach 280 by its own endpoint.",
        },
        "hector_transient_to_reversal_signal":{
            "raw_label_crossing":cross,
            "hector_co2_2155_ppm":hector_by.get(2155),
            "hector_co2_2183_ppm":hector_by.get(2183),
            "hector_co2_2190_ppm":hector_by.get(2190),
            "interpretation":"Hector is below the internal Joos trajectory until roughly 2123-2124 under the archived labels, then crosses above it and rebounds strongly after its mid-century minimum. This is inconsistent with a simple constant-bias explanation and is qualitatively consistent with state-dependent sink reversal/equilibration.",
        },
        "pathwise_marginal_response":{
            "status":"ARCHIVED_FAIR_DIAGNOSTIC_NOT_INVERSE_SOLUTION",
            "intervals":intervals,
            "fair_p50_2400_ppm":float(fair_by[2400]["co2_p50_ppm"]),
            "remaining_gap_to_280_ppm_2400":gap2400,
            "remaining_atmospheric_mass_equivalent_gtco2":atm_gap2400,
            "late_interval_apparent_response_fraction":late["pathwise_apparent_atmospheric_response_fraction"],
            "local_linear_extra_net_removal_gtco2_if_late_response_fraction_held_constant":local_linear_extra,
            "caution":"The local-linear extra-removal number is NOT a FaIR inversion and must not be used as a restoration requirement. The response fraction is state- and pathway-dependent; an official iterative FaIR inversion remains required.",
        },
        "open_experiments":{
            "fair_zero_background_nonco2":{
                "status":"OPEN_OFFICIAL_FAIR_EXECUTION_REQUIRED",
                "purpose":"Separate carbon-sink response driven by the deep CO2 drawdown from sink weakening mediated by background non-CO2 warming.",
                "reason_not_executed_here":"Official FaIR 2.2.4/calibration files cannot be installed or cloned in this runtime because outbound package/repository access is blocked.",
            },
            "fair_inverse_removal_schedule":{
                "status":"OPEN_OFFICIAL_FAIR_EXECUTION_REQUIRED",
                "purpose":"Solve for the additional removal schedule required for the calibrated FaIR ensemble to reach a specified atmospheric target, rather than extrapolating from the internal Joos model.",
                "reason_not_executed_here":"Same blocked official FaIR dependency; a prepared protocol is included under external_validation_workflow/V57_ATTRIBUTION_PROTOCOL.md.",
            },
        },
    }


def _grid_harvest_metrics(biomass_gt_dry_yr: float) -> Dict:
    # The V55 physical v19 reconstruction remains the harvester basis.
    return v56.v55.seaweed_branch.grid_harvester(biomass_gt_dry_yr)


def seaweed_v57(base: Dict) -> Dict:
    sw56=base["seaweed_v56"]
    v56_primary=next(r for r in sw56["scenarios"] if r["scenario"]=="nutrient_closed_central")
    biomass=float(v56_primary["total_dry_biomass_gt_yr"])
    full_area_km2=586000.0
    productive_area_km2=biomass*1e9/TARGET_PRODUCTIVE_YIELD_T_DRY_HA_YR/100.0
    diluted_yield=biomass*1e9/(full_area_km2*100.0)
    area_multiplier=full_area_km2/productive_area_km2
    grid=_grid_harvest_metrics(biomass)
    grid_cost_t=float(grid["central_harvest_cost_usd_dry_t"])

    constructions=[
        {
            "construction":"yield_maintained_area_limited_PRIMARY",
            "status":"V57_PRIMARY_ENGINEERING_CONSTRUCTION",
            "biomass_gt_dry_yr":biomass,
            "farm_area_km2":productive_area_km2,
            "dry_yield_t_ha_yr":TARGET_PRODUCTIVE_YIELD_T_DRY_HA_YR,
            "area_fraction_of_586k_full_potential":productive_area_km2/full_area_km2,
            "harvest_cost_scaling_factor_vs_v19_mass_based":1.0,
            "reason":"If nutrients are binding, prioritize the most productive sites and reduce deployed area rather than paying to farm the full ocean footprint at one-sixth the target yield.",
        },
        {
            "construction":"full_area_nutrient_diluted_SENSITIVITY",
            "status":"ALTERNATIVE_ENGINEERING_SENSITIVITY",
            "biomass_gt_dry_yr":biomass,
            "farm_area_km2":full_area_km2,
            "dry_yield_t_ha_yr":diluted_yield,
            "area_fraction_of_586k_full_potential":1.0,
            "harvest_cost_scaling_factor_vs_v19_mass_based":area_multiplier,
            "reason":"Same nutrient-supported biomass spread across the full geometric footprint. The area-per-tonne multiplier is reported as a conservative harvest/transit sensitivity, not a validated cost law.",
        },
        {
            "construction":"managed_nutrient_full_potential_HIGH",
            "status":"HIGH_ENGINEERING_SCENARIO",
            "biomass_gt_dry_yr":1.465,
            "farm_area_km2":full_area_km2,
            "dry_yield_t_ha_yr":25.0,
            "area_fraction_of_586k_full_potential":1.0,
            "harvest_cost_scaling_factor_vs_v19_mass_based":1.0,
            "reason":"Requires demonstrated additional natural/recycled/supplemental nutrient flux and is not the primary nutrient-closed case.",
        },
    ]

    econ=[]
    for label,total_cost in [
        ("favorable_large_scale",FARMGATE_COST_LOW_USD_T_DRY),
        ("central_large_scale",FARMGATE_COST_CENTRAL_USD_T_DRY),
        ("global_low_cost_area_stress",FARMGATE_COST_STRESS_USD_T_DRY),
    ]:
        nonharvest=max(0.0,total_cost-grid_cost_t)
        econ.append({
            "case":label,
            "farmgate_total_usd_per_dry_t":total_cost,
            "grid_harvest_usd_per_dry_t_v19":grid_cost_t,
            "derived_nonharvest_cultivation_support_usd_per_dry_t":nonharvest,
            "annual_farmgate_cost_usd_bn_primary":biomass*1e9*total_cost/1e9,
            "annual_grid_harvest_cost_usd_bn_primary":biomass*1e9*grid_cost_t/1e9,
            "annual_nonharvest_cultivation_support_usd_bn_primary":biomass*1e9*nonharvest/1e9,
            "source":"Stekoll et al. 2025 for ~$100 favorable and ~$250-300 centered 1000-ha farmgate estimates; Bach et al. Nature Plants global cost context for ~$880 median in modeled lowest-cost ocean area.",
            "source_urls":[FARMGATE_COST_SOURCE_2025,FARMGATE_COST_SOURCE_GLOBAL],
            "caution":"The non-harvest line is a derived residual for model completeness, not a published decomposition. Published farmgate costs include farm operations and harvesting assumptions that differ from the Grid Harvester design.",
        })

    # Explicit primary ash fate.
    food_share=0.05; fuel_share=0.80
    fuel_feed_mt=biomass*fuel_share*1000.0
    ash_fraction=0.25
    ash_mt=fuel_feed_mt*ash_fraction
    ash_recovery=[]
    for label,frac,kwh_t in [
        ("low_recovery",ASH_RECOVERY_FRACTION_LOW,ASH_HANDLING_KWH_T_LOW),
        ("central_recovery",ASH_RECOVERY_FRACTION_CENTRAL,ASH_HANDLING_KWH_T_CENTRAL),
        ("high_recovery",ASH_RECOVERY_FRACTION_HIGH,ASH_HANDLING_KWH_T_HIGH),
    ]:
        ash_recovery.append({
            "case":label,
            "ash_entering_fuel_process_mt_yr":ash_mt,
            "mineral_recovery_target_fraction":frac,
            "candidate_recovered_mineral_stream_mt_yr":ash_mt*frac,
            "controlled_residual_mt_yr":ash_mt*(1-frac),
            "ash_handling_energy_kwh_t_ash":kwh_t,
            "ash_handling_electricity_twh_yr":ash_mt*1e6*kwh_t/1e9,
            "credit_to_existing_nutrient_loop_mt_yr":0.0,
            "credit_rule":"ZERO until species/process-specific K/P/Ca/Mg/Na/iodine partition, contaminant limits and recovery efficiencies are measured. This prevents double counting.",
        })

    # Propagate ash sensitivity into fuel output for the primary biomass.
    ash_sens=[]
    for ash in [0.20,0.25,0.35]:
        fuel_feed_gt=biomass*fuel_share
        ash_free_gt=fuel_feed_gt*(1-ash)
        finished_mt=ash_free_gt*1000.0*0.17
        fuel_twh=finished_mt*1e9*43.0/3.6e9
        ash_sens.append({
            "ash_fraction":ash,
            "ash_mt_yr":fuel_feed_gt*1000.0*ash,
            "finished_fuel_mt_yr":finished_mt,
            "finished_fuel_energy_twh_yr":fuel_twh,
        })

    # Protein-first human nutrition reporting.
    food_mt=biomass*food_share*1000.0
    gross_protein_mt=food_mt*0.10
    digestible_protein_mt=gross_protein_mt*0.70
    protein_50_req_kg_yr=0.050*365.0
    protein_65_req_kg_yr=0.065*365.0
    coverage_50=digestible_protein_mt*1e9/protein_50_req_kg_yr/1e6
    coverage_65=digestible_protein_mt*1e9/protein_65_req_kg_yr/1e6
    delivered_fraction=0.85
    nutrition={
        "food_dry_mt_yr_primary":food_mt,
        "gross_protein_mt_yr":gross_protein_mt,
        "digestible_protein_mt_yr_screen":digestible_protein_mt,
        "full_50g_day_digestible_protein_equivalent_million_people_gross_production":coverage_50,
        "full_65g_day_digestible_protein_equivalent_million_people_gross_production":coverage_65,
        "full_50g_day_digestible_protein_equivalent_million_people_after_85pct_delivery":coverage_50*delivered_fraction,
        "full_65g_day_digestible_protein_equivalent_million_people_after_85pct_delivery":coverage_65*delivered_fraction,
        "calorie_gap_headline_removed":True,
        "legacy_2000_kcal_kg_removed_from_current_nutrition_metrics":True,
        "publication_rule":"Report digestible protein and micronutrient potential. Do not convert the legacy 2,000-kcal/kg gross-energy screen into people-fed or hunger-ending claims without species-specific human metabolizable-energy evidence.",
    }

    return {
        "classification":"AREA_YIELD_EXPLICIT_WITH_FARMGATE_ECONOMICS_ASH_FATE_AND_PROTEIN_FIRST_NUTRITION",
        "primary_biomass_gt_dry_yr":biomass,
        "primary_engineering_construction":"yield_maintained_area_limited_PRIMARY",
        "engineering_constructions":constructions,
        "grid_harvester_primary":grid,
        "farmgate_economics":econ,
        "farmgate_source_note":"2025 large-scale Gulf of Alaska TEA reports costs centered around $250-$300/dry t and around $100/dry t under favorable close-to-base/high-yield conditions. Global modeling has much wider costs; ~$880/dry t is used only as a stress/context screen.",
        "ash_fate_primary":{
            "process_note":"HTL process energy remains scaled to total processed feedstock because inorganic material still has to be pumped/heated through the process. Finished-fuel yield is on ash-free dry organics. Ash handling electricity is now explicit and additive.",
            "literature_fate":"Macroalgae HTL studies find much K/Na in aqueous products and Ca/Mg concentrated in solid residue; these streams are candidates for mineral/nutrient recovery.",
            "source_urls":[ASH_FATE_SOURCE_HTL,ASH_FATE_SOURCE_MINERALS],
            "recovery_scenarios":ash_recovery,
            "ash_fraction_fuel_sensitivity":ash_sens,
        },
        "human_nutrition_primary":nutrition,
        "legacy_v56_scenario_reference":{
            "status":"SUPERSEDED_BY_V57_ENGINEERING_CONSTRUCTION",
            "note":"V56 nutrient-closed biomass quantity is retained, but its full-586,000-km2 area convention and calorie-gap metrics are superseded.",
        },
    }


def fisheries_v57(base: Dict, sw57: Dict) -> Dict:
    fish=copy.deepcopy(base["fisheries_v56"])
    primary=next(x for x in sw57["engineering_constructions"] if x["construction"]=="yield_maintained_area_limited_PRIMARY")
    fish["seaweed_coupling"]={
        "primary_nutrient_closed_farm_habitat_footprint_km2":primary["farm_area_km2"],
        "managed_full_high_scenario_footprint_km2":586000.0,
        "coculture_is_counted_as_wild_fish_recovery":False,
        "rule":"Wild-stock recovery remains literature-bounded and separate. Seaweed habitat/co-culture is an implementation co-benefit, not a wild-stock recovery credit.",
    }
    fish["classification"]="V57_LITERATURE_BOUNDED_FISHERIES_WITH_SCENARIO_SPECIFIC_SEAWEED_FOOTPRINTS"
    return fish


def legacy_architecture_reference(base: Dict) -> Dict:
    old=base["v55_integrated_architecture"]
    return {
        "status":"HISTORICAL_ARCHITECTURE_ONLY_SUPERSEDED_DERIVED_VALUES_OMITTED",
        "superseded_by":"V57",
        "do_not_use_for_current_headlines":True,
        "source":"previous_version_v56.py -> previous_version_v55.py and archived V56 JSON",
        "active_recovered_modules":old.get("active_recovered_modules"),
        "lineage_register":old.get("lineage_register"),
        "merge_decisions":old.get("merge_decisions"),
        "energy_reconciliation":old.get("energy_reconciliation"),
        "omitted_from_current_json":[
            "v53_1_core","v53_1_core_validation","integrated_seaweed","historical_seaweed_reference",
            "current_resource_screens","food_logistics","hunger_and_population","integrated_outcomes","external_validation_status"
        ],
        "reason":"These blocks carry V55-derived 2155/2153/2151 climate dates, 1.465-Gt seaweed outputs and legacy calorie/population values that V56/V57 explicitly supersede. They remain recoverable in the archived previous-version files, not live in the V57 result tree.",
    }


def headline_v57(base: Dict, attr: Dict, sw: Dict) -> Dict:
    fair=base["external_validation_v56"]["fair"]
    hector=base["external_validation_v56"]["hector"]
    primary_con=next(x for x in sw["engineering_constructions"] if x["construction"]=="yield_maintained_area_limited_PRIMARY")
    central_econ=next(x for x in sw["farmgate_economics"] if x["case"]=="central_large_scale")
    central_ash=next(x for x in sw["ash_fate_primary"]["recovery_scenarios"] if x["case"]=="central_recovery")
    nut=sw["human_nutrition_primary"]
    return {
        "paper_result":"Current financed removal pathway does not return the archived external carbon-cycle models to 280 ppm; state-dependent sink reversal/equilibration is the binding physical result to explain and design around.",
        "externally_validated_return_year":None,
        "fair_returning_configurations":fair["returning_configurations"],
        "fair_total_configurations":fair["configurations"],
        "fair_p50_co2_ppm_2400":fair["co2_p50_ppm_2400"],
        "hector_minimum_co2_ppm":hector["minimum_co2_ppm"],
        "hector_minimum_year":hector["minimum_co2_year"],
        "time_index_corrected_response_gap_ppm_at_internal_2155_milestone":attr["initial_condition_and_time_index"]["matched_start_response_gap_by_internal_2155_ppm"],
        "fair_p50_after_canonical_2183_flux_ppm":attr["no_extension_test"]["fair_p50_after_2183_flux_timebound_2184_ppm"],
        "late_pathwise_apparent_atmospheric_response_fraction":attr["pathwise_marginal_response"]["late_interval_apparent_response_fraction"],
        "primary_seaweed_biomass_gt_dry_yr":sw["primary_biomass_gt_dry_yr"],
        "primary_seaweed_area_km2":primary_con["farm_area_km2"],
        "primary_seaweed_target_yield_t_dry_ha_yr":primary_con["dry_yield_t_ha_yr"],
        "primary_seaweed_central_farmgate_cost_usd_bn_yr":central_econ["annual_farmgate_cost_usd_bn_primary"],
        "primary_seaweed_ash_mt_yr":central_ash["ash_entering_fuel_process_mt_yr"],
        "primary_seaweed_digestible_protein_mt_yr":nut["digestible_protein_mt_yr_screen"],
        "protein_coverage_million_people_at_50g_day_gross":nut["full_50g_day_digestible_protein_equivalent_million_people_gross_production"],
        "protein_coverage_million_people_at_50g_day_after_delivery":nut["full_50g_day_digestible_protein_equivalent_million_people_after_85pct_delivery"],
        "working_manuscript_title":"Financing planetary restoration under state-dependent carbon-sink reversal",
        "submission_status":"NOT SUBMISSION READY: archived non-return is now the central result, but official FaIR non-CO2 attribution, FaIR inversion and the original OSCAR gate remain open.",
    }


def run_v57() -> Dict:
    base=v56.run_v56()
    attr=attribution_v57(base)
    sw=seaweed_v57(base)
    fish=fisheries_v57(base,sw)
    return {
        "model_version":MODEL_VERSION,
        "release_label":RELEASE_LABEL,
        "release_status":RELEASE_STATUS,
        "classification":"EXTERNAL_RESULT_REFRAMED_WITH_PARTIAL_ATTRIBUTION_AND_CLOSED_SEAWEED_ACCOUNTING",
        "headline":headline_v57(base,attr,sw),
        "external_validation":base["external_validation_v56"],
        "attribution_v57":attr,
        "v53_1_full_core":base["v53_1_full_core"],
        "legacy_architecture_reference":legacy_architecture_reference(base),
        "seaweed_v57":sw,
        "fisheries_v57":fish,
        "restored_human_system_screens":base["restored_human_system_screens"],
        "accounting_rules":{
            "joos_role":"DIAGNOSTIC_ONLY",
            "fair_role":"PRIMARY_ARCHIVED_EXTERNAL_CARBON_CYCLE_EVIDENCE",
            "hector_role":"INDEPENDENT_COMPARATOR_NOT_OSCAR",
            "v55_derived_results_live_in_current_json":False,
            "seaweed_primary_area_convention":"YIELD_MAINTAINED_AREA_LIMITED",
            "seaweed_calorie_gap_headline":False,
            "seaweed_ash_credit_to_nutrient_loop":0.0,
            "cultured_fish_counts_as_wild_stock_recovery":False,
        },
    }


def _write_csv(path: Path, rows: Sequence[Mapping]) -> None:
    if not rows:
        return
    keys=[]
    for row in rows:
        for k in row:
            if k not in keys: keys.append(k)
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=keys)
        w.writeheader()
        for row in rows:
            q={}
            for k in keys:
                v=row.get(k)
                q[k]=json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v
            w.writerow(q)


def write_outputs(result: Dict) -> None:
    data=HERE/"data"; data.mkdir(exist_ok=True)
    (data/"planetary_restoration_v57_results.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    attr=result["attribution_v57"]
    _write_csv(data/"v57_attribution_marginal_response.csv",attr["pathwise_marginal_response"]["intervals"])
    _write_csv(data/"v57_seaweed_engineering_constructions.csv",result["seaweed_v57"]["engineering_constructions"])
    _write_csv(data/"v57_seaweed_farmgate_economics.csv",result["seaweed_v57"]["farmgate_economics"])
    _write_csv(data/"v57_seaweed_ash_recovery.csv",result["seaweed_v57"]["ash_fate_primary"]["recovery_scenarios"])
    _write_csv(data/"v57_seaweed_ash_fuel_sensitivity.csv",result["seaweed_v57"]["ash_fate_primary"]["ash_fraction_fuel_sensitivity"])
    _write_csv(data/"v57_seaweed_protein_coverage.csv",[
        {"metric":k,"value":v} for k,v in result["seaweed_v57"]["human_nutrition_primary"].items() if isinstance(v,(int,float,bool))
    ])
    (data/"v57_legacy_supersession.json").write_text(json.dumps(result["legacy_architecture_reference"],indent=2,ensure_ascii=False)+"\n",encoding="utf-8")


def run_tests(result: Dict) -> None:
    h=result["headline"]
    assert h["externally_validated_return_year"] is None
    assert h["fair_returning_configurations"] == 0
    attr=result["attribution_v57"]
    assert attr["initial_condition_and_time_index"]["prior_v56_misaligned_internal_row2026_minus_fair_timebound2026_gap_ppm"] > 6.0
    assert 3.0 < attr["initial_condition_and_time_index"]["correct_fair_historical_p50_offset_vs_noaa_start_ppm"] < 5.0
    assert attr["initial_condition_and_time_index"]["matched_start_response_gap_by_internal_2155_ppm"] > 30.0
    assert 310.0 < attr["no_extension_test"]["fair_p50_after_2183_flux_timebound_2184_ppm"] < 313.0
    assert attr["hector_transient_to_reversal_signal"]["raw_label_crossing"] is not None
    assert 0.15 < attr["pathwise_marginal_response"]["late_interval_apparent_response_fraction"] < 0.30
    assert result["legacy_architecture_reference"]["superseded_by"] == "V57"
    assert result["accounting_rules"]["v55_derived_results_live_in_current_json"] is False
    sw=result["seaweed_v57"]
    primary=next(x for x in sw["engineering_constructions"] if x["construction"]=="yield_maintained_area_limited_PRIMARY")
    assert 100000 < primary["farm_area_km2"] < 102000
    assert abs(primary["dry_yield_t_ha_yr"]-25.0)<1e-12
    central=next(x for x in sw["farmgate_economics"] if x["case"]=="central_large_scale")
    assert central["annual_farmgate_cost_usd_bn_primary"] > 60
    ash=next(x for x in sw["ash_fate_primary"]["recovery_scenarios"] if x["case"]=="central_recovery")
    assert 49 < ash["ash_entering_fuel_process_mt_yr"] < 52
    nut=sw["human_nutrition_primary"]
    assert 47 < nut["full_50g_day_digestible_protein_equivalent_million_people_gross_production"] < 50
    assert nut["calorie_gap_headline_removed"] is True


def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--tests",action="store_true")
    ap.add_argument("--no-write",action="store_true")
    args=ap.parse_args()
    result=run_v57()
    run_tests(result)
    if not args.no_write:
        write_outputs(result)
    if args.tests:
        print("V57 ATTRIBUTION + SEAWEED ACCOUNTING TESTS PASSED")
    print(json.dumps(result["headline"],indent=2,ensure_ascii=False))


if __name__=="__main__":
    main()
