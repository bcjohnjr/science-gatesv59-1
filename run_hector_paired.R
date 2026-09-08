#!/usr/bin/env Rscript

# V59.1 paired Hector 3.5.0 experiment
# Removal-on vs removal-off from an identical Hector state at end-2025.
# This file is intended to replace only run_hector_paired.R.

suppressPackageStartupMessages(library(hector))

options(error = function() {
  cat("\n=== R TRACEBACK ===\n", file = stderr())
  traceback(20)
  quit(save = "no", status = 1, runLast = FALSE)
})

say <- function(...) {
  cat(sprintf(...), "\n")
  flush.console()
}

fail <- function(...) stop(sprintf(...), call. = FALSE)

root <- normalizePath(".", winslash = "/", mustWork = TRUE)
traj_path <- file.path(root, "external_validation_net_co2_trajectory.csv")
outdir <- root

say("Hector paired experiment starting")
say("Working directory: %s", root)
say("Hector package version: %s", as.character(packageVersion("hector")))

if (as.character(packageVersion("hector")) != "3.5.0") {
  fail("Expected Hector 3.5.0, found %s", as.character(packageVersion("hector")))
}
if (!file.exists(traj_path)) fail("Trajectory not found: %s", traj_path)

x <- read.csv(traj_path, check.names = FALSE, stringsAsFactors = FALSE)
need <- c(
  "year",
  "gross_co2_gtco2",
  "permafrost_co2_gtco2",
  "stored_carbon_reversal_gtco2",
  "cdr_gtco2",
  "net_co2_gtco2"
)
missing_cols <- setdiff(need, names(x))
if (length(missing_cols)) {
  fail("Trajectory is missing required columns: %s", paste(missing_cols, collapse = ", "))
}

x <- x[order(x$year), ]
if (nrow(x) == 0) fail("Trajectory is empty")
if (min(x$year) != 2026 || max(x$year) != 2183) {
  fail("Expected canonical years 2026-2183; got %s-%s", min(x$year), max(x$year))
}
if (anyDuplicated(x$year)) fail("Trajectory contains duplicate years")
if (any(!is.finite(as.matrix(x[, need[-1]])))) fail("Trajectory contains non-finite carbon values")

mass_check <-
  x$gross_co2_gtco2 +
  x$permafrost_co2_gtco2 +
  x$stored_carbon_reversal_gtco2 -
  x$cdr_gtco2
mass_err <- max(abs(mass_check - x$net_co2_gtco2))
if (mass_err >= 1e-9) fail("Trajectory mass-balance check failed; max error = %.12g GtCO2", mass_err)

# Match the archived validation extension convention: hold the terminal
# component fluxes fixed from 2184 through Hector's 2300 horizon.
last <- x[nrow(x), ]
if (max(x$year) < 2300) {
  ext_year <- (max(x$year) + 1L):2300L
  ext <- data.frame(
    year = ext_year,
    gross_co2_gtco2 = rep(last$gross_co2_gtco2, length(ext_year)),
    permafrost_co2_gtco2 = rep(last$permafrost_co2_gtco2, length(ext_year)),
    stored_carbon_reversal_gtco2 = rep(last$stored_carbon_reversal_gtco2, length(ext_year)),
    cdr_gtco2 = rep(last$cdr_gtco2, length(ext_year)),
    net_co2_gtco2 = rep(last$net_co2_gtco2, length(ext_year))
  )
  # Keep any extra diagnostic columns out of the Hector forcing table.
  x <- rbind(x[, names(ext)], ext)
}

yrs <- as.numeric(x$year)
if (!identical(yrs, as.numeric(2026:2300))) {
  fail("Extended trajectory must contain every year 2026-2300 exactly once")
}

# Hector's carbon-cycle input unit is Pg C/yr.
# 1 GtCO2 = (12.011 / 44.009) PgC.
co2_to_c <- 12.011 / 44.009
gross_source_gtco2 <-
  x$gross_co2_gtco2 +
  x$permafrost_co2_gtco2 +
  x$stored_carbon_reversal_gtco2
gross_c <- gross_source_gtco2 * co2_to_c
cdr_c <- x$cdr_gtco2 * co2_to_c
zero_c <- rep(0, length(yrs))

if (any(gross_c < 0)) fail("Gross carbon-source pathway contains negative values")
if (any(cdr_c < 0)) fail("CDR pathway contains negative values")

ini <- system.file("input", "hector_ssp245.ini", package = "hector")
if (!nzchar(ini) || !file.exists(ini)) {
  fail("hector_ssp245.ini not found in installed Hector package")
}

# Use Hector's own unit registry rather than relying on a duplicated unit string.
unit_ffi <- getunits(FFI_EMISSIONS())
unit_luc <- getunits(LUC_EMISSIONS())
unit_luc_uptake <- getunits(LUC_UPTAKE())
unit_daccs <- getunits(DACCS_UPTAKE())

say("Hector input file: %s", ini)
say("Input units: FFI=%s; LUC=%s; LUC uptake=%s; DACCS=%s",
    unit_ffi, unit_luc, unit_luc_uptake, unit_daccs)
