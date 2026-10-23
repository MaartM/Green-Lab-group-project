# 2. Exploration: descriptive statistics, distributions, temporal
# dependence, GPU temperatures, and outliers.

section("2. Exploration")

presentation_theme <- theme_minimal(base_size = 11) +
  theme(
    plot.title = element_text(face = "bold", size = 13),
    axis.title = element_text(colour = "#3f3f3b"),
    panel.grid.minor = element_blank(),
    legend.position = "bottom",
    strip.text = element_text(face = "bold", size = 9)
  )

# 2.1 Descriptive statistics --------------------------------------------------

cat("\n2.1 Descriptive statistics per run-level variable\n")

for (variable in names(RUN_VARIABLES)) {
  cat("\n", RUN_VARIABLES[[variable]], "\n", sep = "")
  print(signif(describe(runs, variable), 6))
}

# Long-format data for distribution plots.
long <- do.call(rbind, lapply(names(RUN_VARIABLES), function(variable) {
  data.frame(
    variable = RUN_VARIABLES[[variable]],
    strategy = runs$strategy,
    value = runs[[variable]]
  )
}))

long$variable <- factor(long$variable, levels = RUN_VARIABLES)
long$strategy <- factor(long$strategy, levels = STRATEGIES)

save_plot(
  ggplot(long, aes(strategy, value, fill = strategy)) +
    geom_boxplot(
      outlier.shape = NA, width = 0.55, alpha = 0.55,
      colour = "#666660"
    ) +
    geom_point(
      aes(colour = strategy),
      position = position_jitter(width = 0.12, height = 0, seed = 42),
      size = 1.1, alpha = 0.7
    ) +
    facet_wrap(~variable, scales = "free_y", ncol = 4) +
    scale_fill_manual(values = COLORS, labels = LABELS, guide = "none") +
    scale_colour_manual(values = COLORS, labels = LABELS, guide = "none") +
    scale_x_discrete(labels = LABELS) +
    labs(
      title = "Run-level distributions by strategy",
      x = NULL, y = NULL
    ) +
    presentation_theme,
  EXPLORATORY, "distributions.png", 13, 9
)

# Compare means and standard deviations across strategies.
summary_data <- do.call(rbind, lapply(names(RUN_VARIABLES), function(variable) {
  do.call(rbind, lapply(STRATEGIES, function(strategy) {
    values <- runs[[variable]][runs$strategy == strategy]
    data.frame(
      variable = RUN_VARIABLES[[variable]],
      strategy = strategy,
      mean = mean(values, na.rm = TRUE),
      sd = sd(values, na.rm = TRUE)
    )
  }))
}))

summary_data$variable <- factor(
  summary_data$variable, levels = RUN_VARIABLES
)
summary_data$strategy <- factor(
  summary_data$strategy, levels = STRATEGIES
)

save_plot(
  ggplot(summary_data, aes(strategy, mean, colour = strategy)) +
    geom_point(size = 2.5) +
    geom_errorbar(
      aes(ymin = mean - sd, ymax = mean + sd),
      width = 0.15, linewidth = 0.6
    ) +
    facet_wrap(~variable, scales = "free_y", ncol = 4) +
    scale_colour_manual(values = COLORS, labels = LABELS, name = NULL) +
    scale_x_discrete(labels = LABELS) +
    labs(
      title = "Mean run-level metrics and standard deviations",
      subtitle = "Error bars show ±1 standard deviation, not confidence intervals",
      x = NULL, y = NULL
    ) +
    presentation_theme,
  EXPLORATORY, "strategy_mean_comparison.png", 13, 8
)

# 2.2 Chronological order and temporal dependence -----------------------------

cat("\n2.2 Chronological order and temporal dependence (energy per query)\n")

runs$residual_energy_per_query_j <-
  runs$energy_per_query_j -
  ave(runs$energy_per_query_j, runs$strategy)

for (strategy in STRATEGIES) {
  subset <- runs[runs$strategy == strategy, ]
  test <- cor.test(
    subset$order,
    subset$energy_per_query_j,
    method = "spearman",
    exact = FALSE
  )

  cat(sprintf(
    "%s: Spearman rho(order, energy per query) = %+.2f, p = %.3f\n",
    strategy, test$estimate, test$p.value
  ))
}

save_plot(
  ggplot(
    runs,
    aes(order, residual_energy_per_query_j, colour = strategy)
  ) +
    geom_hline(yintercept = 0, colour = "#b8b7b0", linewidth = 0.6) +
    geom_line(aes(group = strategy), alpha = 0.45, linewidth = 0.45) +
    geom_point(size = 1.8, alpha = 0.9) +
    scale_colour_manual(values = COLORS, labels = LABELS, name = NULL) +
    labs(
      title = "Energy deviations over experiment time",
      subtitle = "Each run is centered on its strategy's mean energy per query",
      x = "Run position in the experiment (chronological)",
      y = "Energy deviation (J per query)"
    ) +
    presentation_theme,
  EXPLORATORY, "residuals_over_time.png", 8, 3.5
)

