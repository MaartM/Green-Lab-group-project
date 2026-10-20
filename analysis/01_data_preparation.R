# 1. Data preparation: completeness, timeline, sampling, energy check, determinism, energy components.

section("1. Data preparation")

cat("\n1.1 Completeness\n")
print(table(runs$strategy))
cat("questions per run:", unique(runs$n_queries), "\n")
cat("missing values:", sum(is.na(runs)), "\n")
energy_columns <- c("cpu_energy_j", "gpu0_energy_j", "gpu1_energy_j", "energy_j")
cat("non-positive energies:", sum(runs[energy_columns] <= 0), "\n")

cat("\n1.2 Experiment timeline (time between run starts, s)\n")
cat("first run", format(runs$start[1], "%Y-%m-%d %H:%M"), "| last run", format(tail(runs$start, 1), "%H:%M"),
    "| span", format(round(difftime(tail(runs$start, 1), runs$start[1], units = "hours"), 2)), "\n")
gaps <- as.numeric(diff(runs$start), units = "secs")
print(c(count = length(gaps), mean = mean(gaps), sd = sd(gaps), summary(gaps)[-4]))
print(head(runs[c("order", "run_id", "strategy", "start")]), row.names = FALSE)

cat("\n1.3 Sampling interval (ms)\n")
print(summary(runs[c("sample_interval_median_ms", "sample_interval_max_ms")]))

cat("\n1.4 Our energy matches Experiment Runner's run table\n")
run_table <- read.csv(file.path(EXPERIMENT_DIR, "run_table.csv"))
theirs <- with(run_table, setNames(cpu_energy_j + gpu_energy_j, X__run_id))
cat("largest relative difference:", max(abs((runs$energy_j - theirs[runs$run_id]) / runs$energy_j)), "\n")

cat("\n1.5 Determinism: repetitions differing from repetition 0\n")
compared <- c("model", "correct", "completion_tokens", "response")
mismatches <- sapply(STRATEGIES, function(strategy) {
  first <- first_queries[[strategy]][compared]
  sum(sapply(runs$run_id[runs$strategy == strategy], function(run_id) {
    !isTRUE(all.equal(load_queries(run_id)[compared], first, check.attributes = FALSE))
  }))
})
print(mismatches)

cat("\nAnswers that reached the 512-token limit (repetition 0)\n")
TOKEN_LIMIT <- 512
print(do.call(rbind, lapply(STRATEGIES, function(strategy) {
  q <- first_queries[[strategy]]
  at_limit <- q$completion_tokens >= TOKEN_LIMIT
  data.frame(strategy = strategy, answers = nrow(q), at_limit = sum(at_limit),
             at_limit_small = sum(at_limit & q$model == "small"),
             at_limit_large = sum(at_limit & q$model == "large"),
             at_limit_correct = sum(at_limit & q$correct == 1))
})), row.names = FALSE)

cat("\n1.6 Where the energy goes (mean J per run, share %, mean power W)\n")
components <- aggregate(cbind(cpu_energy_j, gpu0_energy_j, gpu1_energy_j, time_s) ~ strategy, runs, mean)
component_columns <- c("cpu_energy_j", "gpu0_energy_j", "gpu1_energy_j")
shares <- 100 * components[component_columns] / rowSums(components[component_columns])
power <- components[component_columns] / components$time_s
print(data.frame(strategy = components$strategy, round(components[component_columns]),
                 setNames(round(shares, 1), paste0(component_columns, "_pct")),
                 setNames(round(power, 1), sub("energy_j", "power_w", component_columns))))

stacked <- data.frame(strategy = factor(unname(LABELS[as.character(components$strategy)]), levels = rev(LABELS)),
                      component = factor(rep(c("CPU", "GPU 0 (9B model)", "GPU 1 (2B model)"), each = 3),
                                         levels = c("CPU", "GPU 0 (9B model)", "GPU 1 (2B model)")),
                      energy = unlist(components[component_columns], use.names = FALSE))
save_plot(ggplot(stacked, aes(energy, strategy, fill = component)) +
            geom_col(width = 0.6, colour = "#fcfcfb", position = position_stack(reverse = TRUE)) +
            scale_fill_manual(values = c("#52514e", COLORS[["L"]], COLORS[["S"]]), name = NULL) +
            labs(x = "Mean energy per run (J)", y = NULL, title = "Energy per run by component"),
          FINAL_FIGURES, "energy_components.png", 6, 3)
