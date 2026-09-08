#!/usr/bin/env python3
"""Planetary Restoration Model V58 — coral-reef recovery + canonical sink-response curve.

V58 extends V57 in two directions:

1. It adds a literature-bounded coral-reef recovery module, including a Great
   Barrier Reef (GBR) state screen using AIMS 2024/2025/2026 hard-coral-cover
   observations and explicit thermal-disturbance gates.  The module separates
   recovery of surviving colonies, recovery of hard-coral cover, and recovery
   of ecological/community structure.  It does NOT claim that a global-mean
   temperature pathway directly predicts GBR marine heatwaves.

2. It closes the next referee bookkeeping items from V57: the interval-dependent
   21% extension-regime response headline is replaced by a canonical cumulative
   FaIR drawdown-vs-cumulative-net-removal curve and rolling 20-year diagnostic;
   seaweed ash is balanced across all biomass allocations; durable seaweed CDR
   is priced against the BiCRS tranche it substitutes for; V53.1 internal dates
   are explicitly marked diagnostic-only in the current JSON; and the FaIR
   splice issue is narrowed to the still-open historical/calibration alignment
   question rather than incorrectly attributing the timebound-2026 mismatch to
   the 2026 AFOLU override.

Official zero-background-non-CO2 FaIR, inverse FaIR removal-schedule and OSCAR
runs remain open.  No unexecuted external experiment is presented as a result.
"""
from __future__ import annotations

import argparse
import copy
import csv
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Mapping, Sequence

HERE = Path(__file__).resolve().parent
MODEL_VERSION = "58.0"
RELEASE_LABEL = "Planetary Restoration Model Version 58.0 — Reef Recovery + Canonical Sink Response"
RELEASE_STATUS = "REEF_RECOVERY_ADDED_REFEREE_BOOKKEEPING_CLOSED_EXTERNAL_FAIR_INVERSION_OSCAR_OPEN"

# Coral-reef evidence anchors.
AIMS_GBR_2025_26 = "https://www.aims.gov.au/monitoring-great-barrier-reef/gbr-condition-summary-2025-26"
AIMS_GBR_2024_25 = "https://www.aims.gov.au/monitoring-great-barrier-reef/gbr-condition-summary-2024-25"
GBRMPA_BLEACHING = "https://www2.gbrmpa.gov.au/learn/reef-health/coral-bleaching"
AIMS_BLEACHING = "https://www.aims.gov.au/research-topics/environmental-issues/coral-bleaching/what-coral-bleaching"
GBR_PALM_ISLANDS_RECOVERY = "https://www.nature.com/articles/s41598-018-29608-y"
GBR_ECOSYSTEM_RESTRUCTURING = "https://www.nature.com/articles/s41586-018-0359-9"
CORAL_RECOVERY_VARIABILITY = "https://www.nature.com/articles/s41598-018-25414-8"
AIMS_CALCIFICATION = "https://www.aims.gov.au/docs/research/climate-change/declining-coral-growth.html"
CORAL_RESTORATION_ACCRETION = "https://www.nature.com/articles/s41598-025-04818-3"
NOAA_GLOBAL_CO2 = "https://www.gml.noaa.gov/ccgg/trends/global.html"

# Great Barrier Reef regional hard-coral cover (%), taken from AIMS LTMP.
GBR_COVER_2024 = {"Northern": 39.8, "Central": 33.2, "Southern": 38.9}
GBR_COVER_2025 = {"Northern": 30.0, "Central": 28.6, "Southern": 26.9}
GBR_COVER_2026 = {"Northern": 35.1, "Central": 31.6, "Southern": 26.4}
GBR_RECENT_MASS_BLEACHING_YEARS = [2016, 2017, 2020, 2022, 2024, 2025]