say("Canonical cumulative CDR through 2183: %.6f GtCO2", sum(x$cdr_gtco2[x$year <= 2183]))
say("Peak annual CDR: %.6f GtCO2/yr", max(x$cdr_gtco2[x$year <= 2183]))

set_checked <- function(core, dates, var, values, unit, label) {
  say("  Setting %s for %d-%d", label, min(dates), max(dates))
  tryCatch(
    setvar(core, dates, var, values, unit),
    error = function(e) fail("setvar failed for %s: %s", label, conditionMessage(e))
  )
}

fetch_scalar <- function(df, variable_name, year) {
  z <- df[df$variable == variable_name & df$year == year, "value"]
  if (length(z) != 1 || !is.finite(z)) {
    fail("Expected one finite value for %s in %d; found %d", variable_name, year, length(z))
  }
  as.numeric(z)
}

run_case <- function(label, removal_on) {
  say("\n=== %s ===", label)
  core <- newcore(ini, suppresslogging = TRUE, name = label)
  on.exit(try(shutdown(core), silent = TRUE), add = TRUE)

  # Critical sequencing change: first run the unmodified SSP2-4.5 history to
  # end-2025.  The official Hector test suite uses this pattern when replacing
  # future time-series values.  Both paired cases therefore begin from the
  # exact same initialized/spun-up/historical state before any V59.1 forcing
  # is applied.
  say("  Running untouched Hector history through 2025")
  tryCatch(
    invisible(run(core, 2025)),
    error = function(e) fail("Historical Hector run failed for %s: %s", label, conditionMessage(e))
  )

  hist <- fetchvars(
    core,
    2025,
    vars = c(CONCENTRATIONS_CO2(), GLOBAL_TAS())
  )
  hist_co2 <- fetch_scalar(hist, CONCENTRATIONS_CO2(), 2025)
  hist_tas <- fetch_scalar(hist, GLOBAL_TAS(), 2025)
  say("  Common-state CO2 in 2025: %.9f ppm", hist_co2)
  say("  Common-state TAS in 2025: %.9f degC", hist_tas)

  # Replace only FUTURE carbon inputs.  Because current Hector date is 2025,
  # these assignments do not force a rewind/reset of the historical state.
  set_checked(core, yrs, FFI_EMISSIONS(), gross_c, unit_ffi,
              "FFI = gross + exported permafrost + stored-carbon reversal")
  set_checked(core, yrs, LUC_EMISSIONS(), zero_c, unit_luc,
              "LUC emissions = 0")
  set_checked(core, yrs, LUC_UPTAKE(), zero_c, unit_luc_uptake,
              "LUC uptake = 0")
  set_checked(core, yrs, DACCS_UPTAKE(), if (removal_on) cdr_c else zero_c,
              unit_daccs,
              if (removal_on) "DACCS = V59.1 CDR" else "DACCS = 0")

  say("  Running Hector from 2025 through 2300")
  tryCatch(
    invisible(run(core, 2300)),
    error = function(e) fail("Forward Hector run failed for %s: %s", label, conditionMessage(e))
  )

  out <- fetchvars(
    core,
    yrs,
    vars = c(CONCENTRATIONS_CO2(), GLOBAL_TAS())
  )
  if (nrow(out) < length(yrs) * 2) {
    fail("Unexpectedly short Hector output for %s: %d rows", label, nrow(out))
  }

  # Audit the actual carbon inputs stored by Hector at representative years.
  audit_years <- c(2026, 2043, 2100, 2183, 2300)
  forcing_audit <- fetchvars(
    core,
    audit_years,
    vars = c(FFI_EMISSIONS(), LUC_EMISSIONS(), LUC_UPTAKE(), DACCS_UPTAKE())
  )

  list(
    output = out,
    forcing_audit = forcing_audit,
    hist_co2 = hist_co2,
    hist_tas = hist_tas
  )
}

on_case <- run_case("removal-on / SSP245", TRUE)
off_case <- run_case("removal-off / SSP245", FALSE)

common_state_co2_error <- abs(on_case$hist_co2 - off_case$hist_co2)
common_state_tas_error <- abs(on_case$hist_tas - off_case$hist_tas)
if (common_state_co2_error > 1e-12 || common_state_tas_error > 1e-12) {
  fail(
    "Paired Hector common-state audit failed: CO2 error=%.12g ppm, TAS error=%.12g degC",
    common_state_co2_error, common_state_tas_error
  )
}
say("\nCommon-state audit PASSED")
say("  CO2 difference at 2025: %.12g ppm", common_state_co2_error)
say("  TAS difference at 2025: %.12g degC", common_state_tas_error)

on <- on_case$output
off <- off_case$output

co2_name <- CONCENTRATIONS_CO2()
co2_on <- on[on$variable == co2_name, c("year", "value")]
co2_off <- off[off$variable == co2_name, c("year", "value")]
names(co2_on)[2] <- "co2_on_ppm"
names(co2_off)[2] <- "co2_off_ppm"

