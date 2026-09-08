#!/usr/bin/env python3
"""Planetary Restoration Model V55 — unified seaweed + lineage-recovery release.

V55 merges the two Version-54 branches into a single release boundary:

1. V54 Seaweed Bioeconomy Integrated
   - one physical seaweed mass balance across food, liquid fuels, durable storage,
     materials/feed, standing crop, strategic fuel reserves and habitat;
   - Grid Harvesting from the later v19 physical reconstruction;
   - aviation, heavy-equipment and marine/other liquid-fuel allocation;
   - direct concentrated-solar HTL process heat;
   - explicit additionality sensitivities with reserve-build mass conservation.

2. V54 Lineage Recovery
   - wastewater/food-waste bioenergy and N/P/K nutrient loops;
   - tidal, maritime, storage and firm-clean option screens;
   - shock resilience;
   - tree natural-capital, national allocation and country equalizer;
   - parallel settlement, sanctions, dollar-transition and no-new-burden layers;
   - food/health resource budgets, distributed AI/data centers, Cella archetype,
     workforce transition and cross-border funding.

The V53.1 Earth-system/climate/CDR core remains the authoritative physical core.
Recovered electricity loads/supplies are kept in RECONCILE_ONLY mode until the
86,181.327 TWh/yr external pre-CDR electricity base is decomposed. This prevents
accidental double counting.

The older lineage-recovery seaweed screens are preserved as historical reference
only. The V55 integrated seaweed bioeconomy is the single active seaweed source of
truth.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Mapping, Sequence

HERE = Path(__file__).resolve().parent
BRANCH_DIR = HERE / "previous_branches"

MODEL_VERSION = "55.0"
RELEASE_LABEL = "Planetary Restoration Model Version 55.0 — Unified Lineage + Seaweed Integration"
RELEASE_STATUS = "INTERNAL_INTEGRATED_CANDIDATE_PRIMARY_V53_1_EXTERNAL_VALIDATION_INHERITED; V55_ADDITIONALITY_EXTERNAL_RERUN_PENDING"


# V55 human-food planning assumptions. These are consumption-side screening values,
# deliberately separated from gross food-supply accounting. The user-requested central
# value is 2,350 kcal/person/day, with 2,000-2,500 kcal/day sensitivity bounds.
V55_DAILY_DIET_KCAL_LOW = 2000.0
V55_DAILY_DIET_KCAL_CENTRAL = 2350.0
V55_DAILY_DIET_KCAL_HIGH = 2500.0
V55_TRANSFORMED_TERRESTRIAL_FOOD_CAPACITY_B = 10.2
V55_ENERGY_ONLY_CAPACITY_B = 14.707241956010044
V55_UN_PROJECTED_PEAK_B = 10.3
V55_FOOD_DELIVERY_FRACTION = 0.85  # processing + drying + inland distribution screen


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Load the two V54 branches as auditable implementation dependencies.
lineage = _load_module("v55_lineage_branch", BRANCH_DIR / "v54_lineage_recovery.py")
seaweed_branch = _load_module("v55_seaweed_branch", BRANCH_DIR / "v54_seaweed_integrated.py")


SEAWEED_LEGACY_KEYS = ("seaweed_saf_htl", "grid_harvester", "csp_htl", "seaweed_food")
SEAWEED_LINEAGE_NAMES = {
    "Seaweed SAF / HTL",
    "Grid seaweed harvester",
    "Seaweed human food",
}


def _rows_from_dict(d: Mapping, prefix: str = "") -> List[Dict]:
    rows: List[Dict] = []
    for key, value in d.items():
        metric = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, Mapping):
            rows.extend(_rows_from_dict(value, metric))
        elif isinstance(value, list):
            rows.append({"metric": metric, "value": json.dumps(value, ensure_ascii=False)})
        else:
            rows.append({"metric": metric, "value": value})
    return rows


def _write_csv(path: Path, rows: Sequence[Mapping]) -> None:
    if not rows:
        return
    keys: List[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            q = {}
            for key in keys:
                value = row.get(key)
                q[key] = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value
            writer.writerow(q)


def merged_lineage_modules() -> Dict:
    """Return the live recovered modules plus historical seaweed reference screens.

    V55 removes the duplicate V54-lineage seaweed screens from the active module set.
    They remain accessible under ``historical_seaweed_reference`` for auditability.
    """
    all_restored = lineage.restored_modules_v54()
    historical = {k: all_restored[k] for k in SEAWEED_LEGACY_KEYS if k in all_restored}
    active = {k: v for k, v in all_restored.items() if k not in SEAWEED_LEGACY_KEYS}
    return {
        "active_recovered_modules": active,
        "historical_seaweed_reference": historical,
    }


def lineage_register_v55() -> List[Dict]:
    rows: List[Dict] = []
    for row in lineage.lineage_register_v54():
        q = dict(row)
        if q.get("module") in SEAWEED_LINEAGE_NAMES:
            q["v55_status"] = "MERGED_INTO_V55_UNIFIED_SEAWEED_MODULE"
            q["v55_coupling_rule"] = "Historical v9/v18/v19 values retained for lineage only; V55 unified mass balance is authoritative."
        else:
            q["v55_status"] = "ACTIVE_RECOVERED_MODULE"
            q["v55_coupling_rule"] = q.get("coupling_rule")
        rows.append(q)
    # CSP/HTL was embedded in the old seaweed/SAF lineage but deserves an explicit merge entry.
    rows.extend([
        {
            "module": "CSP + HTL seaweed process integration",
            "source_lineage": "v18/v19",
            "v54_status": "RESTORED",
            "coupling_rule": "Legacy process-energy screen",
            "v55_status": "MERGED_INTO_V55_UNIFIED_SEAWEED_MODULE",
            "v55_coupling_rule": "V55 uses the integrated 1.465 Gt/yr biomass allocation and scales direct solar heat/electric-H2 process demand consistently.",
        },
        {
            "module": "Strategic seaweed fuel reserve",
            "source_lineage": "V54 seaweed branch",
            "v54_status": "NEW_IN_V54_SEAWEED_BRANCH",
            "coupling_rule": "Working carbon stock",
            "v55_status": "ACTIVE_INTEGRATED_MODULE",
            "v55_coupling_rule": "Fuel placed into reserve is subtracted from same-year delivered fuel; reserve carbon is not durable CDR.",
        },
        {
            "module": "Standing seaweed farm carbon stock",
            "source_lineage": "V54 seaweed branch",
            "v54_status": "NEW_IN_V54_SEAWEED_BRANCH",
            "coupling_rule": "Working carbon stock",
            "v55_status": "ACTIVE_INTEGRATED_MODULE",
            "v55_coupling_rule": "Reported as temporary stock; not added to permanent CDR.",
        },
        {
            "module": "Heavy-equipment low-carbon liquid fuel",
            "source_lineage": "V54 seaweed branch",
            "v54_status": "NEW_IN_V54_SEAWEED_BRANCH",
            "coupling_rule": "Technology implementation",
            "v55_status": "ACTIVE_INTEGRATED_MODULE",
            "v55_coupling_rule": "25% of finished V55 seaweed liquid-fuel energy in the central allocation; primary climate case does not double-count generic V53 transition abatement.",
        },
        {
            "module": "Seaweed farm habitat + edible aquatic co-culture",
            "source_lineage": "V54 seaweed branch",
            "v54_status": "NEW_IN_V54_SEAWEED_BRANCH",
            "coupling_rule": "Scenario only",
            "v55_status": "ACTIVE_SCREEN",
            "v55_coupling_rule": "Physical habitat footprint reported; illustrative edible aquatic production remains outside the core fish-stock headline.",
        },
        {
            "module": "Durable seaweed storage / BiCRS land relief",
            "source_lineage": "V54 seaweed branch",
            "v54_status": "NEW_IN_V54_SEAWEED_BRANCH",
            "coupling_rule": "Substitution",
            "v55_status": "ACTIVE_SENSITIVITY",
            "v55_coupling_rule": "Substitutes for part of existing BiCRS feedstock; never stacked as extra CDR.",
        },
    ])
    return rows


def food_logistics_v55(seaweed_result: Dict) -> Dict:
    """Dry-food logistics screen for moving marine food inland.

    The seaweed production model reports dry biomass. This function makes the otherwise
    hidden wet-to-dry handling burden explicit. It uses a thermodynamic drying minimum
    and an editable engineering multiplier; the thermal requirement is not treated as
    grid electricity because solar thermal / waste heat can supply low-temperature heat.
    Inland transport is a scenario screen, not a calibrated Africa logistics forecast.
    """
    sea = seaweed_result["seaweed_bioeconomy"]
    food_mt = float(sea["food"]["food_grade_dry_seaweed_mt_yr"])
    initial_dry_matter_fraction = 0.125
    final_dry_matter_fraction = 0.90
    wet_t_per_dry_t = 1.0 / initial_dry_matter_fraction
    final_product_t_per_dry_t = 1.0 / final_dry_matter_fraction
    water_removed_t_per_dry_t = wet_t_per_dry_t - final_product_t_per_dry_t
    latent_heat_mj_per_kg_water = 2.257
    thermodynamic_min_mwhth_per_dry_t = water_removed_t_per_dry_t * latent_heat_mj_per_kg_water / 3.6
    drying_system_multiplier = 1.25
    central_drying_mwhth_per_dry_t = thermodynamic_min_mwhth_per_dry_t * drying_system_multiplier
    electric_aux_mwh_per_dry_t = 0.08
    inland_distance_km = 1500.0
    transport_kwh_per_t_km = 0.10
    drying_heat_twhth = food_mt * 1e6 * central_drying_mwhth_per_dry_t / 1e6
    drying_aux_twh = food_mt * 1e6 * electric_aux_mwh_per_dry_t / 1e6
    transport_twh = food_mt * 1e6 * inland_distance_km * transport_kwh_per_t_km / 1e9
    return {
        "classification": "ENGINEERING_SCENARIO_FOR_DRY_FOOD_LOGISTICS_NOT_A_CALIBRATED_REGIONAL_FORECAST",
        "initial_harvest_dry_matter_fraction": initial_dry_matter_fraction,
        "final_food_product_dry_matter_fraction": final_dry_matter_fraction,
        "water_removed_t_per_t_dry_food": water_removed_t_per_dry_t,
        "thermodynamic_minimum_drying_mwhth_per_t_dry_food": thermodynamic_min_mwhth_per_dry_t,
        "central_drying_heat_mwhth_per_t_dry_food": central_drying_mwhth_per_dry_t,
        "central_food_allocation_dry_mt_yr": food_mt,
        "central_drying_heat_twhth_yr": drying_heat_twhth,
        "central_drying_aux_electricity_twh_yr": drying_aux_twh,
        "central_inland_transport_distance_km": inland_distance_km,
        "central_transport_energy_intensity_kwh_t_km": transport_kwh_per_t_km,
        "central_inland_transport_electricity_twh_yr": transport_twh,
        "central_drying_plus_transport_electricity_twh_yr": drying_aux_twh + transport_twh,
        "preferred_heat_sources": "Direct solar thermal, recovered industrial/data-center heat, and other low-carbon low-temperature heat before grid electricity.",
        "inland_distribution_use_case": "Dried shelf-stable seaweed ingredients can be shipped from coastal farms to inland food-deficit regions; exact routes, fortification, species safety, storage and market acceptance require regional modeling.",
    }


def hunger_and_population_v55(seaweed_result: Dict) -> Dict:
    """Seaweed hunger-relief capacity and human-population screening limits.

    This is intentionally a capacity screen, not a prediction that logistics or politics
    automatically end hunger. The 10.2-billion transformed terrestrial benchmark is kept
    as an evidence anchor from the earlier model; seaweed food is added only as an
    explicitly additional marine calorie stream. Energy remains a separate 14.707B screen.
    """
    food_rows = seaweed_result["food_allocation_sensitivity"]
    by_case = {r["case"]: r for r in food_rows}
    mature_dry_gt = float(seaweed_result["seaweed_bioeconomy"]["total_dry_biomass_gt_yr"])
    kcal_per_kg = float(seaweed_branch.SeaweedBioeconomyInputs().edible_dry_kcal_kg)

    # Recalculate full-diet equivalents at explicit V55 calorie assumptions instead of
    # relying on any older 3,700-kcal gross-supply interpretation.
    calorie_sensitivity = []
    central_food_mt = float(by_case["central_5pct_food"]["food_grade_dry_seaweed_mt_yr"])
    annual_central_kcal = central_food_mt * 1e9 * kcal_per_kg
    for kcal_day in (V55_DAILY_DIET_KCAL_LOW, V55_DAILY_DIET_KCAL_CENTRAL, V55_DAILY_DIET_KCAL_HIGH):
        eq_b = annual_central_kcal / (kcal_day * 365.0) / 1e9
        calorie_sensitivity.append({
            "daily_consumed_kcal_per_person": kcal_day,
            "seaweed_full_diet_equivalent_billion_people_at_5pct_food": eq_b,
            "evidence_anchored_food_capacity_billion": V55_TRANSFORMED_TERRESTRIAL_FOOD_CAPACITY_B + eq_b,
            "integrated_capacity_after_energy_cap_billion": min(V55_ENERGY_ONLY_CAPACITY_B, V55_TRANSFORMED_TERRESTRIAL_FOOD_CAPACITY_B + eq_b),
            "interpretation": "Consumption-side screening value; gross food-system supply can be higher because of losses and waste.",
        })

    capacity_cases = []
    for case in ("central_5pct_food", "food_priority_20pct", "food_emergency_50pct", "all_food_theoretical_ceiling"):
        r = by_case[case]
        food_mt = float(r["food_grade_dry_seaweed_mt_yr"])
        eq_b = food_mt * 1e9 * kcal_per_kg / (V55_DAILY_DIET_KCAL_CENTRAL * 365.0) / 1e9
        food_cap = V55_TRANSFORMED_TERRESTRIAL_FOOD_CAPACITY_B + eq_b
        capacity_cases.append({
            "case": case,
            "food_share": float(r["food_share"]),
            "seaweed_food_dry_mt_yr": food_mt,
            "seaweed_full_diet_equivalent_billion_people_at_2350_kcal": eq_b,
            "evidence_anchored_food_capacity_billion": food_cap,
            "energy_only_capacity_billion": V55_ENERGY_ONLY_CAPACITY_B,
            "integrated_capacity_billion": min(food_cap, V55_ENERGY_ONLY_CAPACITY_B),
            "finished_fuel_energy_twh_yr": float(r["finished_fuel_energy_twh_yr"]),
            "status": "SCREENING_CAPACITY_NOT_EMPIRICAL_EARTH_CARRYING_CAPACITY",
        })

    # Hunger-gap closure capacity. 85% delivery is an explicit logistics haircut.
    hunger_rows = []
    deficit_levels = (300.0, 400.0, 500.0)
    target_people_m = (100.0, 500.0, 800.0, 1000.0)
    for case in ("central_5pct_food", "food_priority_20pct", "food_emergency_50pct"):
        r = by_case[case]
        food_share = float(r["food_share"])
        mature_food_mt = mature_dry_gt * 1000.0 * food_share
        delivered_annual_kcal = mature_food_mt * 1e9 * kcal_per_kg * V55_FOOD_DELIVERY_FRACTION
        for deficit in deficit_levels:
            mature_people_m = delivered_annual_kcal / (deficit * 365.0) / 1e6
            row = {
                "case": case,
                "food_share": food_share,
                "calorie_deficit_kcal_person_day": deficit,
                "delivery_fraction_after_processing_distribution": V55_FOOD_DELIVERY_FRACTION,
                "mature_deficit_coverage_million_people": mature_people_m,
            }
            for target_m in target_people_m:
                first_year = None
                for year in range(2026, 2061):
                    dep = seaweed_branch.deployment_fraction(year)
                    if mature_people_m * dep >= target_m:
                        first_year = year
                        break
                row[f"first_year_capacity_covers_{int(target_m)}m_people"] = first_year
            row["caution"] = "Capacity threshold only; ending starvation also requires safe species/processing, micronutrients, financing, storage, ports, inland transport, conflict access and local distribution."
            hunger_rows.append(row)

    # Climate trade-off for prioritizing food over fuel. These are still additionality-only
    # deterministic sensitivities, not the V55 primary climate forecast.
    food_priority_climate = []
    for name, food, fuel, durable, mat in (
        ("central_5pct_food", 0.05, 0.80, 0.10, 0.05),
        ("food_priority_20pct", 0.20, 0.65, 0.10, 0.05),
        ("food_emergency_50pct", 0.50, 0.35, 0.10, 0.05),
    ):
        p = seaweed_branch.SeaweedBioeconomyInputs(
            edible_food_share=food,
            liquid_fuel_feedstock_share=fuel,
            durable_storage_share=durable,
            materials_feed_share=mat,
            reference_daily_diet_kcal=V55_DAILY_DIET_KCAL_CENTRAL,
        )
        rr = seaweed_branch._run_design_with_additionality(1.0, True, p)
        food_priority_climate.append({
            "case": name,
            "food_share": food,
            "fuel_share": fuel,
            "mature_fuel_abatement_gtco2_yr_if_fully_additional": rr["mature_fuel_abatement_gtco2_yr_if_additional"],
            "first_below_280_year_if_fuel_abatement_fully_additional": rr["first_below_280_year"],
            "cumulative_cdr_to_target_gtco2": rr["cumulative_cdr_to_target_gtco2"],
            "status": "DETERMINISTIC_ADDITIONALITY_SENSITIVITY_ONLY",
        })

    historical = {
        "un_projected_peak_billion": V55_UN_PROJECTED_PEAK_B,
        "historical_energy_only_capacity_billion": V55_ENERGY_ONLY_CAPACITY_B,
        "historical_transformed_terrestrial_food_benchmark_billion": V55_TRANSFORMED_TERRESTRIAL_FOOD_CAPACITY_B,
        "historical_v11_optimized_population_mc_median_billion": 10.923795,
        "historical_v16_high_planning_case_billion": 12.55,
        "interpretation": "The older 10.924B and 12.55B values are retained as historical scenarios, not silently promoted into the new V55 evidence-anchored capacity calculation.",
    }
    return {
        "daily_calorie_assumptions": {
            "low_kcal_person_day": V55_DAILY_DIET_KCAL_LOW,
            "central_kcal_person_day": V55_DAILY_DIET_KCAL_CENTRAL,
            "high_kcal_person_day": V55_DAILY_DIET_KCAL_HIGH,
            "note": "These are consumption-side screening values. V55 does not use 3,700 kcal/person/day as average human consumption.",
        },
        "calorie_sensitivity": calorie_sensitivity,
        "population_capacity_cases": capacity_cases,
        "hunger_gap_capacity": hunger_rows,
        "food_priority_climate_tradeoff": food_priority_climate,
        "historical_reference_points": historical,
        "population_caution": "No single number is asserted as Earth's empirical carrying capacity. V55 reports bounded scenario capacities because diets, crop yields, biodiversity, water, materials, regional climate, distribution and governance can become binding.",
        "hunger_caution": "Seaweed can improve food-security resilience because marine farms are buffered from many land heat extremes, but marine heatwaves, storms and species thermal limits remain material risks.",
    }


def energy_reconciliation_v55(seaweed: Dict, active_modules: Dict, food_logistics: Dict | None = None) -> Dict:
    external = float(lineage.BaseSystemInputs().pre_cdr_transformed_electricity_twh_yr)
    wastewater = active_modules["wastewater_food_waste_bioenergy"]["current_planning_central"]
    tidal = active_modules["tidal_energy"]["central"]
    maritime = active_modules["global_maritime"]["central_total_shipping_electricity_twh_yr"]
    process = seaweed["process_energy"]["electricity_plus_hydrogen_twh_e_yr"]
    harvest = seaweed["grid_harvester"]["global_harvest_electricity_twh_yr"]
    supply = wastewater["net_electricity_with_food_waste_twh_yr"] + tidal["net_delivered_tidal_twh_yr"]
    food_logistics = food_logistics or {}
    food_elec = float(food_logistics.get("central_drying_plus_transport_electricity_twh_yr", 0.0))
    seaweed_load = process + harvest + food_elec
    return {
        "mode": "RECONCILE_ONLY",
        "external_pre_cdr_electricity_twh_yr": external,
        "explicit_supply_candidates_twh_yr": {
            "wastewater_plus_food_waste_current_10p3b": wastewater["net_electricity_with_food_waste_twh_yr"],
            "tidal_net": tidal["net_delivered_tidal_twh_yr"],
            "candidate_supply_total": supply,
        },
        "explicit_load_candidates_twh_yr": {
            "seaweed_htl_electricity_plus_hydrogen": process,
            "seaweed_grid_harvesting": harvest,
            "seaweed_food_drying_transport_electricity": food_elec,
            "seaweed_new_load_total": seaweed_load,
            "legacy_detailed_maritime": maritime,
        },
        "candidate_supply_minus_new_seaweed_load_twh_yr": supply - seaweed_load,
        "food_drying_thermal_heat_twhth_yr": float(food_logistics.get("central_drying_heat_twhth_yr", 0.0)),
        "headline_adjustment_twh_yr": 0.0,
        "rule": "No restored load/supply is added to or subtracted from the V53.1 86,181.327 TWh/yr external pre-CDR electricity screen until that screen is decomposed. The candidate balance is shown only to make the hidden flows visible.",
        "maritime_note": "The detailed maritime electricity value is particularly likely to overlap the technology-neutral V53 transition and external electricity base; it is never added automatically.",
    }


def integrated_outcomes_v55(seaweed_result: Dict, active_modules: Dict, reconciliation: Dict, human_food: Dict, food_logistics: Dict) -> Dict:
    sea = seaweed_result["seaweed_bioeconomy"]
    h = seaweed_result["headline_comparison"]
    ens = seaweed_result["v53_1_core"]["ensemble_summary"]
    wastewater = active_modules["wastewater_food_waste_bioenergy"]["current_planning_central"]
    tidal = active_modules["tidal_energy"]["central"]
    nutrients = active_modules["nutrient_loops_npk"]["central"]
    xborder = active_modules["cross_border_fee"]
    cella_rows = active_modules["ai_data_center_transition"]["cella_rows"]
    cella = {r["metric"]: r["value"] for r in cella_rows}
    return {
        "climate": {
            "v53_1_700_draw_conditional_median_return_year": ens["return_year_p50_conditional"],
            "v53_1_700_draw_p05_return_year": ens["return_year_p05_conditional"],
            "v53_1_700_draw_p95_return_year": ens["return_year_p95_conditional"],
            "v53_1_fraction_not_restored_within_horizon": ens["fraction_not_restored_within_horizon"],
            "v55_primary_deterministic_return_year": h["v54_primary_substitution_first_below_280_year"],
            "v55_50pct_seaweed_additionality_return_year": h["v54_50pct_additionality_first_below_280_year"],
            "v55_100pct_seaweed_additionality_return_year": h["v54_100pct_additionality_first_below_280_year"],
            "primary_change_vs_v53_years": h["v54_primary_substitution_first_below_280_year"] - h["v53_1_primary_accelerated_first_below_280_year"],
            "100pct_additionality_change_vs_v53_years": h["v54_100pct_additionality_first_below_280_year"] - h["v53_1_primary_accelerated_first_below_280_year"],
            "v53_cumulative_cdr_to_target_gtco2": h["v53_1_primary_cumulative_cdr_to_target_gtco2"],
            "v55_100pct_additionality_cumulative_cdr_to_target_gtco2": h["v54_100pct_additionality_cumulative_cdr_to_target_gtco2"],
            "cdr_reduction_at_100pct_additionality_gtco2": h["v53_1_primary_cumulative_cdr_to_target_gtco2"] - h["v54_100pct_additionality_cumulative_cdr_to_target_gtco2"],
            "status": "Primary climate result unchanged; additionality cases remain sensitivity-only and require fresh external FaIR/Hector reruns.",
        },
        "seaweed": {
            "farm_area_km2": sea["area_km2"],
            "dry_biomass_gt_yr": sea["total_dry_biomass_gt_yr"],
            "finished_fuel_energy_twh_yr": sea["liquid_fuels"]["finished_fuel_energy_twh_yr"],
            "aviation_energy_twh_yr": sea["liquid_fuels"]["aviation_energy_twh_yr"],
            "heavy_equipment_energy_twh_yr": sea["liquid_fuels"]["heavy_equipment_energy_twh_yr"],
            "marine_other_energy_twh_yr": sea["liquid_fuels"]["marine_other_energy_twh_yr"],
            "potential_lifecycle_avoided_fossil_gtco2_yr": sea["liquid_fuels"]["potential_lifecycle_avoided_fossil_gtco2_yr"],
            "food_grade_dry_seaweed_mt_yr": sea["food"]["food_grade_dry_seaweed_mt_yr"],
            "full_diet_calorie_equivalent_million_people": sea["food"]["full_diet_calorie_equivalent_million_people"],
            "standing_farm_carbon_gtco2eq": sea["carbon_stocks"]["average_standing_farm_carbon_stock_gtco2_equivalent"],
            "strategic_fuel_reserve_gtco2eq": sea["carbon_stocks"]["strategic_fuel_reserve_target_gtco2_equivalent"],
            "combined_working_stock_gtco2eq": sea["carbon_stocks"]["combined_working_stock_gtco2_equivalent"],
            "durable_storage_inside_bicrs_gtco2_yr": sea["carbon_stocks"]["durable_seaweed_storage_gtco2_yr"],
            "habitat_footprint_km2": sea["habitat"]["farm_habitat_footprint_km2"],
            "illustrative_coculture_edible_aquatic_product_mt_yr": sea["habitat"]["illustrative_coculture_edible_aquatic_product_mt_yr"],
            "grid_harvest_electricity_twh_yr": sea["grid_harvester"]["global_harvest_electricity_twh_yr"],
            "conventional_proxy_harvest_electricity_twh_yr": sea["grid_harvester"]["conventional_proxy_harvest_electricity_twh_yr"],
            "grid_harvest_cost_saving_usd_bn_yr": sea["grid_harvester"]["harvest_cost_saving_usd_bn_yr"],
        },
        "circular_energy_and_nutrients": {
            "wastewater_plus_food_waste_electricity_twh_yr_at_10p3b": wastewater["net_electricity_with_food_waste_twh_yr"],
            "wastewater_useful_heat_twhth_yr_at_10p3b": wastewater["useful_heat_twhth_yr"],
            "tidal_net_generation_twh_yr": tidal["net_delivered_tidal_twh_yr"],
            "tidal_firm_value_twh_yr": tidal["firm_value_equivalent_twh_yr"],
            "n_fertilizer_replacement_fraction": nutrients["effective_n_fertilizer_replacement_fraction"],
            "p_fertilizer_replacement_fraction": nutrients["effective_p_fertilizer_replacement_fraction"],
            "k_fertilizer_replacement_fraction": nutrients["effective_k_fertilizer_replacement_fraction"],
            "n_crediting_ratio_vs_legacy_gross": nutrients["n_crediting_ratio_vs_legacy_gross"],
            "p_crediting_ratio_vs_legacy_gross": nutrients["p_crediting_ratio_vs_legacy_gross"],
        },
        "finance_and_implementation": {
            "cross_border_equalizer_access_pool_usd_bn_yr": xborder["equalizer_access_pool_usd_bn_yr"],
            "cross_border_direct_additional_cdr_fund_usd_tn_yr_legacy_screen": xborder["direct_additional_cdr_fund_usd_tn_yr"],
            "distributed_ai_network_year20_sites": next(r["value"] for r in active_modules["ai_data_center_transition"]["distributed_network_rows"] if r["metric"] == "Baseline Year-20 network sites"),
            "cella_continuous_it_load_mw": cella["Continuous IT load"],
            "cella_useful_recovered_heat_gwh_yr": cella["Useful recovered heat"],
            "worker_transition_need_usd_bn_yr": active_modules["workforce_transition"]["annual_transition_need_usd_bn_yr"],
            "worker_transition_existing_fund_usd_bn_yr": active_modules["workforce_transition"]["existing_transition_fund_usd_bn_yr"],
        },
        "food_hunger_population": {
            "daily_calorie_central_kcal_person_day": human_food["daily_calorie_assumptions"]["central_kcal_person_day"],
            "central_5pct_integrated_population_capacity_billion": human_food["population_capacity_cases"][0]["integrated_capacity_billion"],
            "food_priority_20pct_integrated_population_capacity_billion": human_food["population_capacity_cases"][1]["integrated_capacity_billion"],
            "food_emergency_50pct_integrated_population_capacity_billion": human_food["population_capacity_cases"][2]["integrated_capacity_billion"],
            "all_food_theoretical_integrated_population_capacity_billion": human_food["population_capacity_cases"][3]["integrated_capacity_billion"],
            "central_5pct_mature_500kcal_gap_coverage_million_people": next(r["mature_deficit_coverage_million_people"] for r in human_food["hunger_gap_capacity"] if r["case"]=="central_5pct_food" and r["calorie_deficit_kcal_person_day"]==500.0),
            "food_priority_20pct_first_year_800m_500kcal_gap_capacity": next(r["first_year_capacity_covers_800m_people"] for r in human_food["hunger_gap_capacity"] if r["case"]=="food_priority_20pct" and r["calorie_deficit_kcal_person_day"]==500.0),
            "food_emergency_50pct_first_year_800m_500kcal_gap_capacity": next(r["first_year_capacity_covers_800m_people"] for r in human_food["hunger_gap_capacity"] if r["case"]=="food_emergency_50pct" and r["calorie_deficit_kcal_person_day"]==500.0),
            "central_food_drying_heat_twhth_yr": food_logistics["central_drying_heat_twhth_yr"],
            "central_food_drying_transport_electricity_twh_yr": food_logistics["central_drying_plus_transport_electricity_twh_yr"],
            "status": "Capacity screen, not a forecast date for ending hunger or an empirical Earth carrying-capacity claim.",
        },
        "energy_reconciliation": reconciliation,
    }


def run_v55() -> Dict:
    # The seaweed branch preserves the frozen submitted 700-draw V53.1 ensemble by default
    # and reruns only the deterministic V53.1 cases needed for the V55 seaweed sensitivities.
    seaweed_result = seaweed_branch.run_v54(0)
    # Promote the merged branch outputs to the V55 public namespace while retaining
    # the original V54-key aliases for reproducibility of the source branch.
    seaweed_result["model_version"] = MODEL_VERSION
    seaweed_result["release_label"] = RELEASE_LABEL
    seaweed_result["classification"] = "V55 unified seaweed bioeconomy merged with the lineage-recovery release; V53.1 remains the Earth-system core."
    hc = seaweed_result.get("headline_comparison", {})
    hc.update({
        "v55_primary_substitution_first_below_280_year": hc.get("v54_primary_substitution_first_below_280_year"),
        "v55_working_stock_only_first_below_280_year": hc.get("v54_working_stock_only_first_below_280_year"),
        "v55_50pct_additionality_first_below_280_year": hc.get("v54_50pct_additionality_first_below_280_year"),
        "v55_100pct_additionality_first_below_280_year": hc.get("v54_100pct_additionality_first_below_280_year"),
        "v55_100pct_additionality_peak_co2_ppm": hc.get("v54_100pct_additionality_peak_co2_ppm"),
        "v55_100pct_additionality_cumulative_cdr_to_target_gtco2": hc.get("v54_100pct_additionality_cumulative_cdr_to_target_gtco2"),
    })
    merged = merged_lineage_modules()
    active = merged["active_recovered_modules"]
    current_resources = {
        "water": lineage.water(),
        "seaweed_v53_nutrient_screen": lineage.seaweed(),
        "nutrients": lineage.nutrients(),
        "plastics": lineage.plastics(),
        "banking_transition": lineage.banking_transition(),
        "external_social_ecological_screens": lineage.external_social_ecological_screens(),
    }
    food_logistics = food_logistics_v55(seaweed_result)
    human_food = hunger_and_population_v55(seaweed_result)
    reconciliation = energy_reconciliation_v55(seaweed_result["seaweed_bioeconomy"], active, food_logistics)
    register = lineage_register_v55()
    outcomes = integrated_outcomes_v55(seaweed_result, active, reconciliation, human_food, food_logistics)
    return {
        "model_version": MODEL_VERSION,
        "release_label": RELEASE_LABEL,
        "release_status": RELEASE_STATUS,
        "classification": "V53.1 Earth-system core + unified V55 seaweed bioeconomy + recovered historical physical/economic/governance modules, with explicit double-count protection and scenario-vs-core boundaries.",
        "v53_1_core": seaweed_result["v53_1_core"],
        "v53_1_core_validation": seaweed_result["v53_1_core_validation"],
        "integrated_seaweed": seaweed_result,
        "active_recovered_modules": active,
        "historical_seaweed_reference": merged["historical_seaweed_reference"],
        "current_resource_screens": current_resources,
        "lineage_register": register,
        "food_logistics": food_logistics,
        "hunger_and_population": human_food,
        "energy_reconciliation": reconciliation,
        "integrated_outcomes": outcomes,
        "merge_decisions": {
            "active_seaweed_source_of_truth": "V54 Seaweed Bioeconomy Integrated branch mass balance, promoted to V55",
            "historical_lineage_seaweed_treatment": "Retained for provenance only; not active to prevent duplicate seaweed fuel/food/harvester accounting.",
            "electricity_coupling": "RECONCILE_ONLY until the 86,181.327 TWh/yr V53.1 external electricity base is decomposed.",
            "cross_border_cdr_funding": "Restored as a financing mechanism but not automatically added to V53.1 CDR, because the V53.1 funding architecture may already include overlapping transaction-funded removal.",
            "old_restoration_dates": "Superseded; V55 keeps the V53.1 Earth-system core and V55 seaweed additionality sensitivities.",
            "old_zero_new_nuclear_conclusion": "Superseded; V53.1 synthetic 8760 adequacy tests remain authoritative until the recovered generation portfolio is reconciled.",
        },
        "external_validation_status": {
            "primary_v55_trajectory": "Identical to V53.1 primary substitution accounting; inherits the archived V53.1 external benchmark comparison.",
            "working_stock_and_50pct_100pct_additionality": "Not yet externally rerun through calibrated/constrained FaIR/Hector in V55; internal deterministic sensitivities only.",
        },
    }


def write_outputs(result: Dict, root: Path = HERE) -> None:
    data = root / "data"
    data.mkdir(parents=True, exist_ok=True)
    (data / "planetary_restoration_v55_results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    sea = result["integrated_seaweed"]
    _write_csv(data / "v55_seaweed_annual_deployment.csv", sea["seaweed_annual_deployment"])
    _write_csv(data / "v55_seaweed_additionality_sensitivity.csv", sea["additionality_sensitivity"])
    _write_csv(data / "v55_seaweed_parameter_sensitivity.csv", sea["seaweed_parameter_sensitivity"])
    _write_csv(data / "v55_food_allocation_sensitivity.csv", sea["food_allocation_sensitivity"])
    _write_csv(data / "v55_habitat_coculture_sensitivity.csv", sea["habitat_coculture_sensitivity"])
    _write_csv(data / "v55_bicrs_land_relief_sensitivity.csv", sea["bicrs_land_relief_sensitivity"])
    _write_csv(data / "v55_working_stock_only_sensitivity.csv", [sea["working_stock_only_sensitivity"]])
    _write_csv(data / "v55_lineage_register.csv", result["lineage_register"])
    _write_csv(data / "v55_energy_reconciliation.csv", _rows_from_dict(result["energy_reconciliation"]))
    _write_csv(data / "v55_integrated_outcomes.csv", _rows_from_dict(result["integrated_outcomes"]))
    _write_csv(data / "v55_food_logistics.csv", _rows_from_dict(result["food_logistics"]))
    _write_csv(data / "v55_population_capacity.csv", result["hunger_and_population"]["population_capacity_cases"])
    _write_csv(data / "v55_calorie_sensitivity.csv", result["hunger_and_population"]["calorie_sensitivity"])
    _write_csv(data / "v55_hunger_gap_capacity.csv", result["hunger_and_population"]["hunger_gap_capacity"])
    _write_csv(data / "v55_food_priority_climate_tradeoff.csv", result["hunger_and_population"]["food_priority_climate_tradeoff"])
    _write_csv(data / "v55_current_resource_screens.csv", _rows_from_dict(result["current_resource_screens"]))

    for key, module in result["active_recovered_modules"].items():
        if isinstance(module, dict) and isinstance(module.get("rows"), list):
            _write_csv(data / f"v55_{key}.csv", module["rows"])
        elif key == "ai_data_center_transition":
            _write_csv(data / "v55_ai_data_center_market.csv", module["market_rows"])
            _write_csv(data / "v55_distributed_ai_network.csv", module["distributed_network_rows"])
            _write_csv(data / "v55_cella_archetype.csv", module["cella_rows"])
        elif key == "country_equalizer":
            _write_csv(data / "v55_country_equalizer_examples.csv", module["examples"])
        else:
            _write_csv(data / f"v55_{key}.csv", _rows_from_dict(module))


def run_v55_tests(result: Dict | None = None) -> None:
    r = result or run_v55()
    sea = r["integrated_seaweed"]["seaweed_bioeconomy"]
    active = r["active_recovered_modules"]
    h = r["integrated_seaweed"]["headline_comparison"]
    ens = r["v53_1_core"]["ensemble_summary"]

    assert r["model_version"] == "55.0"
    assert ens["samples"] == 700
    assert h["v54_primary_substitution_first_below_280_year"] == 2155
    assert h["v54_50pct_additionality_first_below_280_year"] == 2153
    assert h["v54_100pct_additionality_first_below_280_year"] == 2151
    assert abs(sea["total_dry_biomass_gt_yr"] - 1.465) < 1e-12
    assert abs(sea["liquid_fuels"]["finished_fuel_energy_twh_yr"] - 2379.811111111112) < 1e-6
    assert abs(sea["grid_harvester"]["global_harvest_electricity_twh_yr"] - 15.674804149085904) < 1e-9
    assert "seaweed_saf_htl" not in active and "grid_harvester" not in active and "seaweed_food" not in active and "csp_htl" not in active
    assert "wastewater_food_waste_bioenergy" in active and "tidal_energy" in active and "tree_wealth" in active
    wastewater = active["wastewater_food_waste_bioenergy"]["current_planning_central"]
    assert abs(wastewater["net_electricity_with_food_waste_twh_yr"] - 730.7553790746002) < 1e-9
    assert abs(active["tidal_energy"]["central"]["net_delivered_tidal_twh_yr"] - 1800.0) < 1e-12
    assert r["energy_reconciliation"]["headline_adjustment_twh_yr"] == 0.0
    assert len(r["lineage_register"]) >= 29
    assert abs(r["integrated_outcomes"]["climate"]["cdr_reduction_at_100pct_additionality_gtco2"] - 62.328894196913) < 1e-6
    assert r["v53_1_core_validation"]["status"] == "PASS"
    hp=r["hunger_and_population"]
    assert hp["daily_calorie_assumptions"]["central_kcal_person_day"] == 2350.0
    assert 10.36 < hp["population_capacity_cases"][0]["integrated_capacity_billion"] < 10.38
    assert hp["hunger_gap_capacity"][0]["delivery_fraction_after_processing_distribution"] == 0.85
    assert r["food_logistics"]["central_drying_heat_twhth_yr"] > 300.0
    assert r["integrated_outcomes"]["food_hunger_population"]["food_priority_20pct_first_year_800m_500kcal_gap_capacity"] is not None
    print("V55 UNIFIED INTEGRATION TESTS PASSED")


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=RELEASE_LABEL)
    ap.add_argument("--tests", action="store_true", help="Run the V55 merge/integration validation suite.")
    ap.add_argument("--no-write", action="store_true", help="Do not write result JSON/CSV files.")
    args = ap.parse_args(argv)
    result = run_v55()
    if args.tests:
        run_v55_tests(result)
    if not args.no_write:
        write_outputs(result, HERE)
    print(json.dumps({
        "model_version": result["model_version"],
        "release_label": result["release_label"],
        "integrated_outcomes": result["integrated_outcomes"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