# Recovery-window screens.  The 10-15 year cover-reestablishment window is the
# official GBR Authority/AIMS literature-bounded anchor under minimal disturbance.
GBR_COVER_RECOVERY_YEARS_LOW = 10
GBR_COVER_RECOVERY_YEARS_HIGH = 15
GBR_COVER_RECOVERY_YEARS_CENTRAL = 12
# Community/structural restoration is deliberately a model screen, not a single
# observed GBR forecast. Literature shows anything from rapid site recovery to
# several decades, and community composition can remain shifted after cover rises.
REEF_ECOLOGICAL_RECOVERY_YEARS_LOW = 15
REEF_ECOLOGICAL_RECOVERY_YEARS_CENTRAL = 20
REEF_ECOLOGICAL_RECOVERY_YEARS_HIGH = 30

# Seaweed allocation inherited from the active V57 primary architecture.
SEAWEED_FOOD_SHARE = 0.05
SEAWEED_FUEL_SHARE = 0.80
SEAWEED_DURABLE_SHARE = 0.10
SEAWEED_MATERIALS_SHARE = 0.05
SEAWEED_ASH_FRACTION = 0.25
SEAWEED_TOTAL_DRY_CARBON_FRACTION = 0.30
ATMOSPHERIC_GTCO2_PER_PPM = 7.77
BICRS_START_USD_TCO2 = 160.0
BICRS_FLOOR_USD_TCO2 = 80.0


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


v57 = _load_module("prm_v57_dependency", HERE / "previous_version_v57.py")


def canonical_sink_response_v58() -> Dict:
    """Replace interval-choice headline with canonical cumulative response curve.

    Internal row Y is post-year-Y flux; FaIR timebound Y+1 is therefore used for
    the post-flux concentration.  The curve begins in the first negative-net-CO2
    year (2039) and ends after the final canonical 2183 flux (timebound 2184).
    """
    traj = v57._trajectory_rows()
    fair = v57._fair_timeseries()
    fair_by = {int(round(r["year"])): r for r in fair}
    first_negative = next(int(r["year"]) for r in traj if float(r["net_co2_gtco2"]) < 0)
    baseline_ppm = float(fair_by[first_negative]["co2_p50_ppm"])

    rows=[]
    cumulative_net_removal=0.0
    by_year={int(r["year"]): r for r in traj}
    for y in range(first_negative, max(by_year)+1):
        r=by_year[y]
        cumulative_net_removal += -float(r["net_co2_gtco2"])
        if cumulative_net_removal <= 0 or (y+1) not in fair_by:
            continue
        post_ppm=float(fair_by[y+1]["co2_p50_ppm"])
        drawdown=baseline_ppm-post_ppm
        atm_mass=drawdown*ATMOSPHERIC_GTCO2_PER_PPM
        apparent=atm_mass/cumulative_net_removal if cumulative_net_removal>0 else None
        rows.append({
            "emissions_through_year":y,
            "fair_timebound_after_flux":y+1,
            "cumulative_net_removal_gtco2":cumulative_net_removal,
            "fair_p50_cumulative_drawdown_ppm":drawdown,
            "atmospheric_mass_decrease_equivalent_gtco2":atm_mass,
            "cumulative_apparent_atmospheric_response_fraction":apparent,
        })

    rolling=[]
    window=20
    for end in range(first_negative+window-1, max(by_year)+1):
        start=end-window+1
        removal=sum(-float(by_year[y]["net_co2_gtco2"]) for y in range(start,end+1))
        if removal <= 0 or start not in fair_by or (end+1) not in fair_by:
            continue
        ppm_drop=float(fair_by[start]["co2_p50_ppm"])-float(fair_by[end+1]["co2_p50_ppm"])
        frac=ppm_drop*ATMOSPHERIC_GTCO2_PER_PPM/removal
        rolling.append({
            "window_start_emissions_year":start,
            "window_end_emissions_year":end,
            "fair_start_timebound":start,
            "fair_end_timebound":end+1,
            "window_net_removal_gtco2":removal,
            "window_fair_p50_drawdown_ppm":ppm_drop,
            "rolling_20y_apparent_atmospheric_response_fraction":frac,
        })

    final=rows[-1]
    roll_final=rolling[-1]
    return {
        "classification":"CANONICAL_CUMULATIVE_FAIR_RESPONSE_DIAGNOSTIC",
        "first_negative_net_co2_year":first_negative,
        "canonical_last_emissions_year":max(by_year),
        "canonical_post_flux_timebound":max(by_year)+1,
        "cumulative_curve":rows,
        "rolling_20_year":rolling,
        "canonical_endpoint":final,
        "canonical_endpoint_cumulative_apparent_response_fraction":final["cumulative_apparent_atmospheric_response_fraction"],
        "canonical_endpoint_rolling_20y_response_fraction":roll_final["rolling_20y_apparent_atmospheric_response_fraction"],
        "old_v57_extension_regime_21pct_is_current_headline":False,
        "interpretation":"The cumulative curve is the primary diagnostic because it avoids arbitrary interval selection. The rolling 20-year fraction is secondary and shows the late canonical slowdown. Values are pathwise diagnostics, not a universal marginal derivative or a FaIR inversion.",
    }