pair <- merge(co2_on, co2_off, by = "year", all = FALSE)
pair <- pair[order(pair$year), ]
if (nrow(pair) != length(yrs)) {
  fail("Expected %d paired annual CO2 rows; found %d", length(yrs), nrow(pair))
}
if (!identical(as.numeric(pair$year), yrs)) {
  fail("Paired output years do not match 2026-2300 forcing years")
}

pair$delta_co2_ppm <- pair$co2_off_ppm - pair$co2_on_ppm
cum_cdr <- cumsum(x$cdr_gtco2)
pair$cumulative_cdr_gtco2 <- cum_cdr[match(pair$year, x$year)]

# Independent reporting conversion used by the FaIR paired experiment.
gtco2_per_ppm <- 2.124 * (44.009 / 12.011)
pair$apparent_response_fraction <- ifelse(
  pair$cumulative_cdr_gtco2 > 0,
  pair$delta_co2_ppm * gtco2_per_ppm / pair$cumulative_cdr_gtco2,
  NA_real_
)

if (any(!is.finite(pair$co2_on_ppm)) || any(!is.finite(pair$co2_off_ppm))) {
  fail("Non-finite atmospheric CO2 values in paired Hector result")
}
if (any(pair$delta_co2_ppm < -1e-9)) {
  fail("Removal-on produces higher CO2 than removal-off in at least one year beyond numerical tolerance")
}

write.csv(pair, file.path(outdir, "hector_paired_attribution.csv"), row.names = FALSE)
write.csv(on, file.path(outdir, "hector_removal_on_long.csv"), row.names = FALSE)
write.csv(off, file.path(outdir, "hector_removal_off_long.csv"), row.names = FALSE)
write.csv(on_case$forcing_audit,
          file.path(outdir, "hector_removal_on_forcing_audit.csv"), row.names = FALSE)
write.csv(off_case$forcing_audit,
          file.path(outdir, "hector_removal_off_forcing_audit.csv"), row.names = FALSE)

year_value <- function(v, y) {
  z <- pair[pair$year == y, v]
  if (length(z) != 1) return(NA_real_)
  as.numeric(z)
}

min_i <- which.min(pair$co2_on_ppm)
summary <- list(
  model = "Hector",
  version = "3.5.0",
  experiment = "paired removal-on/removal-off from exact common state at end-2025",
  background_nonco2 = "Hector SSP2-4.5; identical in both paired runs",
  common_state_year = 2025,
  common_state_co2_on_ppm = on_case$hist_co2,
  common_state_co2_off_ppm = off_case$hist_co2,
  common_state_co2_abs_error_ppm = common_state_co2_error,
  common_state_tas_on_degc = on_case$hist_tas,
  common_state_tas_off_degc = off_case$hist_tas,
  common_state_tas_abs_error_degc = common_state_tas_error,
  carbon_forcing = paste0(
    "2026 onward: FFI = gross + exported permafrost + stored-carbon reversal; ",
    "LUC emissions = 0; LUC uptake = 0; DACCS = anthropogenic CDR in removal-on and 0 in removal-off"
  ),
  extension = "Terminal V59.1 component fluxes held from 2184 through 2300",
  first_year = min(yrs),
  last_year = max(yrs),
  canonical_cdr_2026_2183_gtco2 = sum(x$cdr_gtco2[x$year <= 2183]),
  peak_cdr_2026_2183_gtco2_per_year = max(x$cdr_gtco2[x$year <= 2183]),
  gtco2_per_ppm_reporting_conversion = gtco2_per_ppm,
  minimum_on_ppm = pair$co2_on_ppm[min_i],
  minimum_on_year = pair$year[min_i],
  co2_on_2200 = year_value("co2_on_ppm", 2200),
  co2_on_2300 = year_value("co2_on_ppm", 2300),
  co2_off_2200 = year_value("co2_off_ppm", 2200),
  co2_off_2300 = year_value("co2_off_ppm", 2300),
  delta_co2_2200_ppm = year_value("delta_co2_ppm", 2200),
  delta_co2_2300_ppm = year_value("delta_co2_ppm", 2300),
  response_fraction_2200 = year_value("apparent_response_fraction", 2200),
  response_fraction_2300 = year_value("apparent_response_fraction", 2300),
  cross_model_common_background_gate = paste0(
    "OPEN: this Hector pair holds Hector SSP2-4.5 non-CO2 background common within Hector. ",
    "It does not by itself prescribe the same future non-CO2 forcing used in the FaIR neutral-background control."
  )
)

jsonlite::write_json(
  summary,
  file.path(outdir, "hector_science_summary.json"),
  pretty = TRUE,
  auto_unbox = TRUE,
  digits = NA
)

say("\n=== HECTOR PAIRED EXPERIMENT COMPLETE ===")
cat(jsonlite::toJSON(summary, pretty = TRUE, auto_unbox = TRUE, digits = NA), "\n")
say("Outputs written:")
say("  hector_paired_attribution.csv")
say("  hector_removal_on_long.csv")
say("  hector_removal_off_long.csv")
say("  hector_science_summary.json")
say("  hector_removal_on_forcing_audit.csv")
say("  hector_removal_off_forcing_audit.csv")
