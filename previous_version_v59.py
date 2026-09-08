#!/usr/bin/env python3
"""Planetary Restoration Model V59 — Sea-Level Rise/Fall Timelines + External-CO2 Ocean pH.

V59 preserves the complete V58 architecture and adds two physical screening layers:

1. A global-mean sea-level response module driven by the archived FaIR 2.2.4
   p05/p50/p95 temperature trajectories.  The model uses a Mengel-et-al.-style
   component pursuit-curve framework for thermosteric expansion, glaciers,
   Greenland surface-mass-balance response and Antarctic dynamic response.
   It is calibrated as a screening emulator, not presented as an IPCC/FACTS
   replacement or a process-based ice-sheet forecast.

2. An ocean-pH screen driven by the archived FaIR median CO2 concentration
   rather than the superseded Joos concentration trajectory.  It retains the
   existing compact carbonate/OAE chemistry from V53.1 and the same OAE
   deployment schedule, but aligns the chemistry to the externally benchmarked
   atmospheric CO2 path.

Critical boundary:
- V59 can estimate *conditional* sea-level rise/fall timelines under explicit
  post-2400 temperature assumptions.
- It cannot claim an unconditional sea-level-restoration date because the
  archived FaIR run ends at 2400 and the package does not contain a process-based
  Greenland/Antarctic hysteresis model.
- The old internal pH-at-280 result remains lineage only because external FaIR
  does not reach 280 ppm by 2400.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import sys
import zipfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Mapping, Sequence, Optional

HERE = Path(__file__).resolve().parent
MODEL_VERSION = "59.0"
RELEASE_LABEL = "Planetary Restoration Model Version 59.0 — Sea-Level Rise/Fall + External-CO2 Ocean pH"
RELEASE_STATUS = "INTERNAL_SCREENING_SEA_LEVEL_ADDED_EXTERNAL_FAIR_OSCAR_AND_INVERSE_GATES_OPEN"

V58_PATH = HERE / "previous_version_v58.py"
V53_PATH = HERE / "previous_branches" / "planetary_restoration_model_v53_1.py"
FAIR_ZIP = HERE / "external_validation_results" / "fair-v2.2.4-results.zip"

NASA_2026_GMSL_SINCE_1993_MM = 100.7
NASA_2026_GMSL_UNCERTAINTY_MM = 4.0
NASA_LONG_RUN_RATE_MM_YR = 4.4
AR6_SSP119_2100_MEDIAN_M_REL_1995_2014 = 0.38
AR6_SSP119_2100_LIKELY_LOW_M = 0.28
AR6_SSP119_2100_LIKELY_HIGH_M = 0.55
AR6_SSP119_2150_MEDIAN_M_REL_1995_2014 = 0.60
AR6_SSP119_2150_LIKELY_LOW_M = 0.40
AR6_SSP119_2150_LIKELY_HIGH_M = 0.90

# Approximate context-only offset from the IPCC 1995–2014 baseline to 2026.
# This is deliberately NOT used to initialize the component ODEs or to claim
# a precise observational baseline conversion.
APPROX_1995_2014_TO_2026_GMSL_M = 0.07


def _import_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


v58mod = _import_module(V58_PATH, "v59_previous_v58")
v53mod = _import_module(V53_PATH, "v59_v53_lineage")


@dataclass(frozen=True)
class SeaLevelParams:
    name: str
    fair_temperature_quantile: str

    # Absolute 2026 component states used only to initialize the pursuit curves.
    # V59 headline outputs are changes *from 2026*, so these are not claimed as
    # a reconstruction of observed component partitioning.
    initial_thermal_m: float = 0.080
    initial_glacier_m: float = 0.080
    initial_greenland_m: float = 0.045
    initial_antarctica_m: float = 0.015
    initial_landwater_m: float = 0.000

    # Mengel-style pursuit-curve parameters.
    thermal_commitment_m_per_c: float = 0.40
    thermal_tau_yr: float = 350.0

    # Simplified saturating glacier-equilibrium screen.
    glacier_equilibrium_max_m: float = 0.32
    glacier_temperature_scale_c: float = 1.20
    glacier_tau_yr: float = 130.0

    greenland_smb_commitment_m_per_c2: float = 0.12
    greenland_tau_yr: float = 300.0

    antarctic_dynamic_commitment_m_per_c: float = 1.20
    antarctic_tau_yr: float = 1800.0


SEA_LEVEL_CASES = {
    "low": SeaLevelParams(
        name="Low sea-level response screen",
        fair_temperature_quantile="p05",
        thermal_commitment_m_per_c=0.36,
        thermal_tau_yr=330.0,
        glacier_equilibrium_max_m=0.31,
        glacier_tau_yr=135.0,
        greenland_smb_commitment_m_per_c2=0.09,
        greenland_tau_yr=330.0,
        antarctic_dynamic_commitment_m_per_c=1.08,
        antarctic_tau_yr=1750.0,
    ),
    "central": SeaLevelParams(
        name="Central sea-level response screen",
        fair_temperature_quantile="p50",
    ),
    "high": SeaLevelParams(
        name="High sea-level response screen",
        fair_temperature_quantile="p95",
        thermal_commitment_m_per_c=0.46,
        thermal_tau_yr=340.0,
        glacier_equilibrium_max_m=0.34,
        glacier_tau_yr=140.0,
        greenland_smb_commitment_m_per_c2=0.145,
        greenland_tau_yr=320.0,
        antarctic_dynamic_commitment_m_per_c=1.28,
        antarctic_tau_yr=1900.0,
    ),
}


def load_fair_timeseries() -> List[Dict]:
    with zipfile.ZipFile(FAIR_ZIP) as z:
        rows = list(csv.DictReader(z.read("fair_v2_2_4_timeseries.csv").decode().splitlines()))
    out = []
    for r in rows:
        out.append({
            "year": int(float(r["year"])),
            "co2_p05_ppm": float(r["co2_p05_ppm"]),
            "co2_p50_ppm": float(r["co2_p50_ppm"]),
            "co2_p95_ppm": float(r["co2_p95_ppm"]),
            "temperature_p05_c": float(r["temperature_p05_c"]),
            "temperature_p50_c": float(r["temperature_p50_c"]),
            "temperature_p95_c": float(r["temperature_p95_c"]),
        })
    return out


def fair_temperature_by_year(rows: Sequence[Mapping], quantile: str) -> Dict[int, float]:
    key = f"temperature_{quantile}_c"
    return {int(r["year"]): float(r[key]) for r in rows}


def fair_co2_by_year(rows: Sequence[Mapping], quantile: str = "p50") -> Dict[int, float]:
    key = f"co2_{quantile}_ppm"
    return {int(r["year"]): float(r[key]) for r in rows}


def extend_temperature(
    base: Mapping[int, float],
    end_year: int,
    mode: str,
    target_c: float = 0.0,
    tau_yr: float = 300.0,
    target_year: int = 2700,
) -> Dict[int, float]:
    """Explicit post-2400 boundary scenarios; never treated as archived FaIR output."""
    out = dict(base)
    last_year = max(y for y in out if y <= 2400)
    t0 = float(out[last_year])
    for y in range(last_year + 1, end_year + 1):
        if mode == "hold_2400":
            out[y] = t0
        elif mode == "exponential":
            out[y] = target_c + (t0 - target_c) * math.exp(-(y - last_year) / tau_yr)
        elif mode == "linear":
            if y >= target_year:
                out[y] = target_c
            else:
                f = (y - last_year) / (target_year - last_year)
                out[y] = t0 + f * (target_c - t0)
        else:
            raise KeyError(mode)
    return out


def _equilibrium_components(temp_c: float, p: SeaLevelParams) -> Dict[str, float]:
    t = max(0.0, float(temp_c))
    return {
        "thermal_m": p.thermal_commitment_m_per_c * t,
        "glacier_m": p.glacier_equilibrium_max_m * (1.0 - math.exp(-t / p.glacier_temperature_scale_c)),
        "greenland_m": p.greenland_smb_commitment_m_per_c2 * t * t,
        "antarctica_m": p.antarctic_dynamic_commitment_m_per_c * t,
        "landwater_m": p.initial_landwater_m,
    }


def run_sea_level(
    temperature_by_year: Mapping[int, float],
    p: SeaLevelParams,
    start_year: int = 2026,
    end_year: int = 2400,
) -> List[Dict]:
    state = {
        "thermal_m": p.initial_thermal_m,
        "glacier_m": p.initial_glacier_m,
        "greenland_m": p.initial_greenland_m,
        "antarctica_m": p.initial_antarctica_m,
        "landwater_m": p.initial_landwater_m,
    }
    initial_total = sum(state.values())
    previous_total = initial_total
    rows: List[Dict] = []

    tau = {
        "thermal_m": p.thermal_tau_yr,
        "glacier_m": p.glacier_tau_yr,
        "greenland_m": p.greenland_tau_yr,
        "antarctica_m": p.antarctic_tau_yr,
    }

    for year in range(start_year, end_year + 1):
        temp = float(temperature_by_year[year])
        eq = _equilibrium_components(temp, p)
        for k in ("thermal_m", "glacier_m", "greenland_m", "antarctica_m"):
            state[k] += (eq[k] - state[k]) / tau[k]
        total = sum(state.values())
        rate_mm_yr = (total - previous_total) * 1000.0
        previous_total = total
        rows.append({
            "year": year,
            "temperature_c_above_1750_fair_reference": temp,
            "gmsl_additional_since_2026_m": total - initial_total,
            "gmsl_rate_mm_yr": rate_mm_yr,
            "thermal_additional_m": state["thermal_m"] - p.initial_thermal_m,
            "glacier_additional_m": state["glacier_m"] - p.initial_glacier_m,
            "greenland_additional_m": state["greenland_m"] - p.initial_greenland_m,
            "antarctica_additional_m": state["antarctica_m"] - p.initial_antarctica_m,
            "absolute_climate_driven_component_state_m": total,
        })
    return rows


def _year_row(rows: Sequence[Mapping], year: int) -> Mapping:
    return next(r for r in rows if int(r["year"]) == year)


def _first_nonpositive_rate_after(rows: Sequence[Mapping], year: int) -> Optional[int]:
    r = next((x for x in rows if int(x["year"]) > year and float(x["gmsl_rate_mm_yr"]) <= 0.0), None)
    return None if r is None else int(r["year"])


def _peak(rows: Sequence[Mapping]) -> Mapping:
    return max(rows, key=lambda r: float(r["gmsl_additional_since_2026_m"]))


def _first_after_peak_below(rows: Sequence[Mapping], peak_year: int, threshold: float) -> Optional[int]:
    r = next((x for x in rows if int(x["year"]) > peak_year and float(x["gmsl_additional_since_2026_m"]) <= threshold), None)
    return None if r is None else int(r["year"])


def _first_absolute_component_state_below(rows: Sequence[Mapping], peak_year: int, threshold_m: float) -> Optional[int]:
    r = next((x for x in rows if int(x["year"]) > peak_year and float(x["absolute_climate_driven_component_state_m"]) <= threshold_m), None)
    return None if r is None else int(r["year"])


def sea_level_v59(fair_rows: Sequence[Mapping]) -> Dict:
    archived = {}
    archived_long_rows = []
    for key, p in SEA_LEVEL_CASES.items():
        temps = fair_temperature_by_year(fair_rows, p.fair_temperature_quantile)
        rows = run_sea_level(temps, p, 2026, 2400)
        archived[key] = {
            "parameters": asdict(p),
            "rows": rows,
            "milestones": {
                str(y): {
                    "additional_since_2026_m": float(_year_row(rows, y)["gmsl_additional_since_2026_m"]),
                    "rate_mm_yr": float(_year_row(rows, y)["gmsl_rate_mm_yr"]),
                } for y in (2050, 2100, 2150, 2200, 2300, 2400)
            },
            "peak_within_archived_horizon": {
                "year": int(_peak(rows)["year"]),
                "additional_since_2026_m": float(_peak(rows)["gmsl_additional_since_2026_m"]),
            },
        }
        for r in rows:
            archived_long_rows.append({"case": key, **r})

    # Long-term boundary tests. These are NOT archived FaIR outputs.
    restoration_cases = {}
    for key, p in SEA_LEVEL_CASES.items():
        temps0 = fair_temperature_by_year(fair_rows, p.fair_temperature_quantile)
        t_ext = extend_temperature(temps0, 20000, "exponential", target_c=0.0, tau_yr=300.0)
        rows = run_sea_level(t_ext, p, 2026, 20000)
        peak = _peak(rows)
        py = int(peak["year"])
        pv = float(peak["gmsl_additional_since_2026_m"])
        restoration_cases[key] = {
            "post_2400_temperature_boundary": "exponential decline toward 0 C; 300-year e-folding; scenario only",
            "peak_gmsl_year": py,
            "peak_additional_since_2026_m": pv,
            "first_nonpositive_gmsl_rate_year": _first_nonpositive_rate_after(rows, 2026),
            "first_10cm_below_peak_year": _first_after_peak_below(rows, py, pv - 0.10),
            "first_return_to_2026_gmsl_year": _first_after_peak_below(rows, py, 0.0),
            "first_within_5cm_of_preindustrial_climate_component_state_year":
                _first_absolute_component_state_below(rows, py, 0.05),
        }

    p = SEA_LEVEL_CASES["central"]
    t0 = fair_temperature_by_year(fair_rows, "p50")

    hold_rows = run_sea_level(extend_temperature(t0, 10000, "hold_2400"), p, 2026, 10000)
    hold_peak = _peak(hold_rows)

    floor_rows = run_sea_level(
        extend_temperature(t0, 10000, "exponential", target_c=0.20, tau_yr=300.0),
        p, 2026, 10000
    )
    floor_peak = _peak(floor_rows)
    floor_py = int(floor_peak["year"])

    central = archived["central"]["rows"]
    central_2026_rate = float(_year_row(central, 2026)["gmsl_rate_mm_yr"])
    approx_rel_1995_2100 = (
        float(_year_row(central, 2100)["gmsl_additional_since_2026_m"])
        + APPROX_1995_2014_TO_2026_GMSL_M
    )

    return {
        "classification": (
            "Global-mean sea-level screening emulator using a Mengel-et-al.-style pursuit-curve "
            "framework driven by archived FaIR temperature. It is not a process-based ice-sheet "
            "model and not an IPCC/FACTS sea-level projection."
        ),
        "observational_context": {
            "nasa_gmsl_since_1993_aug_2026_mm": NASA_2026_GMSL_SINCE_1993_MM,
            "nasa_uncertainty_mm": NASA_2026_GMSL_UNCERTAINTY_MM,
            "nasa_long_run_rate_since_early_1990s_mm_yr": NASA_LONG_RUN_RATE_MM_YR,
            "central_screen_first_year_rate_mm_yr": central_2026_rate,
            "model_reports_changes_from_2026": True,
        },
        "method": {
            "pursuit_curve": "dS/dt = (S_eq(T) - S) / tau",
            "thermal_commitment_range_source": "Mengel et al. 2016: 0.2–0.626 m/C; tau 81.7–1290 y",
            "greenland_smb_range_source": "Mengel et al. 2016: 0.05–0.21 m/C^2; tau 99.7–927 y",
            "antarctic_dynamic_range_source": "Mengel et al. 2016: 1.0–1.5 m/C; tau 1350–2910 y",
            "glacier_treatment": (
                "Simplified saturating global glacier-equilibrium screen with response time within "
                "Mengel calibrated 98–295 y range; tuned only as an AR6-consistency screen."
            ),
            "missing_processes": [
                "marine ice-sheet instability / marine ice-cliff instability",
                "full Greenland dynamic-discharge convolution",
                "Antarctic snowfall surface-mass-balance parameterization",
                "regional gravitational/rotational fingerprints",
                "vertical land motion and local relative sea level",
                "explicit ice-sheet hysteresis and tipping thresholds",
            ],
        },
        "archived_fair_horizon": archived,
        "archived_rows_flat": archived_long_rows,
        "ar6_sanity_check": {
            "approx_1995_2014_to_2026_offset_m_context_only": APPROX_1995_2014_TO_2026_GMSL_M,
            "central_2100_approx_rel_1995_2014_m": approx_rel_1995_2100,
            "v59_low_2100_approx_rel_1995_2014_m": (
                float(_year_row(archived["low"]["rows"], 2100)["gmsl_additional_since_2026_m"])
                + APPROX_1995_2014_TO_2026_GMSL_M
            ),
            "v59_high_2100_approx_rel_1995_2014_m": (
                float(_year_row(archived["high"]["rows"], 2100)["gmsl_additional_since_2026_m"])
                + APPROX_1995_2014_TO_2026_GMSL_M
            ),
            "ar6_ssp1_1_9_2100_median_m": AR6_SSP119_2100_MEDIAN_M_REL_1995_2014,
            "ar6_ssp1_1_9_2100_likely_range_m": [AR6_SSP119_2100_LIKELY_LOW_M, AR6_SSP119_2100_LIKELY_HIGH_M],
            "ar6_ssp1_1_9_2150_median_m": AR6_SSP119_2150_MEDIAN_M_REL_1995_2014,
            "ar6_ssp1_1_9_2150_likely_range_m": [AR6_SSP119_2150_LIKELY_LOW_M, AR6_SSP119_2150_LIKELY_HIGH_M],
            "interpretation": (
                "Sanity check only. V59 is driven by a different temperature pathway and the "
                "1995–2014→2026 offset is approximate."
            ),
        },
        "conditional_post_2400_restoration_to_zero_temperature": restoration_cases,
        "central_boundary_tests": {
            "hold_2400_temperature_constant": {
                "temperature_c": float(t0[2400]),
                "peak_by_10000_year": int(hold_peak["year"]),
                "peak_by_10000_additional_since_2026_m": float(hold_peak["gmsl_additional_since_2026_m"]),
                "first_nonpositive_rate_year": _first_nonpositive_rate_after(hold_rows, 2400),
                "interpretation": "No sea-level fall occurs by 10000 in this constant-positive-warming boundary test.",
            },
            "cool_to_0p2c_300y_efold": {
                "peak_year": int(floor_peak["year"]),
                "peak_additional_since_2026_m": float(floor_peak["gmsl_additional_since_2026_m"]),
                "first_10cm_below_peak_year": _first_after_peak_below(
                    floor_rows, floor_py, float(floor_peak["gmsl_additional_since_2026_m"]) - 0.10
                ),
                "first_return_to_2026_gmsl_year": _first_after_peak_below(floor_rows, floor_py, 0.0),
                "additional_gmsl_in_10000_m": float(floor_rows[-1]["gmsl_additional_since_2026_m"]),
                "interpretation": (
                    "With a residual 0.2 C warming floor, thermosteric/glacier components relax but "
                    "the modeled climate-driven GMSL remains above the 2026 level through 10000."
                ),
            },
        },
        "publication_rule": (
            "Report sea-level rise through 2400 as a V59 screening emulator driven by archived FaIR. "
            "Report sea-level fall/restoration dates only as explicit post-2400 boundary scenarios. "
            "Do not present the ~4th-millennium return-to-2026 result as a forecast."
        ),
        "source_urls": {
            "IPCC_AR6_WGI_CH9": "https://www.ipcc.ch/report/ar6/wg1/chapter/chapter-9/",
            "MENGEL_2016": "https://doi.org/10.1073/pnas.1500515113",
            "MENGEL_CODE": "https://github.com/matthiasmengel/sealevel",
            "NASA_2026_GMSL": "https://science.nasa.gov/earth/explore/earth-indicators/sea-leve/",
            "NASA_LAG_CONTEXT": "https://sealevel.nasa.gov/faq/13/how-long-have-sea-levels-been-rising-how-does-recent-sea-level-rise-compare-to-that-over-the-previous/",
        },
    }


def ocean_ph_v59(fair_rows: Sequence[Mapping]) -> Dict:
    """Drive the inherited compact carbonate/OAE screen with archived FaIR p50 CO2."""
    legacy = v53mod.run_v52_case("accelerated", "central", "baseline", 50.0)
    pathway_rows = legacy["durable_carbon"]["pathway_rows"]
    fair_co2 = fair_co2_by_year(fair_rows, "p50")

    # Internal year Y is a post-year-Y state; compare with FaIR timebound Y+1.
    carbon_rows = []
    for year in range(2026, 2400):
        carbon_rows.append({"year": year, "co2_ppm": fair_co2[year + 1]})

    ph_rows = v53mod.ocean_surface_state(carbon_rows, pathway_rows)
    minimum = min(ph_rows, key=lambda r: float(r["surface_ocean_ph"]))
    last = ph_rows[-1]

    def recovery_year(threshold: float) -> Optional[int]:
        r = next(
            (x for x in ph_rows
             if int(x["year"]) >= int(minimum["year"])
             and float(x["surface_ocean_ph"]) >= threshold),
            None,
        )
        return None if r is None else int(r["year"])

    legacy_h = legacy["headline"]
    return {
        "classification": (
            "Inherited compact fixed-T/S carbonate + OAE surface-ocean screen, now driven by archived "
            "FaIR median atmospheric CO2 rather than the superseded Joos concentration trajectory."
        ),
        "faIR_time_alignment": "V59 ocean year Y uses FaIR timebound Y+1 concentration.",
        "rows": ph_rows,
        "minimum_surface_ph": float(minimum["surface_ocean_ph"]),
        "minimum_surface_ph_year": int(minimum["year"]),
        "pH_2026": float(ph_rows[0]["surface_ocean_ph"]),
        "pH_at_end_of_canonical_2183": float(_year_row(ph_rows, 2183)["surface_ocean_ph"]),
        "pH_at_fair_2400_timebound": float(last["surface_ocean_ph"]),
        "pH_without_oae_at_fair_2400_timebound": float(last["surface_ocean_ph_without_oae"]),
        "recovery_year_pH_8_10": recovery_year(8.10),
        "recovery_year_pH_8_15": recovery_year(8.15),
        "recovery_year_pH_8_17": recovery_year(8.17),
        "legacy_internal_pH_at_or_below_280": legacy_h["surface_ocean_ph_at_or_below_280"],
        "legacy_internal_280_pH_status": "DIAGNOSTIC_ONLY_SUPERSEDED_CO2_DRIVER",
        "publication_rule": (
            "Use the FaIR-driven pH trajectory as the current V59 surface-ocean screening result. "
            "Do not claim global-ocean restoration from this compact mixed-layer model; full "
            "CO2SYS/PyCO2SYS, regional temperature/salinity and depth-resolved carbonate chemistry "
            "remain external validation needs."
        ),
        "source_urls": {
            "NOAA_OCEAN_ACIDIFICATION": "https://www.noaa.gov/education/resource-collections/ocean-coasts/ocean-acidification",
            "V53_LINEAGE_MODEL": "previous_branches/planetary_restoration_model_v53_1.py",
        },
    }


def run_v59() -> Dict:
    base = v58mod.run_v58()
    fair_rows = load_fair_timeseries()
    sl = sea_level_v59(fair_rows)
    ph = ocean_ph_v59(fair_rows)

    central = sl["archived_fair_horizon"]["central"]
    central_zero = sl["conditional_post_2400_restoration_to_zero_temperature"]["central"]

    headline = {
        **base["headline"],
        "model_version": MODEL_VERSION,
        "sea_level_module_added": True,
        "gmsl_additional_since_2026_central_2050_m": central["milestones"]["2050"]["additional_since_2026_m"],
        "gmsl_additional_since_2026_central_2100_m": central["milestones"]["2100"]["additional_since_2026_m"],
        "gmsl_additional_since_2026_central_2150_m": central["milestones"]["2150"]["additional_since_2026_m"],
        "gmsl_additional_since_2026_central_2300_m": central["milestones"]["2300"]["additional_since_2026_m"],
        "gmsl_additional_since_2026_central_2400_m": central["milestones"]["2400"]["additional_since_2026_m"],
        "gmsl_rate_central_2400_mm_yr": central["milestones"]["2400"]["rate_mm_yr"],
        "conditional_zero_warming_extension_peak_gmsl_year_central": central_zero["peak_gmsl_year"],
        "conditional_zero_warming_extension_peak_additional_gmsl_m_central": central_zero["peak_additional_since_2026_m"],
        "conditional_zero_warming_extension_return_to_2026_gmsl_year_central": central_zero["first_return_to_2026_gmsl_year"],
        "conditional_zero_warming_extension_within_5cm_preindustrial_component_year_central":
            central_zero["first_within_5cm_of_preindustrial_climate_component_state_year"],
        "surface_ocean_ph_external_fair_driven_minimum": ph["minimum_surface_ph"],
        "surface_ocean_ph_external_fair_driven_minimum_year": ph["minimum_surface_ph_year"],
        "surface_ocean_ph_external_fair_driven_at_canonical_2183": ph["pH_at_end_of_canonical_2183"],
        "surface_ocean_ph_external_fair_driven_at_fair_2400": ph["pH_at_fair_2400_timebound"],
        "surface_ocean_ph_recovery_year_8_10": ph["recovery_year_pH_8_10"],
        "surface_ocean_ph_recovery_year_8_15": ph["recovery_year_pH_8_15"],
        "surface_ocean_ph_recovery_year_8_17": ph["recovery_year_pH_8_17"],
        "sea_level_restoration_date_is_conditional": True,
        "ocean_ph_preserved": True,
    }

    return {
        "model_version": MODEL_VERSION,
        "release_label": RELEASE_LABEL,
        "release_status": RELEASE_STATUS,
        "classification": (
            "V59 preserves V58 and adds global-mean sea-level rise/fall screening plus an "
            "externally-driven surface-ocean pH screen."
        ),
        "headline": headline,
        "sea_level_v59": sl,
        "ocean_ph_v59": ph,
        "v58_full_architecture": {
            **base,
            "_v59_interpretation": {
                "status": "PRESERVED_FULL_V58_LINEAGE",
                "superseded_by": "V59",
                "do_not_use_v58_headline_as_current": True,
            },
        },
        "accounting_rules": {
            **base["accounting_rules"],
            "sea_level_global_mean_only": True,
            "sea_level_post_2400_fall_dates_are_conditional_scenarios": True,
            "sea_level_process_based_ice_sheet_validation_still_required": True,
            "ocean_ph_current_driver_is_archived_fair_p50_co2": True,
            "legacy_internal_ph_at_280_is_diagnostic_only": True,
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
    (data / "planetary_restoration_v59_results.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    _write_csv(data / "v59_sea_level_archived_fair_horizon.csv",
               result["sea_level_v59"]["archived_rows_flat"])

    milestone_rows = []
    for case, rec in result["sea_level_v59"]["archived_fair_horizon"].items():
        for year, m in rec["milestones"].items():
            milestone_rows.append({"case": case, "year": int(year), **m})
    _write_csv(data / "v59_sea_level_milestones.csv", milestone_rows)

    long_rows = []
    for case, rec in result["sea_level_v59"]["conditional_post_2400_restoration_to_zero_temperature"].items():
        long_rows.append({"case": case, **rec})
    _write_csv(data / "v59_sea_level_conditional_fall_milestones.csv", long_rows)
    _write_csv(data / "v59_ocean_ph_external_fair_driver.csv", result["ocean_ph_v59"]["rows"])


def run_tests(result: Dict) -> None:
    assert result["model_version"] == "59.0"
    assert result["headline"]["ocean_ph_preserved"] is True
    assert result["v58_full_architecture"]["_v59_interpretation"]["status"] == "PRESERVED_FULL_V58_LINEAGE"

    sl = result["sea_level_v59"]
    c = sl["archived_fair_horizon"]["central"]
    assert 0.28 < c["milestones"]["2100"]["additional_since_2026_m"] < 0.34
    assert 0.65 < c["milestones"]["2400"]["additional_since_2026_m"] < 0.76
    assert c["milestones"]["2400"]["rate_mm_yr"] > 0.0

    z = sl["conditional_post_2400_restoration_to_zero_temperature"]["central"]
    assert 2400 < z["peak_gmsl_year"] < 2500
    assert 0.65 < z["peak_additional_since_2026_m"] < 0.80
    assert 3500 < z["first_return_to_2026_gmsl_year"] < 4500
    assert 5500 < z["first_within_5cm_of_preindustrial_climate_component_state_year"] < 7500

    hold = sl["central_boundary_tests"]["hold_2400_temperature_constant"]
    assert hold["first_nonpositive_rate_year"] is None

    ph = result["ocean_ph_v59"]
    assert 8.04 < ph["minimum_surface_ph"] < 8.06
    assert 2028 <= ph["minimum_surface_ph_year"] <= 2040
    assert ph["recovery_year_pH_8_10"] is not None
    assert ph["recovery_year_pH_8_15"] is not None
    assert ph["recovery_year_pH_8_17"] is None
    assert 8.14 < ph["pH_at_fair_2400_timebound"] < 8.17


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tests", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()
    result = run_v59()
    run_tests(result)
    if not args.no_write:
        write_outputs(result)
    if args.tests:
        print("V59 SEA LEVEL + EXTERNAL-CO2 OCEAN PH TESTS PASSED")
    print(json.dumps(result["headline"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