def fair_splice_diagnostic_v58(base: Dict) -> Dict:
    """Narrow what can and cannot explain the historical concentration mismatch."""
    fair=v57._fair_timeseries()
    fair_by={int(round(r["year"])):r for r in fair}
    noaa_may_2026=428.73
    fair_tb_2026=float(fair_by[2026]["co2_p50_ppm"])
    fair_tb_2027=float(fair_by[2027]["co2_p50_ppm"])
    return {
        "status":"PARTIALLY_CLOSED_CAUSALLY_OFFICIAL_RESTART_STILL_REQUIRED",
        "noaa_global_monthly_mean_may_2026_ppm":noaa_may_2026,
        "fair_p50_timebound_2026_ppm":fair_tb_2026,
        "reported_difference_may_monthly_minus_fair_timebound_2026_ppm":noaa_may_2026-fair_tb_2026,
        "fair_p50_timebound_2027_ppm":fair_tb_2027,
        "co2_override_behavior":"From 2026 onward the archived runner maps the full V53.1 net CO2 flux to CO2 FFI and sets CO2 AFOLU to zero.",
        "causal_finding":"FaIR timebound 2026 is the state before the 2026 override flux is applied, so zeroing CO2 AFOLU from 2026 cannot be the cause of the timebound-2026 concentration difference itself. It can affect 2027 onward. The remaining mismatch therefore belongs to calendar/timebound alignment and/or the calibrated historical emissions/concentration setup and must be resolved in the official restart.",
        "open_restart_checks":[
            "Compare observed concentration to the correctly dated FaIR timebound or initialize the override run from a common observed concentration state.",
            "Preserve total CO2 while testing FFI/AFOLU allocation at the splice so the carbon-cycle state is not changed merely by bookkeeping.",
            "Run the already-planned zero-background-non-CO2 experiment from the same common state.",
        ],
        "source_urls":[NOAA_GLOBAL_CO2],
    }