# Ljung-Box tests on residuals ordered chronologically.
cat("\nLjung-Box test of the residuals in chronological order\n")

residuals <- runs$residual_energy_per_query_j[order(runs$order)]

for (lag in c(1, 5, 10)) {
  test <- Box.test(residuals, lag = lag, type = "Ljung-Box")
  cat(sprintf(
    "lag %2d: Q = %.2f, p = %.4f\n",
    lag, test$statistic, test$p.value
  ))
}

autocorrelation <- acf(residuals, lag.max = 15, plot = FALSE)

acf_data <- data.frame(
  lag = as.numeric(autocorrelation$lag[, 1, 1]),
  acf = as.numeric(autocorrelation$acf[, 1, 1])
)

acf_bound <- 1.96 / sqrt(length(residuals))

save_plot(
  ggplot(acf_data, aes(lag, acf)) +
    annotate(
      "rect",
      xmin = -Inf, xmax = Inf,
      ymin = -acf_bound, ymax = acf_bound,
      fill = "#e5e4dc", alpha = 0.8
    ) +
    geom_hline(yintercept = 0, colour = "#777770") +
    geom_segment(
      aes(xend = lag, yend = 0),
      colour = "#52514e", linewidth = 0.6
    ) +
    geom_point(colour = "#2a78d6", size = 2) +
    labs(
      title = "Autocorrelation of energy residuals",
      subtitle = "Shaded band is an approximate 95% reference interval",
      x = "Lag (runs)", y = "Autocorrelation"
    ) +
    presentation_theme,
  EXPLORATORY, "residuals_autocorrelation.png", 6.5, 3.2
)

# 2.3 GPU starting temperatures ------------------------------------------------

cat("\n2.3 GPU starting temperatures\n")

temperatures <- rbind(
  data.frame(
    gpu = "GPU 0 (9B model)",
    order = runs$order,
    strategy = runs$strategy,
    temp = runs$gpu0_start_temp_c
  ),
  data.frame(
    gpu = "GPU 1 (2B model)",
    order = runs$order,
    strategy = runs$strategy,
    temp = runs$gpu1_start_temp_c
  )
)

temperature_summary <- aggregate(
  temp ~ gpu + strategy,
  temperatures,
  function(x) mean(x, na.rm = TRUE)
)
names(temperature_summary)[3] <- "mean_temp_c"
print(temperature_summary, row.names = FALSE)

save_plot(
  ggplot(temperatures, aes(order, temp, colour = strategy)) +
    geom_line(aes(group = strategy), alpha = 0.35, linewidth = 0.4) +
    geom_point(size = 1.5, alpha = 0.85) +
    facet_wrap(~gpu, scales = "free_y") +
    scale_colour_manual(values = COLORS, labels = LABELS, name = NULL) +
    labs(
      title = "GPU temperature at run start",
      x = "Run position in the experiment",
      y = "Starting temperature (°C)"
    ) +
    presentation_theme,
  EXPLORATORY, "gpu_start_temperature.png", 10, 3.5
)

# 2.4 Outliers ----------------------------------------------------------------

cat("\n2.4 Outliers: runs more than 3 standard deviations from their strategy's mean\n")

outliers <- do.call(rbind, lapply(names(RUN_VARIABLES), function(variable) {
  values <- runs[[variable]]
  strategy_mean <- ave(values, runs$strategy, FUN = function(x) {
    mean(x, na.rm = TRUE)
  })
  strategy_sd <- ave(values, runs$strategy, FUN = function(x) {
    sd(x, na.rm = TRUE)
  })

  z <- (values - strategy_mean) / strategy_sd
  flagged <- which(is.finite(z) & abs(z) > 3)

  if (length(flagged)) {
    data.frame(
      variable = RUN_VARIABLES[[variable]],
      run_id = runs$run_id[flagged],
      order = runs$order[flagged],
      strategy = runs$strategy[flagged],
      value = values[flagged],
      z = z[flagged]
    )
  } else {
    NULL
  }
}))

