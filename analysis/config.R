# Settings shared by all analysis scripts: constants, plot theme and helpers.

suppressPackageStartupMessages(library(ggplot2))

ALPHA <- 0.05
STRATEGIES <- c("S", "L", "R")
STRATEGY_NAMES <- c(S = "small-only", L = "large-only", R = "routing")
COLORS <- c(S = "#2a78d6", L = "#eb6834", R = "#1baf7a")
LABELS <- setNames(paste0(STRATEGIES, " (", STRATEGY_NAMES, ")"), STRATEGIES)

# Run-level dependent variables (report Table 5): column -> label with unit.
RUN_VARIABLES <- c(
  energy_j = "Total energy E (J)",
  energy_per_query_j = "Energy per query E/N (J/query)",
  energy_per_token_j = "Energy per output token E/K (J/token)",
  efficiency_correct_per_kj = "Energy efficiency C/E (correct per kJ)",
  time_s = "Total inference time T (s)",
  latency_mean_s = "Mean query latency (s)",
  latency_p95_s = "95th-percentile query latency (s)",
  gpu0_util_pct = "Mean utilization GPU 0 (%)",
  gpu1_util_pct = "Mean utilization GPU 1 (%)",
  host_memory_peak_mib = "Peak host memory (MiB)",
  gpu_memory_peak_mib = "Peak GPU memory, both GPUs (MiB)"
)

theme_set(theme_minimal(base_size = 10) +
            theme(panel.grid.minor = element_blank(), legend.position = "top",
                  plot.background = element_rect(fill = "#fcfcfb", colour = NA)))

save_plot <- function(plot, dir, name, width, height) {
  ggsave(file.path(dir, name), plot, width = width, height = height, dpi = 150)
}

section <- function(title) cat("\n\n==========", title, "==========\n")