def seaweed_v58(base: Dict) -> Dict:
    sw=copy.deepcopy(base["seaweed_v57"])
    biomass_gt=float(sw["primary_biomass_gt_dry_yr"])
    biomass_mt=biomass_gt*1000.0

    allocations={
        "food":SEAWEED_FOOD_SHARE,
        "fuel_feedstock":SEAWEED_FUEL_SHARE,
        "durable_storage":SEAWEED_DURABLE_SHARE,
        "materials_feed":SEAWEED_MATERIALS_SHARE,
    }
    ash_total_mt=biomass_mt*SEAWEED_ASH_FRACTION
    ash_rows=[]
    for stream,share in allocations.items():
        dry_mt=biomass_mt*share
        ash_mt=dry_mt*SEAWEED_ASH_FRACTION
        ash_rows.append({
            "allocation_stream":stream,
            "allocation_share":share,
            "dry_biomass_mt_yr":dry_mt,
            "ash_mt_yr":ash_mt,
            "ash_free_organic_mt_yr":dry_mt-ash_mt,
        })

    organic_fraction=1.0-SEAWEED_ASH_FRACTION
    implied_c_fraction_of_organic=SEAWEED_TOTAL_DRY_CARBON_FRACTION/organic_fraction

    # The V56 primary scenario already carried the durable carbon result, which V57
    # inherited as architecture but did not price.  Use that exact primary screen.
    sw56_primary=next(r for r in base["external_validation"].get("_unused",[]) if False) if False else None
    # Re-load the active V56 primary through V57's dependency chain.
    v56_result=v57.v56.run_v56()
    v56_primary=next(r for r in v56_result["seaweed_v56"]["scenarios"] if r["scenario"]=="nutrient_closed_central")
    durable_co2_mt=float(v56_primary["durable_seaweed_storage_gtco2_yr_inside_bicrs"])*1000.0
    durable_dry_mt=biomass_mt*SEAWEED_DURABLE_SHARE

    durable_cost=[]
    for row in sw["farmgate_economics"]:
        case=row["case"]
        cost_t=float(row["farmgate_total_usd_per_dry_t"])
        annual_cost_bn=durable_dry_mt*1e6*cost_t/1e9
        cost_per_tco2=annual_cost_bn*1e9/(durable_co2_mt*1e6)
        durable_cost.append({
            "farmgate_case":case,
            "farmgate_usd_per_dry_t":cost_t,
            "durable_dry_stream_mt_yr":durable_dry_mt,
            "durable_storage_mtco2_yr_inside_bicrs":durable_co2_mt,
            "annual_farmgate_cost_usd_bn":annual_cost_bn,
            "farmgate_cost_usd_per_tco2_durable":cost_per_tco2,
            "multiple_of_bicrs_160_start":cost_per_tco2/BICRS_START_USD_TCO2,
            "multiple_of_bicrs_80_floor":cost_per_tco2/BICRS_FLOOR_USD_TCO2,
        })

    conversion=dry_t_per_tco2=durable_dry_mt/durable_co2_mt
    break_even_160=BICRS_START_USD_TCO2/conversion
    break_even_80=BICRS_FLOOR_USD_TCO2/conversion

    sw["classification"]="V58_FULL_ASH_BALANCE_DURABLE_STORAGE_ECONOMICS_PROTEIN_FIRST"
    sw["ash_allocation_mass_balance"]={
        "total_primary_dry_biomass_mt_yr":biomass_mt,
        "ash_fraction_of_total_dry":SEAWEED_ASH_FRACTION,
        "total_ash_mt_yr":ash_total_mt,
        "allocation_rows":ash_rows,
        "food_stream_ash_mt_yr":next(r["ash_mt_yr"] for r in ash_rows if r["allocation_stream"]=="food"),
        "fuel_stream_ash_mt_yr":next(r["ash_mt_yr"] for r in ash_rows if r["allocation_stream"]=="fuel_feedstock"),
        "durable_stream_ash_mt_yr":next(r["ash_mt_yr"] for r in ash_rows if r["allocation_stream"]=="durable_storage"),
        "materials_stream_ash_mt_yr":next(r["ash_mt_yr"] for r in ash_rows if r["allocation_stream"]=="materials_feed"),
        "food_safety_interpretation":"The food-grade dry stream carries the same 25% ash screen unless species/process data justify another value; this makes iodine, sodium and trace-element controls a quantified mass-flow issue rather than only a caution string.",
        "carbon_basis_reconciliation":{
            "carbon_fraction_of_total_dry":SEAWEED_TOTAL_DRY_CARBON_FRACTION,
            "ash_fraction_of_total_dry":SEAWEED_ASH_FRACTION,
            "implied_carbon_fraction_of_ash_free_organic":implied_c_fraction_of_organic,
            "interpretation":"0.30 C per total dry mass and 25% ash are internally compatible if ash-free organic matter is about 40% carbon by mass. This is a basis reconciliation, not a species-specific measurement.",
        },
    }
    sw["durable_storage_economics"]={
        "classification":"FARMGATE_ONLY_COST_COMPARISON_BEFORE_TRANSPORT_SINKING_MRV",
        "durable_dry_stream_mt_yr":durable_dry_mt,
        "durable_storage_mtco2_yr_inside_bicrs":durable_co2_mt,
        "farmgate_cases":durable_cost,
        "bicrs_reference_start_usd_tco2":BICRS_START_USD_TCO2,
        "bicrs_reference_floor_usd_tco2":BICRS_FLOOR_USD_TCO2,
        "break_even_farmgate_usd_per_dry_t_vs_bicrs_start":break_even_160,
        "break_even_farmgate_usd_per_dry_t_vs_bicrs_floor":break_even_80,
        "land_relief_mha_unpriced":2.93,
        "design_rule":"Do not automatically substitute seaweed durable storage for BiCRS in the central or stress farmgate cases. Favorable sites can compete with unlearned BiCRS but not with the $80/tCO2 floor before transport/sinking/MRV. Retain the durable stream only where measured full-chain cost plus valued co-benefits beats the displaced alternative.",
    }
    return sw


