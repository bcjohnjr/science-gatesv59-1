#!/usr/bin/env python3
"""Planetary Restoration Model V56 — audit-corrected external-validation release.

V56 is a corrective integration release. It preserves the V55 physical/economic
architecture but changes the scientific hierarchy:

* official archived FaIR 2.2.4 / fair-calibrate 1.4.1 results are first-class
  validation outputs and are authoritative over the Joos IRF for sustained large
  negative-emissions interpretation;
* Hector 3.5.0 is retained as an independent carbon-cycle comparator, explicitly
  labelled as a Hector substitution rather than the OSCAR run originally required;
* the Joos four-reservoir carbon calculation is retained only as a diagnostic;
* every V53.1 top-level adverse/stress block is propagated into the V56 result;
* seaweed has a nutrient-closed central case, an ecological accumulation benchmark,
  and a managed-nutrient full-potential case rather than silently treating the
  geometric 1.465 Gt dry/yr potential as nutrient-closed;
* seaweed ash is explicit and HTL finished-fuel yield is applied to ash-free dry
  organic matter;
* human-food reporting separates protein/micronutrient value from an intentionally
  conservative protein-only metabolizable-energy floor and the older gross-energy
  upper screen; the old 2,000 kcal/kg number is NOT treated as metabolizable energy;
* fisheries and the missing v16-v19 welfare/economic/material/demographic/monetary
  screens are restored explicitly as literature/scenario layers.

No precise year for return to 280 ppm is presented as externally validated in V56.
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import importlib.util
import json
import math
import sys
import zipfile
from pathlib import Path
from typing import Dict, List, Mapping, Sequence

HERE = Path(__file__).resolve().parent
MODEL_VERSION = "56.0"
RELEASE_LABEL = "Planetary Restoration Model Version 56.0 — Audit-Corrected External Validation"
RELEASE_STATUS = "INTERNAL_AUDIT_CORRECTED_NOT_SUBMISSION_READY_OSCAR_AND_CARBON_CORE_RESOLUTION_OPEN"

V53_JSON = HERE / "data" / "planetary_restoration_v53_1_results.json"
FAIR_ZIP = HERE / "external_validation_results" / "fair-v2.2.4-results.zip"
HECTOR_ZIP = HERE / "external_validation_results" / "hector-v3.5.0-results.zip"
TRAJECTORY = HERE / "data" / "external_validation_net_co2_trajectory.csv"

# V56 seaweed accounting assumptions.
SEAWEED_AREA_MKM2 = 0.586
SEAWEED_CARBON_FRACTION = 0.30
SEAWEED_ASH_FRACTION_CENTRAL = 0.25
SEAWEED_ASH_FRACTION_LOW = 0.20
SEAWEED_ASH_FRACTION_HIGH = 0.35
HTL_FINISHED_FUEL_YIELD_OF_ASH_FREE_DRY = 0.17
SEAWEED_PROTEIN_FRACTION_DRY = 0.10
SEAWEED_HUMAN_PROTEIN_DIGESTIBILITY_SCREEN = 0.70
PROTEIN_KCAL_PER_G = 4.0
LEGACY_GROSS_ENERGY_UPPER_KCAL_KG = 2000.0
FOOD_DELIVERY_FRACTION = 0.85
DAILY_DIET_SCREEN_KCAL = 2350.0


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


v55 = _load_module("prm_v55_dependency", HERE / "previous_version_v55.py")


def _load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _zip_json(path: Path, member: str) -> Dict:
    with zipfile.ZipFile(path) as z:
        return json.loads(z.read(member).decode("utf-8"))


def _zip_csv_rows(path: Path, member: str) -> List[Dict]:
    with zipfile.ZipFile(path) as z:
        text = z.read(member).decode("utf-8")
    return list(csv.DictReader(text.splitlines()))


def _coerce_row(row: Mapping[str, str]) -> Dict:
    out = {}
    for k, v in row.items():
        if v is None:
            out[k] = None
            continue
        s = str(v).strip()
        if s == "":
            out[k] = None
            continue
        try:
            out[k] = int(s)
            continue
        except ValueError:
            pass
        try:
            out[k] = float(s)
            continue
        except ValueError:
            pass
        out[k] = s
    return out


def _nearest_year(rows: Sequence[Mapping], year: int) -> Dict:
    return min(rows, key=lambda r: abs(int(float(r["year"])) - year))


def external_validation_v56(v53_full: Dict) -> Dict:
    fair_summary = _zip_json(FAIR_ZIP, "fair_v2_2_4_summary.json")
    fair_ts = [_coerce_row(r) for r in _zip_csv_rows(FAIR_ZIP, "fair_v2_2_4_timeseries.csv")]
    hector_summary = _zip_json(HECTOR_ZIP, "hector_v3_5_0_summary.json")
    # member names are archived with the package; inspect robustly for a time-series CSV.
    with zipfile.ZipFile(HECTOR_ZIP) as z:
        hector_csv = next(n for n in z.namelist() if n.lower().endswith(".csv") and "time" in n.lower())
    hector_long = [_coerce_row(r) for r in _zip_csv_rows(HECTOR_ZIP, hector_csv)]
    hector_ts = [{"year": int(r["year"]), "co2_ppm": float(r["value"])} for r in hector_long if r.get("variable") == "CO2_concentration"]

    fair_2026 = _nearest_year(fair_ts, 2026)
    fair_2155 = _nearest_year(fair_ts, 2155)
    fair_2300 = _nearest_year(fair_ts, 2300)
    fair_2400 = _nearest_year(fair_ts, 2400)
    hector_2026 = _nearest_year(hector_ts, 2026)
    hector_2155 = _nearest_year(hector_ts, 2155)
    hector_2190 = _nearest_year(hector_ts, 2190)
    hector_2300 = _nearest_year(hector_ts, 2300)
    hector_min = min(hector_ts, key=lambda r: float(r.get("co2_ppm", r.get("CO2_ppm", 1e9))))

    internal_2026 = float(v55.seaweed_branch.v53.run_v52_case("accelerated", "central", "baseline", 50.0)["durable_carbon"]["rows"][0]["co2_ppm"])
    internal_2155 = 280.0
    fair_p50_2026 = float(fair_2026["co2_p50_ppm"])
    fair_p50_2155 = float(fair_2155["co2_p50_ppm"])
    ppm_gap = fair_p50_2155 - internal_2155
    atmospheric_equiv_gtco2 = ppm_gap * 7.77

    return {
        "classification": "ARCHIVED_EXTERNAL_VALIDATION_FIRST_CLASS_RESULT",
        "publication_gate": "BLOCKING_CARBON_CORE_DIVERGENCE_AND_OSCAR_OPEN",
        "externally_validated_return_to_280_ppm": False,
        "validated_return_year": None,
        "fair": {
            "model": fair_summary.get("model"),
            "version": fair_summary.get("version"),
            "calibration": fair_summary.get("calibration"),
            "configurations": fair_summary.get("configs"),
            "returning_configurations": fair_summary.get("returning_configs"),
            "nonreturn_fraction": fair_summary.get("nonreturn_fraction"),
            "background_nonco2_scenario": fair_summary.get("background_nonco2_scenario"),
            "co2_override": fair_summary.get("co2_override"),
            "co2_p50_ppm_2026": fair_p50_2026,
            "co2_p50_ppm_2155": fair_p50_2155,
            "co2_p50_ppm_2300": float(fair_2300["co2_p50_ppm"]),
            "co2_p50_ppm_2400": float(fair_2400["co2_p50_ppm"]),
            "co2_p05_ppm_2400": float(fair_2400["co2_p05_ppm"]),
            "co2_p95_ppm_2400": float(fair_2400["co2_p95_ppm"]),
            "temperature_p50_c_2155": float(fair_2155.get("temperature_p50_c", fair_2155.get("temp_p50_c"))),
            "temperature_p50_c_2400": float(fair_2400.get("temperature_p50_c", fair_2400.get("temp_p50_c"))),
            "result": "0/841 calibrated-constrained configurations reach <=280 ppm through 2400.",
        },
        "hector": {
            "model": hector_summary.get("model", "Hector"),
            "version": hector_summary.get("version", "3.5.0"),
            "first_le_280_year": hector_summary.get("first_le_280_year"),
            "right_censored_at_2300": hector_summary.get("right_censored_at_2300"),
            "background_nonco2_scenario": hector_summary.get("background_nonco2_scenario"),
            "co2_ppm_2026": float(hector_2026.get("co2_ppm", hector_2026.get("CO2_ppm"))),
            "co2_ppm_2155": float(hector_2155.get("co2_ppm", hector_2155.get("CO2_ppm"))),
            "minimum_co2_ppm": float(hector_min.get("co2_ppm", hector_min.get("CO2_ppm"))),
            "minimum_co2_year": int(float(hector_min["year"])),
            "co2_ppm_2190": float(hector_2190.get("co2_ppm", hector_2190.get("CO2_ppm"))),
            "co2_ppm_2300": float(hector_2300.get("co2_ppm", hector_2300.get("CO2_ppm"))),
            "result": "No <=280 ppm crossing through 2300; carbon concentration rebounds after its mid-22nd-century minimum.",
            "model_role": "Independent SCM comparator. Hector does NOT satisfy V53.1's original OSCAR requirement and is not described as OSCAR.",
        },
        "attribution_diagnostics": {
            "internal_joos_2026_ppm": internal_2026,
            "fair_p50_2026_ppm": fair_p50_2026,
            "initial_condition_offset_internal_minus_fair_p50_ppm": internal_2026 - fair_p50_2026,
            "internal_joos_2155_ppm": internal_2155,
            "fair_p50_2155_ppm": fair_p50_2155,
            "fair_minus_internal_gap_2155_ppm": ppm_gap,
            "gap_atmospheric_concentration_equivalent_gtco2_at_7p77_gt_per_ppm": atmospheric_equiv_gtco2,
            "gap_caution": "The GtCO2 conversion is only an atmospheric concentration-equivalent diagnostic. It is NOT an estimate of extra CDR required because ocean/land sink response is state-dependent.",
            "joos_first_negative_fast_reservoir_year": v53_full["central_joos_diagnostic_summary"]["first_negative_fast_reservoir_year"],
            "joos_first_natural_flux_outgassing_year": v53_full["central_joos_diagnostic_summary"]["first_natural_flux_outgassing_year"],
            "joos_minimum_fast_reservoir_gtc": v53_full["central_joos_diagnostic_summary"]["minimum_fast_reservoir_gtc"],
        },
        "trajectory_extension": {
            "canonical_trajectory_start_year": 2026,
            "canonical_trajectory_end_year": 2183,
            "external_comparison_end_year_fair": 2400,
            "external_comparison_end_year_hector": 2300,
            "extension_rule": "For 2184 onward, the archived benchmark workflow holds the 2183 annual net CO2 flux constant. This is a validation extension, not a V56 emissions forecast.",
            "documentation": "external_validation_workflow/BENCHMARK_EXTENSION_NOTE.md",
        },
        "oscar": {
            "status": "NOT_RUN_IN_ARCHIVED_V56_PACKAGE",
            "requirement": "V53.1 explicitly required official IIASA OSCAR in addition to calibrated/constrained FaIR. Hector is useful independent evidence but is not a silent substitute.",
        },
        "publication_rule": "Do not state 2155, 2188, or any other precise <=280 year as externally validated. The archived external result is non-return within the tested horizons.",
    }


def _area_ha() -> float:
    return SEAWEED_AREA_MKM2 * 1e6 * 100.0


def seaweed_scenario(name: str, biomass_gt_dry_yr: float, ash_fraction: float, status: str,
                     food_share: float = 0.05, fuel_share: float = 0.80,
                     durable_share: float = 0.10, materials_share: float = 0.05) -> Dict:
    assert abs(food_share + fuel_share + durable_share + materials_share - 1.0) < 1e-12
    dry_yield = biomass_gt_dry_yr * 1e9 / _area_ha()
    food_mt = biomass_gt_dry_yr * food_share * 1000.0
    fuel_feed_gt = biomass_gt_dry_yr * fuel_share
    ash_free_fuel_gt = fuel_feed_gt * (1.0 - ash_fraction)
    finished_fuel_mt = ash_free_fuel_gt * 1000.0 * HTL_FINISHED_FUEL_YIELD_OF_ASH_FREE_DRY
    fuel_energy_twh = finished_fuel_mt * 1e9 * 43.0 / 3.6e9
    fossil_equiv = finished_fuel_mt * 3.153 / 1000.0
    avoided = fossil_equiv * 0.70
    gross_protein_mt = food_mt * SEAWEED_PROTEIN_FRACTION_DRY
    digestible_protein_mt = gross_protein_mt * SEAWEED_HUMAN_PROTEIN_DIGESTIBILITY_SCREEN
    protein_energy_floor_kcal_kg = SEAWEED_PROTEIN_FRACTION_DRY * 1000.0 * SEAWEED_HUMAN_PROTEIN_DIGESTIBILITY_SCREEN * PROTEIN_KCAL_PER_G
    delivered_food_kg = food_mt * 1e9 * FOOD_DELIVERY_FRACTION
    coverage_500_floor_m = delivered_food_kg * protein_energy_floor_kcal_kg / (500.0 * 365.0) / 1e6
    coverage_500_gross_upper_m = delivered_food_kg * LEGACY_GROSS_ENERGY_UPPER_KCAL_KG / (500.0 * 365.0) / 1e6
    grid = v55.seaweed_branch.grid_harvester(biomass_gt_dry_yr)
    process_per_gt = 1452.1481266666665 / 1.8526241882352943
    process_twh_eq = fuel_feed_gt * process_per_gt
    durable_gtco2 = biomass_gt_dry_yr * durable_share * SEAWEED_CARBON_FRACTION * (44/12) * 0.90
    return {
        "scenario": name,
        "status": status,
        "farm_area_km2": SEAWEED_AREA_MKM2 * 1e6,
        "dry_yield_t_ha_yr": dry_yield,
        "total_dry_biomass_gt_yr": biomass_gt_dry_yr,
        "ash_fraction_dry": ash_fraction,
        "ash_free_fraction_dry": 1.0 - ash_fraction,
        "food_share": food_share,
        "food_dry_mt_yr": food_mt,
        "gross_protein_mt_yr": gross_protein_mt,
        "digestible_protein_mt_yr_screen": digestible_protein_mt,
        "human_protein_digestibility_screen_fraction": SEAWEED_HUMAN_PROTEIN_DIGESTIBILITY_SCREEN,
        "protein_only_metabolizable_energy_floor_kcal_kg_dry": protein_energy_floor_kcal_kg,
        "legacy_gross_energy_upper_screen_kcal_kg_dry": LEGACY_GROSS_ENERGY_UPPER_KCAL_KG,
        "people_covered_million_at_500_kcal_day_gap_protein_floor": coverage_500_floor_m,
        "people_covered_million_at_500_kcal_day_gap_gross_upper": coverage_500_gross_upper_m,
        "food_energy_interpretation": "V56 does not assign a single metabolizable-energy value to mixed seaweed. Protein-only energy is an intentionally conservative floor; 2,000 kcal/kg is retained only as the older gross/composition upper screen. Species-specific human metabolizable energy is required before calorie capacity can become a primary result.",
        "fuel_feedstock_gt_dry_yr": fuel_feed_gt,
        "ash_free_fuel_feedstock_gt_yr": ash_free_fuel_gt,
        "finished_fuel_yield_fraction_of_ash_free_dry": HTL_FINISHED_FUEL_YIELD_OF_ASH_FREE_DRY,
        "finished_fuel_mt_yr": finished_fuel_mt,
        "finished_fuel_energy_twh_yr": fuel_energy_twh,
        "aviation_energy_twh_yr": fuel_energy_twh * 0.70,
        "heavy_equipment_energy_twh_yr": fuel_energy_twh * 0.25,
        "marine_other_energy_twh_yr": fuel_energy_twh * 0.05,
        "potential_lifecycle_avoided_fossil_gtco2_yr": avoided,
        "process_energy_twh_eq_yr": process_twh_eq,
        "direct_solar_heat_twhth_yr": process_twh_eq * 0.3925465838509317,
        "electricity_h2_twh_yr": process_twh_eq * 0.6074534161490683,
        "grid_harvest_electricity_twh_yr": grid["global_harvest_electricity_twh_yr"],
        "grid_harvester_fleet_units": grid["required_global_fleet_units"],
        "durable_seaweed_storage_gtco2_yr_inside_bicrs": durable_gtco2,
    }


def seaweed_v56(v55_result: Dict) -> Dict:
    ns = v55_result["current_resource_screens"]["seaweed_v53_nutrient_screen"]
    nutrient_closed = float(ns["nutrient_supported_biomass_without_other_sources_gt_yr"])
    ecological_dry_yield = 1546.0 / 1000.0 / SEAWEED_CARBON_FRACTION
    ecological_biomass = _area_ha() * ecological_dry_yield / 1e9
    managed_full = float(ns["area_yield_potential_gt_dry_yr"])
    scenarios = [
        seaweed_scenario(
            "nutrient_closed_central", nutrient_closed, SEAWEED_ASH_FRACTION_CENTRAL,
            "V56_PRIMARY_SEAWEED_PHYSICAL_SCREEN_WITH_ONLY_EXPLICITLY_CREDITED_EUTROPHIC_N_AND_P"
        ),
        seaweed_scenario(
            "ecosystem_accumulation_benchmark", ecological_biomass, SEAWEED_ASH_FRACTION_CENTRAL,
            "EXTERNAL_ECOLOGICAL_BENCHMARK_NOT_A_FARM_YIELD_CAP_OR_PRIMARY_PRODUCTION_CASE"
        ),
        seaweed_scenario(
            "managed_nutrient_full_geometric_potential", managed_full, SEAWEED_ASH_FRACTION_CENTRAL,
            "HIGH_ENGINEERING_SCENARIO_REQUIRES_REGIONAL_DEMONSTRATION_OF_SUPPLEMENTAL_OR_NATURAL_NUTRIENT_FLUX"
        ),
    ]
    return {
        "classification": "NUTRIENT_CONSTRAINED_SCENARIO_HIERARCHY_WITH_EXPLICIT_ASH_AND_FOOD_ENERGY_BOUNDARY",
        "primary_scenario": "nutrient_closed_central",
        "scenarios": scenarios,
        "nutrient_mass_balance": ns,
        "managed_full_potential_supplemental_n_mt_yr": ns["supplemental_or_natural_n_needed_for_full_potential_mt_yr"],
        "managed_full_potential_supplemental_p_mt_yr": ns["supplemental_or_natural_p_needed_for_full_potential_mt_yr"],
        "ash_sensitivity": [
            {"ash_fraction": SEAWEED_ASH_FRACTION_LOW, "effective_17pct_yield_on_total_dry_fraction": HTL_FINISHED_FUEL_YIELD_OF_ASH_FREE_DRY*(1-SEAWEED_ASH_FRACTION_LOW)},
            {"ash_fraction": SEAWEED_ASH_FRACTION_CENTRAL, "effective_17pct_yield_on_total_dry_fraction": HTL_FINISHED_FUEL_YIELD_OF_ASH_FREE_DRY*(1-SEAWEED_ASH_FRACTION_CENTRAL)},
            {"ash_fraction": SEAWEED_ASH_FRACTION_HIGH, "effective_17pct_yield_on_total_dry_fraction": HTL_FINISHED_FUEL_YIELD_OF_ASH_FREE_DRY*(1-SEAWEED_ASH_FRACTION_HIGH)},
        ],
        "ecological_benchmark_note": "The 1,546 kgC/ha/yr meta-analysis biomass-accumulation median is a context-dependent ecosystem-service benchmark, not a direct cultivated harvest-yield cap. V56 reports it separately rather than using it to prove or disprove 25 t dry/ha/yr farm productivity.",
    }


def fisheries_v56() -> Dict:
    return {
        "classification": "LITERATURE_BOUNDED_FISHERIES_RECOVERY_SCREEN_NOT_STOCK_BY_STOCK_GLOBAL_FORECAST",
        "observed_reference": {
            "biologically_sustainable_assessed_stock_fraction_2023": 0.624,
            "landings_from_biologically_sustainable_assessed_stocks_fraction_2023": 0.726,
            "source": "FAO SOFIA 2026 reference retained from the V50/V53 lineage.",
        },
        "management_recovery_screen": {
            "modeled_fisheries_count": 4713,
            "median_recovery_years_under_effective_reform": 10.0,
            "modeled_biologically_healthy_fraction_by_2050": 0.98,
            "status": "LITERATURE_SCREEN",
            "caution": "A global bioeconomic literature scenario; not a prediction that every stock or ecosystem recovers in ten years.",
        },
        "long_lived_and_ecosystem_context": {
            "marine_reserve_age_signal_years": 15.0,
            "reef_fish_recovery_context_years": 35.0,
            "status": "CONTEXT_ONLY",
        },
        "seaweed_coupling": {
            "farm_habitat_footprint_km2_managed_full": 586000.0,
            "coculture_is_counted_as_wild_fish_recovery": False,
            "rule": "Seaweed habitat/co-culture may relieve fishing pressure or provide habitat in scenarios, but cultured edible biomass is never added to wild-stock recovery metrics.",
        },
        "publication_rule": "Use ~10 years only as a managed-stock median sensitivity and 2050 as a literature planning horizon; do not claim global ecosystem restoration by a single year.",
    }


def restored_human_system_screens() -> Dict:
    return {
        "Human_Welfare_Floor": {
            "status": "RESTORED_SCREEN_UPDATED_V56",
            "rows": [
                {"constraint":"Dietary energy","unit":"kcal/person/day","legacy_minimum":2300,"v56_central_consumption_screen":2350,"coverage_target":0.99,"caution":"Calories alone do not prove micronutrient adequacy."},
                {"constraint":"Protein","unit":"g/person/day","minimum":50,"legacy_central":65,"coverage_target":0.99,"caution":"Age/sex distributions require disaggregation."},
                {"constraint":"Safe municipal water","unit":"L/person/day","minimum":50,"legacy_central":100,"coverage_target":0.99,"caution":"Regional climate and availability vary."},
            ],
        },
        "Demographics": {
            "status":"RESTORED_SCENARIO",
            "population_billion":{"reference":8.2,"planning":10.3,"low":9.5,"legacy_high":12.55},
            "life_expectancy_years":{"reference":73,"planning_target":82,"low":78,"high":85},
            "total_fertility_rate":{"reference":2.25,"planning":2.1,"low":1.75,"high":2.25},
            "planning_infrastructure_at_10p3b":{"doctors_million":30.9,"hospital_beds_million":30.9,"teachers_million":103.0,"housing_floor_area_billion_m2":309.0,"reliable_electricity_twh_yr":66950.0},
            "caution":"Targets and workforce screens, not demographic forecasts produced by V56.",
        },
        "Global_Economics": {
            "status":"RESTORED_SCENARIO",
            "population_billion":{"low":9.5,"central":10.3,"high":12.55},
            "real_gdp_usd_person_yr":{"low":22000,"central":30000,"high":40000},
            "welfare_basic_services_usd_person_yr":{"low":11000,"central":13000,"high":16000},
            "caution":"Decent-living affordability screen; not a general-equilibrium forecast.",
        },
        "Industry_Materials": {
            "status":"RESTORED_SCREEN",
            "rows":[
                {"material":"Steel","demand_kg_person_yr":250,"recycled_share":0.70,"virgin_kg_person_yr":75,"global_demand_mt_yr_at_10p3b":2575,"virgin_demand_mt_yr":772.5,"low_carbon_share":0.95,"economic_cost_usd_t":850},
                {"material":"Cement/concrete binder","demand_kg_person_yr":300,"recycled_share":0.35,"virgin_kg_person_yr":195,"global_demand_mt_yr_at_10p3b":3090,"virgin_demand_mt_yr":2008.5,"low_carbon_share":0.95,"economic_cost_usd_t":140},
                {"material":"Aluminium","demand_kg_person_yr":30,"recycled_share":0.70,"virgin_kg_person_yr":9,"global_demand_mt_yr_at_10p3b":309,"virgin_demand_mt_yr":92.7,"low_carbon_share":0.95,"economic_cost_usd_t":2500},
            ],
            "caution":"Legacy material metabolism screen; not a current supplier-constrained buildout model.",
        },
        "Population_Literature": {
            "status":"RESTORED_CONTEXT",
            "rows":[
                {"case":"UN WPP planning peak","population_billion":10.3,"meaning":"Demographic planning reference, not carrying capacity."},
                {"case":"Gerten transformed terrestrial food-system context","population_billion":10.2,"meaning":"Literature context within four assessed terrestrial planetary boundaries after major transformation."},
                {"case":"Legacy v12 vegetarian+fish Monte Carlo median","population_billion":12.20,"meaning":"Historical model scenario; not empirical Earth capacity."},
                {"case":"Legacy optimized omnivore","population_billion":11.24,"meaning":"Historical model scenario."},
                {"case":"Legacy vegetarian/aquatic high case","population_billion":12.55,"meaning":"Historical model scenario."},
                {"case":"Legacy plant-based upper screen","population_billion":13.0,"meaning":"Historical upper scenario."},
                {"case":"Legacy energy-only screen","population_billion":14.7,"meaning":"Annual energy balance only; not integrated carrying capacity."},
            ],
            "publication_rule":"V56 does not assert one immutable maximum human population on Earth.",
        },
        "Monetary_System_Risks": {
            "status":"RESTORED_REQUIRED_FUNCTIONS",
            "rows":[
                {"function":"Payments/settlement","blockchain_replacement":"YES","institution_still_required":"YES","safeguard":"Redundant global nodes + offline recovery"},
                {"function":"Credit underwriting/lending","blockchain_replacement":"PARTLY","institution_still_required":"YES","safeguard":"Capital rules + competitive credit markets"},
                {"function":"Deposit/liquidity insurance","blockchain_replacement":"PARTLY","institution_still_required":"YES","safeguard":"Ring-fenced reserve + emergency liquidity governance"},
                {"function":"AML/KYC/fraud/cybersecurity","blockchain_replacement":"PARTLY","institution_still_required":"YES","safeguard":"Financial-integrity and cybersecurity governance"},
            ],
        },
        "Diet_Carbon_v19": {
            "status":"RESTORED_HISTORICAL_SCREEN_CLIMATE_DATES_SUPERSEDED",
            "rows":[
                {"diet":"Optimized omnivore","population_capacity_billion_legacy":11.24,"diet_enabled_restoration_stock_gtco2_legacy":0,"status":"HISTORICAL_SCENARIO"},
                {"diet":"EAT-Lancet-like","population_capacity_billion_legacy":11.8,"diet_enabled_restoration_stock_gtco2_legacy":166,"status":"HISTORICAL_SCENARIO"},
                {"diet":"Vegetarian + dairy/eggs + aquatic","population_capacity_billion_legacy":12.55,"diet_enabled_restoration_stock_gtco2_legacy":220,"status":"HISTORICAL_SCENARIO"},
            ],
            "publication_rule":"Old v19 CO2-return dates are not propagated because the V56 external carbon-cycle validation supersedes them.",
        },
    }


def headline_v56(v53_full: Dict, ext: Dict, sw: Dict, fisheries: Dict) -> Dict:
    ens = v53_full["full_advanced_sensitivity_ensemble"]
    h = v53_full["headline"]
    primary_sw = next(r for r in sw["scenarios"] if r["scenario"] == "nutrient_closed_central")
    return {
        "external_validation_primary_result": "280 ppm NOT REACHED within archived FaIR 2400 horizon or Hector 2300 horizon",
        "externally_validated_return_year": None,
        "fair_returning_configurations": ext["fair"]["returning_configurations"],
        "fair_total_configurations": ext["fair"]["configurations"],
        "fair_p50_co2_ppm_2400": ext["fair"]["co2_p50_ppm_2400"],
        "hector_minimum_co2_ppm": ext["hector"]["minimum_co2_ppm"],
        "hector_minimum_year": ext["hector"]["minimum_co2_year"],
        "internal_v53_ensemble_conditional_median_year_context_only": ens["return_year_p50_conditional"],
        "internal_v53_ensemble_conditional_p05_year_context_only": ens["return_year_p05_conditional"],
        "internal_v53_ensemble_conditional_p95_year_context_only": ens["return_year_p95_conditional"],
        "internal_joos_accelerated_crossing_year_diagnostic_only": h["first_below_280_year"],
        "internal_joos_accelerated_percentile_rank_of_returning_draws": h["accelerated_design_percentile_rank_among_returning"],
        "internal_residual_warming_at_nominal_280_c": h["warming_at_280_c"],
        "internal_residual_nonco2_forcing_at_nominal_280_w_m2": h["residual_forcing_at_280_nonco2_w_m2"],
        "v53_grid_default_failed_cases": v53_full["energy_and_grid"]["default_failed_case_count"],
        "v53_grid_default_case_count": v53_full["energy_and_grid"]["default_case_count"],
        "v53_monetary_liquidity_failed_cases": len(v53_full["monetary_liquidity_stress"]["failed_cases"]),
        "v53_monetary_liquidity_total_cases": len(v53_full["monetary_liquidity_stress"]["rows"]),
        "v56_primary_seaweed_biomass_gt_dry_yr": primary_sw["total_dry_biomass_gt_yr"],
        "v56_primary_seaweed_finished_fuel_twh_yr": primary_sw["finished_fuel_energy_twh_yr"],
        "v56_primary_seaweed_digestible_protein_mt_yr_screen": primary_sw["digestible_protein_mt_yr_screen"],
        "fisheries_recovery_reporting": "10-year managed-stock median sensitivity; 2050 literature healthy-stock horizon; no single global ecosystem recovery date",
        "submission_status": "BLOCKED pending carbon-core resolution and/or explicit reframing, plus the originally required OSCAR run or a documented decision to replace that gate.",
    }


def run_v56() -> Dict:
    v55_result = v55.run_v55()
    v53_full = _load_json(V53_JSON)
    ext = external_validation_v56(v53_full)
    sw = seaweed_v56(v55_result)
    fish = fisheries_v56()
    human = restored_human_system_screens()
    return {
        "model_version": MODEL_VERSION,
        "release_label": RELEASE_LABEL,
        "release_status": RELEASE_STATUS,
        "classification": "AUDIT_CORRECTED_INTEGRATED_SCREENING_MODEL_EXTERNAL_VALIDATION_FIRST",
        "headline": headline_v56(v53_full, ext, sw, fish),
        "external_validation_v56": ext,
        "v53_1_full_core": v53_full,
        "v55_integrated_architecture": v55_result,
        "seaweed_v56": sw,
        "fisheries_v56": fish,
        "restored_human_system_screens": human,
        "accounting_rules": {
            "joos_role": "DIAGNOSTIC_ONLY",
            "fair_role": "PRIMARY_ARCHIVED_EXTERNAL_CARBON_CYCLE_VALIDATION",
            "hector_role": "INDEPENDENT_COMPARATOR_NOT_OSCAR",
            "oscar_status": "OPEN",
            "seaweed_working_stocks_are_durable_cdr": False,
            "seaweed_durable_storage_stacks_on_existing_bicrs": False,
            "restored_electricity_terms_auto_added_to_v53_external_base": False,
            "cultured_fish_counts_as_wild_stock_recovery": False,
            "legacy_seaweed_2000_kcal_kg_is_metabolizable_energy": False,
        },
    }


def _write_csv(path: Path, rows: Sequence[Mapping]) -> None:
    if not rows:
        return
    keys: List[str] = []
    for row in rows:
        for k in row:
            if k not in keys:
                keys.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for row in rows:
            q = {}
            for k in keys:
                v = row.get(k)
                q[k] = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
            w.writerow(q)


def write_outputs(result: Dict) -> None:
    data = HERE / "data"
    data.mkdir(exist_ok=True)
    (data / "planetary_restoration_v56_results.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _write_csv(data / "v56_seaweed_scenarios.csv", result["seaweed_v56"]["scenarios"])
    _write_csv(data / "v56_fisheries_screen.csv", [
        {"metric":"observed_sustainable_stock_fraction_2023","value":result["fisheries_v56"]["observed_reference"]["biologically_sustainable_assessed_stock_fraction_2023"]},
        {"metric":"sustainable_landings_fraction_2023","value":result["fisheries_v56"]["observed_reference"]["landings_from_biologically_sustainable_assessed_stocks_fraction_2023"]},
        {"metric":"managed_stock_median_recovery_years","value":result["fisheries_v56"]["management_recovery_screen"]["median_recovery_years_under_effective_reform"]},
        {"metric":"modeled_healthy_fraction_by_2050","value":result["fisheries_v56"]["management_recovery_screen"]["modeled_biologically_healthy_fraction_by_2050"]},
    ])
    _write_csv(data / "v56_external_validation_summary.csv", [
        {"model":"FaIR 2.2.4","crossing":"none <=280 by 2400","configs":result["external_validation_v56"]["fair"]["configurations"],"returning":result["external_validation_v56"]["fair"]["returning_configurations"],"co2_2155_ppm":result["external_validation_v56"]["fair"]["co2_p50_ppm_2155"],"co2_horizon_ppm":result["external_validation_v56"]["fair"]["co2_p50_ppm_2400"]},
        {"model":"Hector 3.5.0","crossing":"none <=280 by 2300","configs":1,"returning":0,"co2_2155_ppm":result["external_validation_v56"]["hector"]["co2_ppm_2155"],"co2_horizon_ppm":result["external_validation_v56"]["hector"]["co2_ppm_2300"]},
    ])
    # Propagate the adverse V53.1 blocks as standalone machine-readable files.
    v53 = result["v53_1_full_core"]
    for key in ("energy_and_grid", "monetary_liquidity_stress", "degraded_collection_physics", "central_joos_diagnostic_summary", "scenario_matrix", "external_validation", "primary_screen_headline"):
        (data / f"v53_1_restored_{key}.json").write_text(json.dumps(v53[key], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _write_csv(data / "v56_v53_grid_adequacy_cases.csv", v53["energy_and_grid"]["default_adequacy_rows"])
    _write_csv(data / "v56_v53_monetary_liquidity_cases.csv", v53["monetary_liquidity_stress"]["rows"])
    _write_csv(data / "v56_v53_degraded_collection_cases.csv", v53["degraded_collection_physics"]["rows"])
    hs = result["restored_human_system_screens"]
    _write_csv(data / "v56_human_welfare_floor.csv", hs["Human_Welfare_Floor"]["rows"])
    _write_csv(data / "v56_industry_materials.csv", hs["Industry_Materials"]["rows"])
    _write_csv(data / "v56_population_context.csv", hs["Population_Literature"]["rows"])
    _write_csv(data / "v56_monetary_system_risks.csv", hs["Monetary_System_Risks"]["rows"])
    _write_csv(data / "v56_diet_carbon_v19_historical.csv", hs["Diet_Carbon_v19"]["rows"])


def run_tests(result: Dict) -> None:
    ext = result["external_validation_v56"]
    assert ext["fair"]["configurations"] == 841
    assert ext["fair"]["returning_configurations"] == 0
    assert ext["fair"]["co2_p50_ppm_2400"] > 290
    assert ext["hector"]["first_le_280_year"] is None
    assert ext["hector"]["minimum_co2_ppm"] > 295
    assert result["accounting_rules"]["joos_role"] == "DIAGNOSTIC_ONLY"
    v53 = result["v53_1_full_core"]
    for key in ("energy_and_grid", "monetary_liquidity_stress", "degraded_collection_physics", "central_joos_diagnostic_summary", "scenario_matrix", "external_validation", "primary_screen_headline"):
        assert key in v53
    assert v53["energy_and_grid"]["default_failed_case_count"] == 4
    assert len(v53["monetary_liquidity_stress"]["failed_cases"]) == 3
    sw = result["seaweed_v56"]
    central = next(x for x in sw["scenarios"] if x["scenario"] == "nutrient_closed_central")
    full = next(x for x in sw["scenarios"] if x["scenario"] == "managed_nutrient_full_geometric_potential")
    assert 0.25 < central["total_dry_biomass_gt_yr"] < 0.26
    assert abs(full["total_dry_biomass_gt_yr"] - 1.465) < 1e-9
    assert central["ash_fraction_dry"] == 0.25
    assert central["finished_fuel_yield_fraction_of_ash_free_dry"] == 0.17
    assert central["protein_only_metabolizable_energy_floor_kcal_kg_dry"] < central["legacy_gross_energy_upper_screen_kcal_kg_dry"]
    assert result["accounting_rules"]["legacy_seaweed_2000_kcal_kg_is_metabolizable_energy"] is False
    assert result["fisheries_v56"]["seaweed_coupling"]["coculture_is_counted_as_wild_fish_recovery"] is False
    for key in ("Human_Welfare_Floor", "Demographics", "Global_Economics", "Industry_Materials", "Population_Literature", "Monetary_System_Risks", "Diet_Carbon_v19"):
        assert key in result["restored_human_system_screens"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tests", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()
    result = run_v56()
    run_tests(result)
    if not args.no_write:
        write_outputs(result)
    if args.tests:
        print("V56 AUDIT-CORRECTED TESTS PASSED")
    print(json.dumps(result["headline"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
