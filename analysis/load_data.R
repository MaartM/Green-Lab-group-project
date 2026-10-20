# Load one experiment into one row per run (runs) and correctness per question (answers),
# and save both as processed CSVs. Everything is recomputed from the raw per-run files
# (energibridge.csv and queries.csv), not taken from run_table.csv.

SAMPLE_COLUMNS <- c("Time", "CPU_ENERGY (J)", "USED_MEMORY",
                    paste0("GPU", rep(0:1, each = 4), "_",
                           c("POWER (mWatts)", "USAGE", "MEMORY_USED", "TEMPERATURE")))

load_samples <- function(run_id) {
  path <- file.path(EXPERIMENT_DIR, run_id, "energibridge.csv")
  header <- strsplit(readLines(path, n = 1), ",")[[1]]
  classes <- ifelse(header %in% SAMPLE_COLUMNS, "numeric", "NULL")
  samples <- read.csv(path, colClasses = classes, check.names = FALSE)
  samples$t_s <- (samples$Time - samples$Time[1]) / 1000
  samples
}

load_queries <- function(run_id) {
  read.csv(file.path(EXPERIMENT_DIR, run_id, "queries.csv"), stringsAsFactors = FALSE)
}

# Experiment Runner numbers the treatments in run table order: run_0 = S, run_1 = L, run_2 = R.
strategy_of <- function(run_id) STRATEGIES[as.integer(strsplit(run_id, "_")[[1]][2]) + 1]

# CPU: sum of the positive increments of the cumulative RAPL counter.
# GPU g: sum over samples of (time since previous sample) x (power at this sample).
energy <- function(samples) {
  dt_s <- diff(samples$Time) / 1000
  power_w <- function(gpu) samples[[paste0("GPU", gpu, "_POWER (mWatts)")]][-1] / 1000
  c(cpu_energy_j = sum(pmax(diff(samples[["CPU_ENERGY (J)"]]), 0)),
    gpu0_energy_j = sum(dt_s * power_w(0)),
    gpu1_energy_j = sum(dt_s * power_w(1)))
}

summarize_run <- function(run_id) {
  samples <- load_samples(run_id)
  queries <- load_queries(run_id)
  e <- energy(samples)
  total <- sum(e)
  n <- nrow(queries)
  correct <- sum(queries$correct)
  tokens <- sum(queries$completion_tokens)
  intervals <- diff(samples$Time)
  data.frame(
    run_id = run_id, strategy = strategy_of(run_id),
    repetition = as.integer(sub(".*_", "", run_id)),
    start = as.POSIXct(samples$Time[1] / 1000, origin = "1970-01-01", tz = "UTC"),
    t(e), energy_j = total,
    n_queries = n, n_correct = correct, n_tokens = tokens,
    n_to_large = sum(queries$model == "large"),
    accuracy_pct = 100 * correct / n,
    energy_per_query_j = total / n,
    energy_per_token_j = total / tokens,
    efficiency_correct_per_kj = 1000 * correct / total,
    time_s = tail(samples$t_s, 1),
    latency_mean_s = mean(queries$latency_s),
    latency_p95_s = unname(quantile(queries$latency_s, 0.95)),
    gpu0_util_pct = mean(samples$GPU0_USAGE),
    gpu1_util_pct = mean(samples$GPU1_USAGE),
    host_memory_peak_mib = max(samples$USED_MEMORY) / 2^20,
    gpu_memory_peak_mib = max(samples$GPU0_MEMORY_USED + samples$GPU1_MEMORY_USED),
    gpu0_start_temp_c = samples$GPU0_TEMPERATURE[1],
    gpu1_start_temp_c = samples$GPU1_TEMPERATURE[1],
    sample_interval_median_ms = median(intervals),
    sample_interval_max_ms = max(intervals)
  )
}

run_ids <- sort(list.files(EXPERIMENT_DIR, pattern = "^run_[0-9]+_repetition_[0-9]+$"))
runs <- do.call(rbind, lapply(run_ids, summarize_run))
runs <- runs[order(runs$start), ]
rownames(runs) <- NULL
runs$order <- seq_len(nrow(runs)) - 1  # position in the experiment, from 0
runs$strategy <- factor(runs$strategy, levels = STRATEGIES)

# Correctness per question and strategy, from each strategy's first repetition.
# Generation is deterministic (checked in 1.5), so every repetition gives the same answers.
first_queries <- lapply(setNames(seq_along(STRATEGIES) - 1, STRATEGIES),
                        function(i) load_queries(sprintf("run_%d_repetition_0", i)))
qids <- sort(first_queries$S$qid)
answers <- data.frame(qid = qids, sapply(first_queries, function(q) q$correct[match(qids, q$qid)]))

# Sanity checks: the strategy is inferred from the run ID, so check that each run used the
# models of its strategy, and that every run answered the same questions exactly once.
for (run_id in run_ids) {
  queries <- load_queries(run_id)
  used <- sort(unique(queries$model))
  expected <- switch(strategy_of(run_id), S = "small", L = "large", R = c("large", "small"))
  if (!identical(used, expected)) stop(run_id, " used models ", toString(used), ", expected ", toString(expected))
  if (!identical(sort(queries$qid), qids)) stop(run_id, " did not answer the same questions as run_0_repetition_0")
}

write.csv(transform(runs, start = format(start, "%Y-%m-%dT%H:%M:%SZ")),
          file.path(PROCESSED, "runs.csv"), row.names = FALSE)
write.csv(answers, file.path(PROCESSED, "answers.csv"), row.names = FALSE)