def coral_reef_recovery_v58() -> Dict:
    regions=[]
    for region in ("Northern","Central","Southern"):
        pre=GBR_COVER_2024[region]
        c25=GBR_COVER_2025[region]
        c26=GBR_COVER_2026[region]
        regions.append({
            "region":region,
            "hard_coral_cover_2024_pct":pre,
            "hard_coral_cover_2025_pct":c25,
            "hard_coral_cover_2026_pct":c26,
            "2026_gap_to_2024_percentage_points":pre-c26,
            "2026_relative_gap_to_2024_fraction":(pre-c26)/pre,
            "observed_2025_to_2026_change_percentage_points":c26-c25,
            "one_year_linear_cover_return_screen_year":(
                2026 + (pre-c26)/(c26-c25) if (c26-c25)>0 and pre>c26 else (2026 if c26>=pre else None)
            ),
            "linear_screen_status":"ONE_YEAR_TREND_EXTRAPOLATION_NOT_FORECAST",
        })

    intervals=[b-a for a,b in zip(GBR_RECENT_MASS_BLEACHING_YEARS[:-1],GBR_RECENT_MASS_BLEACHING_YEARS[1:])]
    mean_interval=sum(intervals)/len(intervals)

    recurrence_scenarios=[]
    for interval in [2,5,10,15,20,30]:
        recurrence_scenarios.append({
            "severe_bleaching_recurrence_interval_years":interval,
            "typical_10y_cover_recovery_window_available":interval>=GBR_COVER_RECOVERY_YEARS_LOW,
            "conservative_15y_cover_recovery_window_available":interval>=GBR_COVER_RECOVERY_YEARS_HIGH,
            "20y_ecological_recovery_screen_available":interval>=REEF_ECOLOGICAL_RECOVERY_YEARS_CENTRAL,
            "interpretation":(
                "Repeated severe heat likely interrupts full coral-cover re-establishment" if interval<10 else
                "A lower-bound cover-recovery window may exist, but ecological/community recovery can still be interrupted" if interval<20 else
                "Both coral-cover and central ecological-recovery windows are physically available if local stressors are also controlled"
            ),
        })

    recovery_start=2026
    return {
        "classification":"LITERATURE_BOUNDED_CORAL_REEF_RECOVERY_SCREEN_NOT_REGIONAL_CLIMATE_FORECAST",
        "great_barrier_reef_observed_state":{
            "2024_pre_mass_bleaching_regional_cover_pct":GBR_COVER_2024,
            "2025_post_2024_bleaching_regional_cover_pct":GBR_COVER_2025,
            "2026_observed_regional_cover_pct":GBR_COVER_2026,
            "region_rows":regions,
            "2026_status":"AIMS reports initial recovery in Northern/Central regions and near-stable/slightly lower cover in the Southern region after monsoon relief; current coral cover remains close to long-term averages overall.",
            "sources":[AIMS_GBR_2024_25,AIMS_GBR_2025_26],
        },
        "recovery_endpoints":{
            "surviving_colony_physiology_and_growth":{
                "screen":"months to several years",
                "growth_calcification_impairment_upper_screen_years":4,
                "meaning":"Bleached but surviving colonies can regain symbionts when thermal stress abates, while growth/reproduction can remain impaired for years.",
                "source":AIMS_CALCIFICATION,
            },
            "hard_coral_cover_reestablishment":{
                "typical_disturbance_free_years_low":GBR_COVER_RECOVERY_YEARS_LOW,
                "typical_disturbance_free_years_central":GBR_COVER_RECOVERY_YEARS_CENTRAL,
                "typical_disturbance_free_years_high":GBR_COVER_RECOVERY_YEARS_HIGH,
                "conditional_calendar_window_from_2026":[recovery_start+GBR_COVER_RECOVERY_YEARS_LOW,recovery_start+GBR_COVER_RECOVERY_YEARS_HIGH],
                "central_conditional_year_from_2026":recovery_start+GBR_COVER_RECOVERY_YEARS_CENTRAL,
                "meaning":"GBR Authority/AIMS state reefs usually re-establish in about 10-15 years if major disturbances are minimal. This is a cover/re-establishment window, not proof that species composition or reef framework has returned to the prior state.",
                "sources":[GBRMPA_BLEACHING,AIMS_BLEACHING,GBR_PALM_ISLANDS_RECOVERY],
            },
            "ecological_community_and_structure":{
                "model_screen_years_low":REEF_ECOLOGICAL_RECOVERY_YEARS_LOW,
                "model_screen_years_central":REEF_ECOLOGICAL_RECOVERY_YEARS_CENTRAL,
                "model_screen_years_high":REEF_ECOLOGICAL_RECOVERY_YEARS_HIGH,
                "conditional_calendar_window_from_2026":[recovery_start+REEF_ECOLOGICAL_RECOVERY_YEARS_LOW,recovery_start+REEF_ECOLOGICAL_RECOVERY_YEARS_HIGH],
                "central_conditional_year_from_2026":recovery_start+REEF_ECOLOGICAL_RECOVERY_YEARS_CENTRAL,
                "status":"MODEL_SCREEN_NOT_SINGLE_OBSERVED_GBR_FORECAST",
                "meaning":"Coral cover can recover faster than community composition, habitat complexity and reef-building function. Some sites recover within years; others require decades, and repeated bleaching can prevent return to the former assemblage.",
                "sources":[GBR_ECOSYSTEM_RESTRUCTURING,CORAL_RECOVERY_VARIABILITY],
            },
        },
        "thermal_disturbance_gate":{
            "recent_mass_bleaching_event_years":GBR_RECENT_MASS_BLEACHING_YEARS,
            "recent_event_intervals_years":intervals,
            "mean_recent_event_spacing_years":mean_interval,
            "required_minimal_disturbance_window_for_typical_cover_recovery_years":[10,15],
            "recent_event_spacing_is_shorter_than_recovery_window":mean_interval<10,
            "recurrence_scenarios":recurrence_scenarios,
            "interpretation":"A recovery clock is meaningful only if severe thermal disturbances become less frequent than the biological recovery time. Recent GBR mass-bleaching event spacing is far shorter than the 10-15 year typical re-establishment window, so whole-system restoration cannot be assumed simply because one cooler year occurs.",
            "sources":[GBRMPA_BLEACHING,AIMS_GBR_2025_26],
        },
        "active_restoration_screen":{
            "local_outplanting_functional_gain_years":[2,6],
            "status":"LOCAL_INTERVENTION_SCREEN_NOT_GBR_WIDE_RECOVERY_TIME",
            "meaning":"Restoration can improve local accretion/structural complexity within a few years at treated sites, but heat-sensitive fast-growing corals can be lost again in a subsequent severe bleaching event. It cannot substitute for thermal stabilization across the GBR.",
            "source":CORAL_RESTORATION_ACCRETION,
        },
        "coupling_to_planetary_model":{
            "global_mean_temperature_directly_converted_to_gbr_bleaching_frequency":False,
            "regional_marine_heatwave_module_present":False,
            "required_future_coupling":"Use a regional ocean/degree-heating-week model or observed bleaching-frequency scenario to determine the first durable 10-15 year low-disturbance window. Then add the biological recovery window to that thermal-safe start year.",
            "conditional_result_if_2026_begins_sustained_low_disturbance_period":"Hard-coral-cover re-establishment screen ~2036-2041; ecological/community-structure screen ~2041-2056. These dates reset or extend after a new severe bleaching/mortality event.",
        },
        "publication_rule":"Report separate clocks for coral survival/physiology, hard-coral cover, and ecological/structural recovery. Do not report a single 'Great Barrier Reef restored by YEAR' unless a regional thermal-stress model demonstrates a sufficiently long disturbance-free window.",
    }


