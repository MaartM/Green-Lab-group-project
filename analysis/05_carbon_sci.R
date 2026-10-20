# 5. Carbon footprint with the Software Carbon Intensity (SCI) specification

section("5. Carbon footprint (SCI)")

hours <- grid_intensity(min(runs$start), max(runs$start + runs$time_s))
lifespan_s <- LIFESPAN_YEARS * 365.25 * 86400

carbon <- data.frame(
  run_id = runs$run_id, strategy = runs$strategy, start = runs$start, time_s = runs$time_s,
  n_queries = runs$n_queries, n_correct = runs$n_correct,
  energy_kwh = runs$energy_j / 3.6e6,
  intensity_g_per_kwh = run_intensity(runs$start, runs$time_s, hours)
)
carbon$operational_g <- carbon$energy_kwh * carbon$intensity_g_per_kwh
carbon$embodied_g <- 1000 * sum(EMBODIED_KG) * carbon$time_s / lifespan_s * RESOURCE_SHARE
carbon$carbon_g <- carbon$operational_g + carbon$embodied_g
carbon$sci_per_question_mg <- 1000 * carbon$carbon_g / carbon$n_queries
carbon$sci_per_correct_mg <- 1000 * carbon$carbon_g / carbon$n_correct

cat("\n5.1 Grid carbon intensity during the experiment (NED, hourly, g CO2e/kWh)\n")
during <- hours[hours$valid_to > min(runs$start) & hours$valid_from < max(runs$start + runs$time_s), ]
cat("hours:", nrow(during), "| from", format(during$valid_from[1], "%Y-%m-%d %H:%M"),
    "to", format(tail(during$valid_to, 1), "%Y-%m-%d %H:%M"), "UTC\n")
print(summary(1000 * during$emission_factor_kg_per_kwh))
cat("intensity per run, by strategy:\n")
print(aggregate(intensity_g_per_kwh ~ strategy, carbon, function(x) round(c(mean = mean(x), sd = sd(x), min = min(x), max = max(x)), 1)))

cat("\n5.2 Embodied emissions\n")
cat(sprintf("TE = %s = %.1f kg CO2e, EL = %d years, RS = %g: %.2f mg CO2e per second of run\n",
            paste(names(EMBODIED_KG), EMBODIED_KG, sep = " ", collapse = " + "), sum(EMBODIED_KG),
            LIFESPAN_YEARS, RESOURCE_SHARE, 1e6 * sum(EMBODIED_KG) / lifespan_s * RESOURCE_SHARE))

cat("\n5.3 SCI per strategy (mean over runs; g CO2e per run, mg CO2e per functional unit)\n")
summary_columns <- c("energy_kwh", "intensity_g_per_kwh", "operational_g", "embodied_g", "carbon_g",
                     "sci_per_question_mg", "sci_per_correct_mg")
sci <- aggregate(carbon[summary_columns], list(strategy = carbon$strategy), mean)
sci_sd <- aggregate(carbon[c("sci_per_question_mg", "sci_per_correct_mg")], list(strategy = carbon$strategy), sd)
sci$sci_per_question_sd <- sci_sd$sci_per_question_mg
sci$sci_per_correct_sd <- sci_sd$sci_per_correct_mg
sci$embodied_pct <- 100 * sci$embodied_g / sci$carbon_g
print(sci, row.names = FALSE, digits = 4)
per <- function(column) setNames(sci[[column]], sci$strategy)
for (column in c("sci_per_question_mg", "sci_per_correct_mg")) {
  cat(sprintf("%s: R vs L %+.1f%%, R vs S %+.1f%%\n", column,
              100 * (per(column)[["R"]] / per(column)[["L"]] - 1), 100 * (per(column)[["R"]] / per(column)[["S"]] - 1)))
}
# The grid changes during the experiment, so strategies also differ by when their runs fell.
# With I fixed at the experiment's energy-weighted mean, only E and M differ between strategies.
fixed_intensity <- sum(carbon$operational_g) / sum(carbon$energy_kwh)
fixed <- aggregate(1000 * (energy_kwh * fixed_intensity + embodied_g) / n_correct ~ strategy, carbon, mean)
names(fixed)[2] <- "sci_per_correct_mg"
cat(sprintf("with I fixed at %.1f g CO2e/kWh, SCI per correct answer (mg CO2e):\n", fixed_intensity))
print(fixed, row.names = FALSE, digits = 4)

cat("\n5.4 Footprint of all measured runs (g CO2e)\n")
totals <- colSums(carbon[c("energy_kwh", "operational_g", "embodied_g", "carbon_g")])
print(round(totals, 3))
cat("excludes the warm-up, the pauses between runs and everything outside the measured CPU and GPUs\n")

carbon_dir <- file.path(OUT_DIR, "carbon")
dir.create(carbon_dir, showWarnings = FALSE)
write.csv(transform(carbon, start = format(start, "%Y-%m-%dT%H:%M:%SZ")),
          file.path(carbon_dir, "sci_per_run.csv"), row.names = FALSE)
write.csv(sci, file.path(carbon_dir, "sci_summary.csv"), row.names = FALSE)

parts <- data.frame(strategy = factor(unname(LABELS[as.character(sci$strategy)]), levels = rev(LABELS)),
                    part = factor(rep(c("Operational (E x I)", "Embodied (M)"), each = nrow(sci)),
                                  levels = c("Operational (E x I)", "Embodied (M)")),
                    mg = c(sci$operational_g, sci$embodied_g) / sci$carbon_g * sci$sci_per_correct_mg)
save_plot(ggplot(parts, aes(mg, strategy, fill = part)) +
            geom_col(width = 0.6, colour = "#fcfcfb", position = position_stack(reverse = TRUE)) +
            scale_fill_manual(values = c("#52514e", "#c3c2b7"), name = NULL) +
            labs(x = "SCI (mg CO2e per correct answer)", y = NULL, title = "Carbon per correct answer by component"),
          FINAL_FIGURES, "sci_per_correct.png", 6, 3)

# Bars: NED's hourly values. Points: each run at its midpoint and the intensity assigned to it
# (between two bars when the run crosses an hour).
save_plot(ggplot() +
            geom_rect(data = during, aes(xmin = valid_from, xmax = valid_to, ymin = 0,
                                         ymax = 1000 * emission_factor_kg_per_kwh),
                      fill = "#e1e0d9", colour = "#fcfcfb") +
            geom_point(data = carbon, aes(start + time_s / 2, intensity_g_per_kwh, colour = strategy), size = 1.5) +
            scale_colour_manual(values = COLORS, labels = LABELS, name = NULL) +
            scale_x_datetime(date_labels = "%H:%M", timezone = "Europe/Amsterdam") +
            scale_y_continuous(limits = c(0, NA), expand = expansion(mult = c(0, 0.05))) +
            labs(x = "Time (Amsterdam), grey bars: hourly values from NED",
                 y = "Grid carbon intensity\n(g CO2e/kWh)"),
          EXPLORATORY, "grid_intensity.png", 8, 3.2)
