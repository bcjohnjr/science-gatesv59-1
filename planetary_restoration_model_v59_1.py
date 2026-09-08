#!/usr/bin/env python3
"""Planetary Restoration Model V59.1 — scope-freeze maintenance release.

V59.1 adds NO new planetary subsystem. It is a corrective release that:
- fixes archive / manifest reproducibility;
- fixes stale submission-status text;
- narrows the paper-facing sea-level result to the archived FaIR horizon;
- demotes post-2400 sea-level dates to excluded experimental diagnostics;
- reports OAE by its peak pH increment rather than the effectively-zero 2400 residue;
- stops presenting fixed-temperature/salinity pH threshold years as publication-grade;
- explains why early apparent atmospheric response can exceed 1;
- adds an aggregate FaIR percentile-curve response envelope while explicitly
  leaving true configuration-level response uncertainty open;
- records an AR6 sea-level calibration/sanity check and notes that the simple
  three-case emulator under-disperses 2300 uncertainty;
- freezes manuscript scope pending the three external carbon-cycle gates.
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
MODEL_VERSION = "59.1"
RELEASE_LABEL = "Planetary Restoration Model Version 59.1 — Scope-Freeze Maintenance Release"
RELEASE_STATUS = "SCOPE_FROZEN_EXTERNAL_VALIDATION_CRITICAL_PATH"

V59_PATH = HERE / "previous_version_v59.py"
ATMOSPHERIC_GTCO2_PER_PPM = 7.77

AR6_2100_SSP119_LIKELY = [0.28, 0.55]
AR6_2300_SSP126_RANGE = [0.30, 3.10]
APPROX_1995_2014_TO_2026_GMSL_M = 0.07


def _import_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


v59 = _import_module(V59_PATH, "v59_1_previous_v59")


def sink_response_v59_1(base: Dict) -> Dict:
    sink0 = base["v58_full_architecture"]["canonical_sink_response_v58"]
    fair_rows = v59.load_fair_timeseries()
    fair_by = {int(r["year"]): r for r in fair_rows}

    first_neg = int(sink0["first_negative_net_co2_year"])
    end_tb = int(sink0["canonical_post_flux_timebound"])
    cumulative_removal = float(sink0["canonical_endpoint"]["cumulative_net_removal_gtco2"])

    envelope = []
    for q in ("p05", "p50", "p95"):
        start = float(fair_by[first_neg][f"co2_{q}_ppm"])
        end = float(fair_by[end_tb][f"co2_{q}_ppm"])
        drawdown = start - end
        frac = drawdown * ATMOSPHERIC_GTCO2_PER_PPM / cumulative_removal
        envelope.append({
            "archived_concentration_percentile_curve": q,
            "start_ppm_at_first_negative_year_timebound": start,
            "end_ppm_after_final_canonical_flux": end,
            "cumulative_drawdown_ppm": drawdown,
            "apparent_atmospheric_response_fraction": frac,
        })

    return {
        **sink0,
        "why_early_response_can_exceed_one": (
            "The numerator is the total atmospheric CO2 stock decline after the first net-negative year, "
            "while the denominator counts only contemporaneous anthropogenic net removal. Early in the "
            "negative-emissions phase, land and ocean are still net sinks because of the prior elevated-CO2 "
            "state, so natural uptake adds to anthropogenic removal. The ratio is therefore not a physical "
            "efficiency bounded by 1. Values above 1 are expected during that transient."
        ),
        "paper_caption": (
            "Apparent atmospheric response is atmospheric CO2 stock decline divided by cumulative net "
            "anthropogenic removal after the first net-negative year. It can exceed unity early because "
            "legacy natural land/ocean uptake continues in parallel; as those sinks weaken and reverse, "
            "the ratio falls. The metric is path-dependent and is not a universal marginal removal efficiency."
        ),
        "archived_percentile_curve_endpoint_envelope": envelope,
        "archived_percentile_curve_envelope_status": (
            "AGGREGATE_CURVE_ENVELOPE_ONLY_NOT_CONFIGURATION_LEVEL_RESPONSE_QUANTILES"
        ),
        "configuration_level_response_fraction_uncertainty_status": (
            "OPEN_REQUIRES_OFFICIAL_FAIR_RERUN_ARCHIVING_PER_CONFIGURATION_TRAJECTORIES"
        ),
    }


def ocean_ph_v59_1(base: Dict) -> Dict:
    p0 = base["ocean_ph_v59"]
    rows = p0["rows"]
    peak = max(rows, key=lambda r: float(r["oae_ph_increment"]))
    minimum = min(rows, key=lambda r: float(r["surface_ocean_ph"]))
    final = rows[-1]
    modeled_recovery = float(final["surface_ocean_ph"]) - float(minimum["surface_ocean_ph"])
    peak_share = (
        float(peak["oae_ph_increment"]) / modeled_recovery
        if modeled_recovery > 0 else None
    )

    return {
        **p0,
        "peak_oae_ph_increment": float(peak["oae_ph_increment"]),
        "peak_oae_ph_increment_year": int(peak["year"]),
        "peak_oae_alkalinity_anomaly_umol_kg": float(peak["oae_alkalinity_anomaly_umol_kg"]),
        "peak_oae_increment_fraction_of_min_to_endpoint_modeled_recovery": peak_share,
        "oae_endpoint_increment_is_headline": False,
        "fixed_temperature_salinity_publication_precision": "TWO_DECIMAL_PH_ONLY",
        "fixed_temperature_salinity_threshold_years_publication_status": (
            "WITHHELD_AS_PUBLICATION_HEADLINE_PENDING_TEMPERATURE_COUPLED_CO2SYS_PYCO2SYS"
        ),
        "publication_rounded": {
            "pH_2026": round(float(p0["pH_2026"]), 2),
            "minimum_surface_ph": round(float(p0["minimum_surface_ph"]), 2),
            "pH_at_end_of_canonical_2183": round(float(p0["pH_at_end_of_canonical_2183"]), 2),
            "pH_at_fair_2400_timebound": round(float(p0["pH_at_fair_2400_timebound"]), 2),
            "peak_oae_ph_increment": round(float(peak["oae_ph_increment"]), 3),
        },
        "diagnostic_fixed_ts_threshold_years": {
            "pH_8_10": p0["recovery_year_pH_8_10"],
            "pH_8_15": p0["recovery_year_pH_8_15"],
            "pH_8_17": p0["recovery_year_pH_8_17"],
            "status": "DIAGNOSTIC_ONLY_NOT_PUBLICATION_GRADE",
        },
        "temperature_sensitivity_context": (
            "The inherited chemistry fixes temperature and salinity. Published seawater pH temperature "
            "coefficients are of order 0.01–0.015 pH units per °C under oceanographic conditions, large "
            "enough that four-decimal pH and exact threshold-crossing years are not defensible here."
        ),
        "publication_rule_v59_1": (
            "Report pH only to two decimals from this compact fixed-T/S screen. Report the OAE contribution "
            "as its peak increment (~0.002 pH units), not its nearly-decayed endpoint value. Do not publish "
            "exact 8.10/8.15/8.17 crossing years until temperature-coupled CO2SYS/PyCO2SYS is run."
        ),
    }


def sea_level_v59_1(base: Dict) -> Dict:
    s0 = base["sea_level_v59"]
    archived = s0["archived_fair_horizon"]

    checks = []
    for case in ("low", "central", "high"):
        m2100 = float(archived[case]["milestones"]["2100"]["additional_since_2026_m"]) + APPROX_1995_2014_TO_2026_GMSL_M
        m2300 = float(archived[case]["milestones"]["2300"]["additional_since_2026_m"]) + APPROX_1995_2014_TO_2026_GMSL_M
        checks.append({
            "case": case,
            "approx_2100_rel_1995_2014_m": m2100,
            "within_ar6_ssp1_1_9_2100_likely": AR6_2100_SSP119_LIKELY[0] <= m2100 <= AR6_2100_SSP119_LIKELY[1],
            "approx_2300_rel_1995_2014_m": m2300,
            "within_ar6_ssp1_2_6_2300_assessed_range": AR6_2300_SSP126_RANGE[0] <= m2300 <= AR6_2300_SSP126_RANGE[1],
        })

    experiments = {
        "paper_excluded": True,
        "reason": (
            "These experiments run centuries to millennia beyond the archived FaIR driver and depend strongly "
            "on uncalibrated slow ice-sheet response. They are retained for lineage/debugging only and must not "
            "appear in manuscript text, abstract, figures or headline tables."
        ),
        "conditional_post_2400_restoration_to_zero_temperature":
            s0["conditional_post_2400_restoration_to_zero_temperature"],
        "central_boundary_tests": s0["central_boundary_tests"],
    }

    current = dict(s0)
    current.pop("conditional_post_2400_restoration_to_zero_temperature", None)
    current.pop("central_boundary_tests", None)
    current["experimental_post2400_boundary_tests"] = experiments
    current["ar6_calibration_screen"] = {
        "rows": checks,
        "ar6_2100_ssp1_1_9_likely_range_m_rel_1995_2014": AR6_2100_SSP119_LIKELY,
        "ar6_2300_ssp1_2_6_assessed_range_m_rel_1995_2014": AR6_2300_SSP126_RANGE,
        "finding": (
            "The simple V59 sensitivity cases are broadly compatible with the low-emissions AR6 range at "
            "2100 and fall inside the very broad assessed 2300 range, but the V59 high case reaches only "
            "about 1.33 m relative to 1995–2014 by 2300 and therefore does not span the AR6 upper range of "
            "3.1 m. The three V59 cases are illustrative sensitivities, not a calibrated uncertainty interval."
        ),
        "underdispersed_vs_ar6_2300_upper_range": True,
    }
    current["uncertainty_treatment_v59_1"] = (
        "Do not label low/central/high as p05/p50/p95 sea-level uncertainty. They combine FaIR temperature "
        "quantiles with a narrow emulator parameter spread and under-represent deep ice-sheet uncertainty."
    )
    current["paper_facing_result"] = {
        "central_additional_since_2026_m": {
            y: archived["central"]["milestones"][str(y)]["additional_since_2026_m"]
            for y in (2050, 2100, 2150, 2300, 2400)
        },
        "central_rate_mm_yr_2400": archived["central"]["milestones"]["2400"]["rate_mm_yr"],
        "interpretation": (
            "The paper-facing result is the persistence of sea-level rise through the archived FaIR horizon, "
            "not a millennial restoration date."
        ),
    }
    return current


def headline_v59_1(base: Dict, sink: Dict, ph: Dict, sea: Dict) -> Dict:
    h = dict(base["headline"])

    # Remove paper-facing millennial dates and exact fixed-T/S pH threshold dates.
    for key in list(h):
        if key.startswith("conditional_zero_warming_extension_"):
            h.pop(key, None)
    for key in (
        "surface_ocean_ph_external_fair_driven_minimum",
        "surface_ocean_ph_external_fair_driven_at_canonical_2183",
        "surface_ocean_ph_external_fair_driven_at_fair_2400",
        "surface_ocean_ph_recovery_year_8_10",
        "surface_ocean_ph_recovery_year_8_15",
        "surface_ocean_ph_recovery_year_8_17",
    ):
        h.pop(key, None)

    env = sink["archived_percentile_curve_endpoint_envelope"]
    env_values = [float(x["apparent_atmospheric_response_fraction"]) for x in env]

    h.update({
        "model_version": MODEL_VERSION,
        "submission_status": (
            "NOT SUBMISSION READY: scope frozen at V59.1. Remaining critical path is the official "
            "common-state/zero-background-non-CO2 FaIR work, inverse FaIR target solve, and OSCAR "
            "run or explicit gate revision."
        ),
        "scope_frozen": True,
        "no_new_modules_until_external_validation": True,
        "canonical_response_fraction_early_gt1_explained": True,
        "canonical_endpoint_response_fraction_aggregate_percentile_curve_envelope":
            [min(env_values), max(env_values)],
        "configuration_level_response_uncertainty_open": True,
        "sea_level_paper_facing_central_2400_additional_m":
            sea["paper_facing_result"]["central_additional_since_2026_m"][2400],
        "sea_level_paper_facing_central_2400_rate_mm_yr":
            sea["paper_facing_result"]["central_rate_mm_yr_2400"],
        "sea_level_post2400_dates_excluded_from_paper": True,
        "sea_level_three_case_uncertainty_underdispersed_vs_ar6_2300": True,
        "surface_ocean_ph_publication_rounded_minimum":
            ph["publication_rounded"]["minimum_surface_ph"],
        "surface_ocean_ph_publication_rounded_fair_2400":
            ph["publication_rounded"]["pH_at_fair_2400_timebound"],
        "surface_ocean_ph_exact_threshold_years_withheld": True,
        "oae_peak_surface_ph_increment": ph["peak_oae_ph_increment"],
        "oae_peak_surface_ph_increment_year": ph["peak_oae_ph_increment_year"],
        "oae_peak_alkalinity_anomaly_umol_kg": ph["peak_oae_alkalinity_anomaly_umol_kg"],
        "oae_peak_increment_fraction_of_modeled_min_to_endpoint_recovery":
            ph["peak_oae_increment_fraction_of_min_to_endpoint_modeled_recovery"],
        "working_manuscript_scope": (
            "Main text: externally benchmarked carbon-sink reversal / response curve, inverse solve when "
            "available, and sea-level persistence as a consequence. Coral, pH, seaweed, fisheries, grid "
            "and monetary architecture move to Supplementary Information or separate papers."
        ),
    })
    return h




def _sanitize_superseded_statuses(obj):
    # Scrub stale release-status prose inside the embedded prior-version lineage tree.
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k == "submission_status":
                out[k] = "SUPERSEDED_LINEAGE_STATUS_SEE_CURRENT_V59_1_HEADLINE"
            else:
                out[k] = _sanitize_superseded_statuses(v)
        return out
    if isinstance(obj, list):
        return [_sanitize_superseded_statuses(v) for v in obj]
    return obj

def run_v59_1() -> Dict:
    base = v59.run_v59()
    sink = sink_response_v59_1(base)
    ph = ocean_ph_v59_1(base)
    sea = sea_level_v59_1(base)
    base_arch = _sanitize_superseded_statuses(base)
    return {
        "model_version": MODEL_VERSION,
        "release_label": RELEASE_LABEL,
        "release_status": RELEASE_STATUS,
        "classification": "MAINTENANCE_SCOPE_FREEZE_NO_NEW_PLANETARY_MODULES",
        "headline": headline_v59_1(base, sink, ph, sea),
        "sink_response_v59_1": sink,
        "sea_level_v59_1": sea,
        "ocean_ph_v59_1": ph,
        "current_external_validation": base["v58_full_architecture"]["external_validation"],
        "v59_0_full_architecture": {
            **base_arch,
            "_v59_1_interpretation": {
                "status": "PRESERVED_FULL_V59_0_LINEAGE",
                "superseded_by": "V59.1",
                "do_not_use_v59_0_headline_as_current": True,
            },
        },
        "scope_freeze": {
            "status": "ACTIVE",
            "new_planetary_modules_allowed_before_external_gates": False,
            "critical_path": [
                "official FaIR common-state restart / splice reconciliation",
                "official FaIR zero-background-non-CO2 experiment",
                "inverse FaIR removal-schedule solve",
                "OSCAR run or explicit justified revision of the predeclared OSCAR gate",
            ],
            "paper_scope": (
                "Sink-response curve + inverse result + sea-level persistence in main text. "
                "Other integrated modules remain available as supplementary architecture."
            ),
        },
    }


def _write_csv(path: Path, rows: Sequence[Mapping]) -> None:
    if not rows:
        return
    keys = []
    for row in rows:
        for k in row:
            if k not in keys:
                keys.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for row in rows:
            out = {}
            for k in keys:
                v = row.get(k)
                out[k] = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
            w.writerow(out)


def write_outputs(result: Dict) -> None:
    data = HERE / "data"
    data.mkdir(exist_ok=True)
    (data / "planetary_restoration_v59_1_results.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    _write_csv(
        data / "v59_1_sink_response_percentile_curve_envelope.csv",
        result["sink_response_v59_1"]["archived_percentile_curve_endpoint_envelope"],
    )
    _write_csv(
        data / "v59_1_sea_level_ar6_calibration_screen.csv",
        result["sea_level_v59_1"]["ar6_calibration_screen"]["rows"],
    )
    _write_csv(
        data / "v59_1_oae_peak_summary.csv",
        [{
            "peak_oae_ph_increment": result["ocean_ph_v59_1"]["peak_oae_ph_increment"],
            "peak_oae_ph_increment_year": result["ocean_ph_v59_1"]["peak_oae_ph_increment_year"],
            "peak_oae_alkalinity_anomaly_umol_kg":
                result["ocean_ph_v59_1"]["peak_oae_alkalinity_anomaly_umol_kg"],
            "peak_oae_increment_fraction_of_modeled_min_to_endpoint_recovery":
                result["ocean_ph_v59_1"]["peak_oae_increment_fraction_of_min_to_endpoint_modeled_recovery"],
        }],
    )


def run_tests(result: Dict) -> None:
    # Property test: validate the atmospheric ppm -> GtCO2 conversion constant
    # against an independent derivation rather than multiplying and dividing by
    # the same constant. Global Carbon Budget 2025, Table 1 uses 1 ppm CO2 =
    # 2.124 GtC; convert carbon mass to CO2 mass with the molar-mass ratio.
    # Source: Friedlingstein et al., Global Carbon Budget 2025, ESSD 18, 3211-3276
    # (2026), Table 1: https://essd.copernicus.org/articles/18/3211/2026/
    expected_gtco2_per_ppm = 2.124 * (44.009 / 12.011)
    assert math.isclose(
        ATMOSPHERIC_GTCO2_PER_PPM,
        expected_gtco2_per_ppm,
        rel_tol=2e-3,
        abs_tol=0.0,
    ), (ATMOSPHERIC_GTCO2_PER_PPM, expected_gtco2_per_ppm)

    h = result["headline"]
    assert result["model_version"] == "59.1"
    assert h["scope_frozen"] is True
    assert "coral-recovery module and remaining V57 bookkeeping" not in h["submission_status"]
    assert h["sea_level_post2400_dates_excluded_from_paper"] is True
    assert "conditional_zero_warming_extension_return_to_2026_gmsl_year_central" not in h
    assert h["surface_ocean_ph_exact_threshold_years_withheld"] is True
    assert 0.0017 < h["oae_peak_surface_ph_increment"] < 0.0019
    assert h["oae_peak_surface_ph_increment_year"] == 2147
    assert 14.0 < h["oae_peak_alkalinity_anomaly_umol_kg"] < 14.6
    lo, hi = h["canonical_endpoint_response_fraction_aggregate_percentile_curve_envelope"]
    assert 0.56 < lo < 0.58
    assert 0.58 < hi < 0.60
    assert result["sea_level_v59_1"]["ar6_calibration_screen"]["underdispersed_vs_ar6_2300_upper_range"] is True
    assert result["ocean_ph_v59_1"]["fixed_temperature_salinity_publication_precision"] == "TWO_DECIMAL_PH_ONLY"

    # Property test: the externally exported annual carbon trajectory must close its
    # anthropogenic mass balance, rather than merely reproducing a stored headline.
    trajectory_path = HERE / "data" / "external_validation_net_co2_trajectory.csv"
    with trajectory_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows, "external validation trajectory is empty"
    for row in rows:
        gross = float(row["gross_co2_gtco2"])
        permafrost = float(row["permafrost_co2_gtco2"])
        reversal = float(row["stored_carbon_reversal_gtco2"])
        cdr = float(row["cdr_gtco2"])
        reported_net = float(row["net_co2_gtco2"])
        calculated_net = gross + permafrost + reversal - cdr
        assert math.isclose(reported_net, calculated_net, rel_tol=0.0, abs_tol=1e-10), row["year"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tests", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()
    result = run_v59_1()
    run_tests(result)
    if not args.no_write:
        write_outputs(result)
    if args.tests:
        print("V59.1 SCOPE-FREEZE MAINTENANCE TESTS PASSED")
    print(json.dumps(result["headline"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