def v53_core_v58(base: Dict) -> Dict:
    core=copy.deepcopy(base["v53_1_full_core"])
    core["_v58_interpretation"]={
        "status":"DIAGNOSTIC_ONLY_FOR_RETURN_YEAR_HEADLINES",
        "do_not_quote_internal_return_years_as_external_forecasts":True,
        "reason":"Archived calibrated FaIR and Hector do not reproduce the internal <=280 ppm return. The internal 2155/2188/2200/2231 dates are retained for sensitivity lineage only.",
    }
    return core


def headline_v58(base: Dict, sink: Dict, sw: Dict, reefs: Dict) -> Dict:
    h=copy.deepcopy(base["headline"])
    h["model_version"]="58.0"
    h["old_v57_extension_regime_21pct_response_headline_removed"]=True
    h.pop("late_pathwise_apparent_atmospheric_response_fraction",None)
    h["canonical_program_cumulative_apparent_atmospheric_response_fraction"] = sink["canonical_endpoint_cumulative_apparent_response_fraction"]
    h["canonical_program_last_20y_apparent_response_fraction"] = sink["canonical_endpoint_rolling_20y_response_fraction"]
    h["primary_seaweed_total_ash_mt_yr"] = sw["ash_allocation_mass_balance"]["total_ash_mt_yr"]
    h["primary_seaweed_food_stream_ash_mt_yr"] = sw["ash_allocation_mass_balance"]["food_stream_ash_mt_yr"]
    central_durable=next(r for r in sw["durable_storage_economics"]["farmgate_cases"] if r["farmgate_case"]=="central_large_scale")
    h["central_seaweed_durable_storage_farmgate_usd_per_tco2"] = central_durable["farmgate_cost_usd_per_tco2_durable"]
    h["great_barrier_reef_conditional_hard_coral_cover_reestablishment_window_if_2026_safe"] = reefs["recovery_endpoints"]["hard_coral_cover_reestablishment"]["conditional_calendar_window_from_2026"]
    h["great_barrier_reef_conditional_ecological_recovery_window_if_2026_safe"] = reefs["recovery_endpoints"]["ecological_community_and_structure"]["conditional_calendar_window_from_2026"]
    h["great_barrier_reef_recent_mean_mass_bleaching_event_spacing_years"] = reefs["thermal_disturbance_gate"]["mean_recent_event_spacing_years"]
    h["coral_reef_recovery_is_conditional_on_thermal_safe_window"] = True
    h["submission_status"]="NOT SUBMISSION READY: coral-recovery module and remaining V57 bookkeeping are integrated, but official zero-background-non-CO2 FaIR, inverse FaIR target solve and OSCAR remain open."
    return h


