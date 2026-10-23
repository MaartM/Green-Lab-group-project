# 1. Data preparation: completeness, timeline, sampling, energy check,
# determinism, token limits, and energy components.

section("1. Data preparation")

# Shared plotting theme for presentation figures.
presentation_theme <- theme_minimal(base_size = 11) +
  theme(
    plot.title = element_text(face = "bold", size = 13),
    axis.title = element_text(colour = "#3f3f3b"),
    panel.grid.minor = element_blank(),
    legend.position = "bottom"
  )

# 1.1 Completeness ------------------------------------------------------------

cat("\n1.1 Completeness\n")
print(table(runs$strategy))
cat("questions per run:", unique(runs$n_queries), "\n")
cat("missing values:", sum(is.na(runs)), "\n")

energy_columns <- c(
  "cpu_energy_j", "gpu0_energy_j", "gpu1_energy_j", "energy_j"
)
cat(
  "non-positive energies:",
  sum(as.matrix(runs[energy_columns]) <= 0, na.rm = TRUE), "\n"
)

run_counts <- as.data.frame(table(strategy = runs$strategy))
names(run_counts)[2] <- "runs"
run_counts$strategy <- factor(run_counts$strategy, levels = STRATEGIES)

save_plot(
  ggplot(run_counts, aes(strategy, runs, fill = strategy)) +
    geom_col(width = 0.65) +
    geom_text(aes(label = runs), vjust = -0.45, fontface = "bold") +
    scale_fill_manual(values = COLORS, labels = LABELS, guide = "none") +
    scale_x_discrete(labels = LABELS) +
    expand_limits(y = max(run_counts$runs) * 1.12) +
    labs(
      title = "Number of runs per strategy",
      x = NULL, y = "Runs"
    ) +
    presentation_theme,
  FINAL_FIGURES, "data_run_counts.png", 5.5, 3.5
)

# Missingness by variable. Zero-count variables are retained to show that
# the data are complete for those fields.
missingness <- data.frame(
  variable = names(runs),
  missing = vapply(runs, function(x) sum(is.na(x)), numeric(1))
)
missingness <- missingness[order(missingness$missing), ]
missingness$variable <- factor(
  missingness$variable,
  levels = missingness$variable
)

save_plot(
  ggplot(missingness, aes(variable, missing)) +
    geom_col(aes(fill = missing > 0), width = 0.75) +
    scale_fill_manual(
      values = c("FALSE" = "#1baf7a", "TRUE" = "#d9534f"),
      labels = c("Complete", "Missing values"),
      name = NULL
    ) +
    coord_flip() +
    labs(
      title = "Missing values by run-level variable",
      x = NULL, y = "Missing observations"
    ) +
    presentation_theme,
  FINAL_FIGURES, "data_missingness.png", 7, 5
)

# 1.2 Experiment timeline -----------------------------------------------------

cat("\n1.2 Experiment timeline (time between run starts, s)\n")

ordered_runs <- runs[order(runs$start), ]
first_start <- ordered_runs$start[1]
last_start <- tail(ordered_runs$start, 1)

cat(
  "first run", format(first_start, "%Y-%m-%d %H:%M"),
  "| last run", format(last_start, "%H:%M"),
  "| span",
  round(as.numeric(difftime(last_start, first_start, units = "hours")), 2),
  "hours\n"
)

gaps <- as.numeric(diff(ordered_runs$start), units = "secs")
print(c(
  count = length(gaps),
  mean = mean(gaps),
  sd = sd(gaps),
  summary(gaps)[-4]
))

print(
  head(ordered_runs[c("order", "run_id", "strategy", "start")]),
  row.names = FALSE
)

gap_data <- data.frame(
  order = ordered_runs$order[-1],
  strategy = ordered_runs$strategy[-1],
  gap_s = gaps
)

save_plot(
  ggplot(gap_data, aes(order, gap_s, colour = strategy)) +
    geom_line(colour = "#c5c4bd", linewidth = 0.45) +
    geom_point(size = 2, alpha = 0.9) +
    scale_colour_manual(values = COLORS, labels = LABELS, name = NULL) +
    labs(
      title = "Time between consecutive run starts",
      x = "Run position in chronological order",
      y = "Time since previous run (seconds)"
    ) +
    presentation_theme,
  FINAL_FIGURES, "data_timeline_gaps.png", 8, 3.5
)

# 1.3 Sampling interval -------------------------------------------------------

cat("\n1.3 Sampling interval (ms)\n")
print(summary(runs[c(
  "sample_interval_median_ms",
  "sample_interval_max_ms"
)]))

