#!/usr/bin/env Rscript
suppressPackageStartupMessages(library(hector))

root <- normalizePath('.', winslash='/', mustWork=TRUE)
traj_path <- file.path(root, 'external_validation_net_co2_trajectory.csv')
outdir <- root

x <- read.csv(traj_path, check.names=FALSE)
need <- c('year','gross_co2_gtco2','permafrost_co2_gtco2','stored_carbon_reversal_gtco2','cdr_gtco2','net_co2_gtco2')
stopifnot(all(need %in% names(x)))
x <- x[order(x$year),]
stopifnot(min(x$year) == 2026, max(x$year) == 2183)
check <- x$gross_co2_gtco2 + x$permafrost_co2_gtco2 + x$stored_carbon_reversal_gtco2 - x$cdr_gtco2
stopifnot(max(abs(check - x$net_co2_gtco2)) < 1e-9)

# Match the archived extension convention: hold the terminal component fluxes through 2300.
last <- x[nrow(x),]
if (max(x$year) < 2300) {
  ext_year <- (max(x$year)+1):2300
  ext <- data.frame(
    year=ext_year,
    gross_co2_gtco2=last$gross_co2_gtco2,
    permafrost_co2_gtco2=last$permafrost_co2_gtco2,
    stored_carbon_reversal_gtco2=last$stored_carbon_reversal_gtco2,
    cdr_gtco2=last$cdr_gtco2,
    net_co2_gtco2=last$net_co2_gtco2
  )
  x <- rbind(x, ext)
}

# Hector expects PgC/yr; 1 GtCO2 = (12.011/44.009) PgC.
co2_to_c <- 12.011 / 44.009
gross_c <- (x$gross_co2_gtco2 + x$permafrost_co2_gtco2 + x$stored_carbon_reversal_gtco2) * co2_to_c
cdr_c <- x$cdr_gtco2 * co2_to_c
yrs <- x$year

run_case <- function(label, removal_on) {
  ini <- system.file('input/hector_ssp245.ini', package='hector')
  if (ini == '') stop('hector_ssp245.ini not found in installed Hector package')
  core <- newcore(ini, suppresslogging=TRUE, name=label)
  on.exit(try(shutdown(core), silent=TRUE), add=TRUE)
  setvar(core, yrs, FFI_EMISSIONS(), gross_c, 'Pg C/yr')
  setvar(core, yrs, LUC_EMISSIONS(), rep(0, length(yrs)), 'Pg C/yr')
  setvar(core, yrs, DACCS_UPTAKE(), if (removal_on) cdr_c else rep(0, length(yrs)), 'Pg C/yr')
  invisible(run(core, max(yrs)))
  fetchvars(core, yrs, vars=c(CONCENTRATIONS_CO2(), GLOBAL_TAS()))
}

on <- run_case('removal-on / SSP245', TRUE)
off <- run_case('removal-off / SSP245', FALSE)
co2_on <- on[on$variable == CONCENTRATIONS_CO2(), c('year','value')]
co2_off <- off[off$variable == CONCENTRATIONS_CO2(), c('year','value')]
names(co2_on)[2] <- 'co2_on_ppm'; names(co2_off)[2] <- 'co2_off_ppm'
pair <- merge(co2_on, co2_off, by='year')
pair$delta_co2_ppm <- pair$co2_off_ppm - pair$co2_on_ppm
cum_cdr <- cumsum(x$cdr_gtco2)
pair$cumulative_cdr_gtco2 <- cum_cdr[match(pair$year, x$year)]
gtco2_per_ppm <- 2.124 * (44.009/12.011)
pair$apparent_response_fraction <- ifelse(pair$cumulative_cdr_gtco2 > 0,
  pair$delta_co2_ppm * gtco2_per_ppm / pair$cumulative_cdr_gtco2, NA_real_)
write.csv(pair, file.path(outdir, 'hector_paired_attribution.csv'), row.names=FALSE)
write.csv(on, file.path(outdir, 'hector_removal_on_long.csv'), row.names=FALSE)
write.csv(off, file.path(outdir, 'hector_removal_off_long.csv'), row.names=FALSE)

summary <- list(
  model='Hector', version='3.5.0',
  background_nonco2='Hector SSP2-4.5; identical in removal-on and removal-off pair',
  carbon_forcing='FFI = gross + permafrost + stored-carbon reversal; LUC=0; DACCS = anthropogenic CDR in removal-on and 0 in removal-off',
  extension='Terminal component fluxes held from 2184 through 2300 to match the archived benchmark convention',
  first_year=min(yrs), last_year=max(yrs),
  minimum_on_ppm=min(pair$co2_on_ppm),
  minimum_on_year=pair$year[which.min(pair$co2_on_ppm)],
  co2_on_2200=pair$co2_on_ppm[pair$year==2200],
  co2_on_2300=pair$co2_on_ppm[pair$year==2300]
)
jsonlite::write_json(summary, file.path(outdir,'hector_science_summary.json'), pretty=TRUE, auto_unbox=TRUE)
cat(jsonlite::toJSON(summary, pretty=TRUE, auto_unbox=TRUE), '\n')