def run_v58() -> Dict:
    base=v57.run_v57()
    sink=canonical_sink_response_v58()
    sw=seaweed_v58(base)
    reefs=coral_reef_recovery_v58()
    return {
        "model_version":MODEL_VERSION,
        "release_label":RELEASE_LABEL,
        "release_status":RELEASE_STATUS,
        "classification":"CORAL_REEF_RECOVERY_PLUS_CANONICAL_SINK_RESPONSE_AND_FULL_SEAWEED_COST_MASS_BALANCE",
        "headline":headline_v58(base,sink,sw,reefs),
        "external_validation":base["external_validation"],
        "attribution_v57":base["attribution_v57"],
        "canonical_sink_response_v58":sink,
        "fair_splice_diagnostic_v58":fair_splice_diagnostic_v58(base),
        "v53_1_full_core":v53_core_v58(base),
        "legacy_architecture_reference":base["legacy_architecture_reference"],
        "seaweed_v58":sw,
        "fisheries_v57":base["fisheries_v57"],
        "coral_reef_recovery_v58":reefs,
        "restored_human_system_screens":base["restored_human_system_screens"],
        "accounting_rules":{
            **base["accounting_rules"],
            "v53_internal_return_years_diagnostic_only":True,
            "extension_regime_21pct_not_current_headline":True,
            "seaweed_ash_balanced_across_all_allocations":True,
            "seaweed_durable_storage_cost_compared_to_bicrs":True,
            "coral_reef_recovery_requires_regional_thermal_safe_window":True,
        },
    }