if (is.null(outliers) || nrow(outliers) == 0) {
  cat("No runs exceeded the 3-standard-deviation threshold.\n")
} else {
  print(outliers, row.names = FALSE)

  outliers$variable <- factor(
    outliers$variable,
    levels = rev(RUN_VARIABLES)
  )
  outliers$strategy <- factor(
    outliers$strategy,
    levels = STRATEGIES
  )

  save_plot(
    ggplot(
      outliers,
      aes(z, variable, colour = strategy)
    ) +
      geom_vline(
        xintercept = c(-3, 3),
        linetype = "dashed",
        colour = "#88877f"
      ) +
      geom_point(size = 3, alpha = 0.9) +
      geom_text(
        aes(label = paste0("run ", run_id)),
        nudge_y = 0.18,
        size = 2.8,
        show.legend = FALSE,
        check_overlap = TRUE
      ) +
      scale_colour_manual(values = COLORS, labels = LABELS, name = NULL) +
      labs(
        title = "Runs flagged as potential outliers",
        subtitle = "Points lie more than 3 within-strategy standard deviations from the mean",
        x = "Standardized deviation (z-score)",
        y = NULL
      ) +
      presentation_theme,
    EXPLORATORY, "outlier_runs.png", 9, 5
  )
}

# 2.1b Compact distribution plots with individual observations ---------------

cat("\n2.1b Compact run-level distributions with minimum/maximum markers\n")

# Violin + box plot + individual observations.
# Min/max are marked explicitly; all runs remain visible.
#
# Metrics are shown in separate panels with independent y-scales.
# The plots are intended to complement distributions.png, not replace it.

distribution_data <- long
distribution_data <- distribution_data[
  is.finite(distribution_data$value) &
    !is.na(distribution_data$strategy),
]

distribution_data$variable <- factor(
  distribution_data$variable,
  levels = RUN_VARIABLES
)
distribution_data$strategy <- factor(
  distribution_data$strategy,
  levels = STRATEGIES
)

# Compute observed extrema per metric and strategy.
extrema_data <- do.call(rbind, lapply(
  split(
    distribution_data,
    interaction(
      distribution_data$variable,
      distribution_data$strategy,
      drop = TRUE
    )
  ),
  function(d) {
    if (nrow(d) == 0) return(NULL)

    data.frame(
      variable = as.character(d$variable[1]),
      strategy = as.character(d$strategy[1]),
      min_value = min(d$value),
      max_value = max(d$value)
    )
  }
))

if (nrow(extrema_data) > 0) {
  extrema_data$variable <- factor(
    extrema_data$variable,
    levels = RUN_VARIABLES
  )
  extrema_data$strategy <- factor(
    extrema_data$strategy,
    levels = STRATEGIES
  )
}

compact_distribution_plot <- ggplot(
  distribution_data,
  aes(x = strategy, y = value, fill = strategy, colour = strategy)
) +
  # Distribution shape, with a restrained width.
  geom_violin(
    trim = TRUE,
    scale = "width",
    width = 0.82,
    alpha = 0.20,
    linewidth = 0.35,
    colour = NA
  ) +
  # Median, interquartile range, and whiskers.
  geom_boxplot(
    width = 0.20,
    outlier.shape = NA,
    alpha = 0.55,
    linewidth = 0.45,
    colour = "#555550"
  ) +
  # Each point represents an individual run.
  geom_point(
    position = position_jitter(
      width = 0.09,
      height = 0,
      seed = 42
    ),
    size = 1.35,
    alpha = 0.78
  ) +
  # Minimum: downward triangle; maximum: upward triangle.
  geom_point(
    data = extrema_data,
    aes(
      x = strategy,
      y = min_value,
      colour = strategy
    ),
    inherit.aes = FALSE,
    shape = 25,
    fill = "white",
    stroke = 0.8,
    size = 2.7,
    position = position_nudge(x = -0.17)
  ) +
  geom_point(
    data = extrema_data,
    aes(
      x = strategy,
      y = max_value,
      colour = strategy
    ),
    inherit.aes = FALSE,
    shape = 24,
    fill = "white",
    stroke = 0.8,
    size = 2.7,
    position = position_nudge(x = -0.17)
  ) +
  facet_wrap(
    ~ variable,
    scales = "free_y",
    ncol = 4
  ) +
  scale_fill_manual(
    values = COLORS,
    labels = LABELS,
    guide = "none"
  ) +
  scale_colour_manual(
    values = COLORS,
    labels = LABELS,
    guide = "none"
  ) +
  scale_x_discrete(labels = LABELS) +
  labs(
    title = "Run-level distributions by strategy",
    subtitle = paste(
      "Points = individual runs;",
      "box = median and IQR;",
      "triangles = observed minimum and maximum"
    ),
    x = NULL,
    y = NULL,
    caption = paste(
      "Violin widths are normalized within each metric.",
      "Extreme markers are offset slightly left for visibility."
    )
  ) +
  presentation_theme +
  theme(
    plot.title = element_text(face = "bold", size = 12),
    plot.subtitle = element_text(size = 9),
    plot.caption = element_text(size = 8, colour = "#666660"),
    panel.spacing = grid::unit(0.8, "lines"),
    axis.text.x = element_text(size = 8),
    strip.text = element_text(size = 9)
  )

save_plot(
  compact_distribution_plot,
  EXPLORATORY,
  "compact_run_distributions.png",
  11,
  7
)