sampling <- do.call(rbind, lapply(
  c("sample_interval_median_ms", "sample_interval_max_ms"),
  function(variable) {
    data.frame(
      strategy = runs$strategy,
      value = runs[[variable]],
      metric = if (variable == "sample_interval_median_ms") {
        "Median interval"
      } else {
        "Maximum interval"
      }
    )
  }
))

sampling$metric <- factor(
  sampling$metric,
  levels = c("Median interval", "Maximum interval")
)

save_plot(
  ggplot(sampling, aes(strategy, value, fill = strategy)) +
    geom_boxplot(width = 0.55, outlier.shape = NA, alpha = 0.8) +
    geom_point(
      aes(colour = strategy),
      position = position_jitter(width = 0.12, height = 0, seed = 42),
      size = 1.4, alpha = 0.65
    ) +
    facet_wrap(~metric, scales = "free_y") +
    scale_fill_manual(values = COLORS, labels = LABELS, guide = "none") +
    scale_colour_manual(values = COLORS, labels = LABELS, guide = "none") +
    scale_x_discrete(labels = LABELS) +
    labs(
      title = "Sampling interval by strategy",
      x = NULL, y = "Interval (ms)"
    ) +
    presentation_theme,
  FINAL_FIGURES, "data_sampling_intervals.png", 8, 4
)

# 1.4 Validate energy against Experiment Runner's run table -------------------

cat("\n1.4 Our energy matches Experiment Runner's run table\n")

run_table <- read.csv(file.path(EXPERIMENT_DIR, "run_table.csv"))
theirs <- with(
  run_table,
  setNames(cpu_energy_j + gpu_energy_j, X__run_id)
)

runner_energy <- unname(theirs[as.character(runs$run_id)])
relative_difference_pct <- 100 * (runs$energy_j - runner_energy) /
  runs$energy_j

cat(
  "largest relative difference:",
  max(abs(relative_difference_pct), na.rm = TRUE) / 100,
  "\n"
)

energy_check <- data.frame(
  strategy = runs$strategy,
  order = runs$order,
  run_id = runs$run_id,
  ours_j = runs$energy_j,
  runner_j = runner_energy,
  relative_difference_pct = relative_difference_pct
)

save_plot(
  ggplot(
    energy_check,
    aes(order, relative_difference_pct, colour = strategy)
  ) +
    geom_hline(yintercept = 0, colour = "#777770", linewidth = 0.5) +
    geom_point(size = 2, alpha = 0.85) +
    scale_colour_manual(values = COLORS, labels = LABELS, name = NULL) +
    labs(
      title = "Energy calculation validation",
      subtitle = "Difference relative to our measured energy",
      x = "Run position in the experiment",
      y = "Relative difference (%)"
    ) +
    presentation_theme,
  FINAL_FIGURES, "data_energy_validation.png", 8, 3.5
)

# 1.5 Determinism -------------------------------------------------------------

cat("\n1.5 Determinism: repetitions differing from repetition 0\n")

compared <- c("model", "correct", "completion_tokens", "response")

mismatches <- sapply(STRATEGIES, function(strategy) {
  first <- first_queries[[strategy]][compared]

  sum(sapply(runs$run_id[runs$strategy == strategy], function(run_id) {
    !isTRUE(all.equal(
      load_queries(run_id)[compared],
      first,
      check.attributes = FALSE
    ))
  }))
})

print(mismatches)

determinism <- data.frame(
  strategy = factor(names(mismatches), levels = STRATEGIES),
  mismatching_runs = as.numeric(mismatches)
)
determinism$total_runs <- as.numeric(
  table(factor(runs$strategy, levels = STRATEGIES))
)

save_plot(
  ggplot(determinism, aes(strategy, mismatching_runs, fill = strategy)) +
    geom_col(width = 0.65) +
    geom_text(
      aes(label = paste0(mismatching_runs, "/", total_runs)),
      vjust = -0.45, fontface = "bold"
    ) +
    scale_fill_manual(values = COLORS, labels = LABELS, guide = "none") +
    scale_x_discrete(labels = LABELS) +
    expand_limits(y = max(determinism$mismatching_runs, 1) * 1.15) +
    labs(
      title = "Runs differing from repetition 0",
      x = NULL, y = "Mismatching runs"
    ) +
    presentation_theme,
  FINAL_FIGURES, "data_determinism.png", 5.5, 3.5
)

# 1.5b Answers reaching the token limit --------------------------------------

cat("\nAnswers that reached the 512-token limit (repetition 0)\n")

TOKEN_LIMIT <- 512