def _write_csv(path: Path, rows: Sequence[Mapping]) -> None:
    if not rows:
        return
    keys=[]
    for row in rows:
        for k in row:
            if k not in keys:
                keys.append(k)
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=keys)
        w.writeheader()
        for row in rows:
            out={}
            for k in keys:
                v=row.get(k)
                out[k]=json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v
            w.writerow(out)


def write_outputs(result: Dict) -> None:
    data=HERE/"data"; data.mkdir(exist_ok=True)
    (data/"planetary_restoration_v58_results.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    _write_csv(data/"v58_cumulative_sink_response.csv",result["canonical_sink_response_v58"]["cumulative_curve"])
    _write_csv(data/"v58_rolling20_sink_response.csv",result["canonical_sink_response_v58"]["rolling_20_year"])
    _write_csv(data/"v58_seaweed_ash_allocation.csv",result["seaweed_v58"]["ash_allocation_mass_balance"]["allocation_rows"])
    _write_csv(data/"v58_seaweed_durable_storage_economics.csv",result["seaweed_v58"]["durable_storage_economics"]["farmgate_cases"])
    _write_csv(data/"v58_gbr_regional_state.csv",result["coral_reef_recovery_v58"]["great_barrier_reef_observed_state"]["region_rows"])
    _write_csv(data/"v58_coral_recovery_recurrence_scenarios.csv",result["coral_reef_recovery_v58"]["thermal_disturbance_gate"]["recurrence_scenarios"])


def run_tests(result: Dict) -> None:
    h=result["headline"]
    assert h["externally_validated_return_year"] is None
    sink=result["canonical_sink_response_v58"]
    assert sink["old_v57_extension_regime_21pct_is_current_headline"] is False
    assert 0.55 < sink["canonical_endpoint_cumulative_apparent_response_fraction"] < 0.61
    assert 0.05 < sink["canonical_endpoint_rolling_20y_response_fraction"] < 0.12
    sw=result["seaweed_v58"]
    ash=sw["ash_allocation_mass_balance"]
    assert 62.0 < ash["total_ash_mt_yr"] < 64.0
    assert 3.0 < ash["food_stream_ash_mt_yr"] < 3.3
    assert abs(sum(r["ash_mt_yr"] for r in ash["allocation_rows"])-ash["total_ash_mt_yr"]) < 1e-9
    durable=sw["durable_storage_economics"]["farmgate_cases"]
    central=next(r for r in durable if r["farmgate_case"]=="central_large_scale")
    assert 270 < central["farmgate_cost_usd_per_tco2_durable"] < 285
    reefs=result["coral_reef_recovery_v58"]
    assert reefs["recovery_endpoints"]["hard_coral_cover_reestablishment"]["conditional_calendar_window_from_2026"] == [2036,2041]
    assert reefs["thermal_disturbance_gate"]["mean_recent_event_spacing_years"] < 2.0
    assert result["v53_1_full_core"]["_v58_interpretation"]["do_not_quote_internal_return_years_as_external_forecasts"] is True


def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--tests",action="store_true")
    ap.add_argument("--no-write",action="store_true")
    args=ap.parse_args()
    result=run_v58()
    run_tests(result)
    if not args.no_write:
        write_outputs(result)
    if args.tests:
        print("V58 CORAL REEF + CANONICAL SINK RESPONSE TESTS PASSED")
    print(json.dumps(result["headline"],indent=2,ensure_ascii=False))


if __name__=="__main__":
    main()
