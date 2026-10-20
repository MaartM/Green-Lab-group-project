# 2. Exploration: descriptive statistics, distributions, temporal dependence, outliers.

section("2. Exploration")

cat("\n2.1 Descriptive statistics per run-level variable\n")
for (variable in names(RUN_VARIABLES)) {
  cat("\n", RUN_VARIABLES[[variable]], "\n", sep = "")
  print(signif(describe(runs, variable), 6))
}

long <- do.call(rbind, lapply(names(RUN_VARIABLES), function(variable) {
  data.frame(variable = RUN_VARIABLES[[variable]], strategy = runs$strategy, value = runs[[variable]])
}))
long$variable <- factor(long$variable, levels = RUN_VARIABLES)
save_plot(ggplot(long, aes(strategy, value)) +
            geom_boxplot(outlier.shape = NA, width = 0.5, colour = "#898781") +
            geom_jitter(aes(colour = strategy), width = 0.12, height = 0, size = 0.9, alpha = 0.8) +
            facet_wrap(~variable, scales = "free_y", ncol = 4) +
            scale_colour_manual(values = COLORS, guide = "none") +
            labs(x = NULL, y = NULL) + theme(strip.text = element_text(size = 7)),
          EXPLORATORY, "distributions.png", 13, 9)

cat("\n2.3 Chronological order and temporal dependence (energy per query)\n")
runs$residual_energy_per_query_j <- runs$energy_per_query_j - ave(runs$energy_per_query_j, runs$strategy)
for (strategy in STRATEGIES) {
  subset <- runs[runs$strategy == strategy, ]
  test <- cor.test(subset$order, subset$energy_per_query_j, method = "spearman", exact = FALSE)
  cat(sprintf("%s: Spearman rho(order, energy per query) = %+.2f, p = %.3f\n", strategy, test$estimate, test$p.value))
}
save_plot(ggplot(runs, aes(order, residual_energy_per_query_j, colour = strategy)) +
            geom_hline(yintercept = 0, colour = "#c3c2b7") + geom_point(size = 1.5) +
            scale_colour_manual(values = COLORS, labels = LABELS, name = NULL) +
            labs(x = "Run position in the experiment (chronological)",
                 y = "Energy per query minus\nstrategy mean (J)"),
          EXPLORATORY, "residuals_over_time.png", 8, 3.2)

cat("\nLjung-Box test of the residuals in chronological order\n")
residuals <- runs$residual_energy_per_query_j[order(runs$order)]
for (lag in c(1, 5, 10)) {
  test <- Box.test(residuals, lag = lag, type = "Ljung-Box")
  cat(sprintf("lag %2d: Q = %.2f, p = %.4f\n", lag, test$statistic, test$p.value))
}
autocorrelation <- acf(residuals, lag.max = 15, plot = FALSE)
save_plot(ggplot(data.frame(lag = autocorrelation$lag[, 1, 1], acf = autocorrelation$acf[, 1, 1]), aes(lag, acf)) +
            annotate("rect", xmin = -Inf, xmax = Inf, ymin = -1.96 / sqrt(length(residuals)),
                     ymax = 1.96 / sqrt(length(residuals)), fill = "#e1e0d9") +
            geom_segment(aes(xend = lag, yend = 0), colour = "#52514e") + geom_point(colour = "#52514e") +
            labs(x = "Lag (runs)", y = "Autocorrelation", title = "Autocorrelation of energy-per-query residuals"),
          EXPLORATORY, "residuals_autocorrelation.png", 6, 2.8)

temperatures <- rbind(data.frame(gpu = "GPU 0", order = runs$order, strategy = runs$strategy, temp = runs$gpu0_start_temp_c),
                      data.frame(gpu = "GPU 1", order = runs$order, strategy = runs$strategy, temp = runs$gpu1_start_temp_c))
save_plot(ggplot(temperatures, aes(order, temp, colour = strategy)) + geom_point(size = 1.2) +
            facet_wrap(~gpu) + scale_colour_manual(values = COLORS, labels = LABELS, name = NULL) +
            labs(x = "Run position in the experiment", y = "Temperature at run start (\u00b0C)"),
          EXPLORATORY, "gpu_start_temperature.png", 10, 3)

cat("\n2.4 Outliers: runs more than 3 standard deviations from their strategy's mean\n")
outliers <- do.call(rbind, lapply(names(RUN_VARIABLES), function(variable) {
  z <- (runs[[variable]] - ave(runs[[variable]], runs$strategy)) /
    ave(runs[[variable]], runs$strategy, FUN = sd)
  flagged <- which(abs(z) > 3)
  if (length(flagged)) data.frame(variable = variable, run_id = runs$run_id[flagged],
                                  order = runs$order[flagged], z = z[flagged])
}))
print(outliers)