token_limit <- do.call(rbind, lapply(STRATEGIES, function(strategy) {
  q <- first_queries[[strategy]]
  at_limit <- q$completion_tokens >= TOKEN_LIMIT

  data.frame(
    strategy = strategy,
    answers = nrow(q),
    at_limit = sum(at_limit),
    at_limit_small = sum(at_limit & q$model == "small"),
    at_limit_large = sum(at_limit & q$model == "large"),
    at_limit_correct = sum(at_limit & q$correct == 1)
  )
}))

print(token_limit, row.names = FALSE)

token_long <- rbind(
  data.frame(
    strategy = token_limit$strategy,
    category = "Below limit",
    answers = token_limit$answers - token_limit$at_limit
  ),
  data.frame(
    strategy = token_limit$strategy,
    category = "At or above limit",
    answers = token_limit$at_limit
  )
)

token_long$strategy <- factor(token_long$strategy, levels = STRATEGIES)
token_long$category <- factor(
  token_long$category,
  levels = c("Below limit", "At or above limit")
)

save_plot(
  ggplot(token_long, aes(strategy, answers, fill = category)) +
    geom_col(position = "fill", width = 0.65) +
    scale_fill_manual(
      values = c(
        "Below limit" = "#b9b8b0",
        "At or above limit" = "#d9534f"
      ),
      name = NULL
    ) +
    scale_y_continuous(labels = scales::percent) +
    scale_x_discrete(labels = LABELS) +
    labs(
      title = "Answers reaching the completion-token limit",
      subtitle = paste("Limit:", TOKEN_LIMIT, "tokens"),
      x = NULL, y = "Share of answers"
    ) +
    presentation_theme,
  FINAL_FIGURES, "data_token_limit.png", 6, 3.5
)

# 1.6 Energy components -------------------------------------------------------

cat("\n1.6 Where the energy goes (mean J per run, share %, mean power W)\n")

components <- aggregate(
  cbind(cpu_energy_j, gpu0_energy_j, gpu1_energy_j, time_s) ~ strategy,
  runs, mean
)

component_columns <- c("cpu_energy_j", "gpu0_energy_j", "gpu1_energy_j")
shares <- 100 * components[component_columns] /
  rowSums(components[component_columns])
power <- components[component_columns] / components$time_s

print(data.frame(
  strategy = components$strategy,
  round(components[component_columns]),
  setNames(round(shares, 1), paste0(component_columns, "_pct")),
  setNames(
    round(power, 1),
    sub("energy_j", "power_w", component_columns)
  )
))

component_names <- c("CPU", "GPU 0 (9B model)", "GPU 1 (2B model)")
component_colours <- c(
  "CPU" = "#52514e",
  "GPU 0 (9B model)" = COLORS[["L"]],
  "GPU 1 (2B model)" = COLORS[["S"]]
)

stacked <- data.frame(
  strategy = factor(components$strategy, levels = STRATEGIES),
  component = rep(component_names, each = nrow(components)),
  energy = unlist(components[component_columns], use.names = FALSE)
)

stacked$strategy_label <- factor(
  unname(LABELS[as.character(stacked$strategy)]),
  levels = rev(unname(LABELS[STRATEGIES]))
)
stacked$component <- factor(stacked$component, levels = component_names)

save_plot(
  ggplot(stacked, aes(energy, strategy_label, fill = component)) +
    geom_col(
      width = 0.6,
      colour = "#fcfcfb",
      position = position_stack(reverse = TRUE)
    ) +
    scale_fill_manual(values = component_colours, name = NULL) +
    labs(
      title = "Energy per run by component",
      x = "Mean energy per run (J)", y = NULL
    ) +
    presentation_theme,
  FINAL_FIGURES, "energy_components.png", 6, 3
)

# Also show the percentage contribution of each component.
component_shares <- data.frame(
  strategy = factor(components$strategy, levels = STRATEGIES),
  component = rep(component_names, each = nrow(components)),
  share_pct = as.vector(as.matrix(shares))
)

component_shares$strategy_label <- factor(
  unname(LABELS[as.character(component_shares$strategy)]),
  levels = rev(unname(LABELS[STRATEGIES]))
)
component_shares$component <- factor(
  component_shares$component, levels = component_names
)

save_plot(
  ggplot(
    component_shares,
    aes(share_pct, strategy_label, fill = component)
  ) +
    geom_col(
      width = 0.6,
      colour = "#fcfcfb",
      position = position_stack(reverse = TRUE)
    ) +
    scale_fill_manual(values = component_colours, name = NULL) +
    labs(
      title = "Share of energy consumption by component",
      x = "Share of total energy (%)", y = NULL
    ) +
    presentation_theme,
  FINAL_FIGURES, "energy_component_shares.png", 6, 3
)
