# Statistical procedure (report Section 4.5), for run-level variables:
#   1. Shapiro-Wilk per strategy, median-centred Levene across strategies. If normality
#      fails, the same checks on log values; the tests use them if that makes the data normal.
#   2. Omnibus: one-way ANOVA (equal variances), Welch's ANOVA (unequal), Kruskal-Wallis (not normal).
#      With two strategies, the omnibus test is the two-sample test of step 3.
#   3. Pairwise, only after a significant omnibus test: Student's or Welch's t-test with
#      Cohen's d, or Mann-Whitney U with Cliff's delta.
#   4. Benjamini-Hochberg correction per research question, separately for the omnibus and
#      the pairwise tests. Pairwise tests follow omnibus tests that are significant after correction.
# Variables that are constant within every strategy are reported descriptively.

# Research question of each tested variable (report Table 7).
RESEARCH_QUESTIONS <- c(
  energy_j = "RQ1", energy_per_query_j = "RQ1", energy_per_token_j = "RQ1",
  efficiency_correct_per_kj = "RQ2",
  time_s = "RQ3", latency_mean_s = "RQ3", latency_p95_s = "RQ3", gpu0_util_pct = "RQ3",
  gpu1_util_pct = "RQ3", host_memory_peak_mib = "RQ3", gpu_memory_peak_mib = "RQ3"
)

# A GPU's utilization is compared only between the strategies that use that GPU.
COMPARED <- list(gpu0_util_pct = c("R", "L"), gpu1_util_pct = c("R", "S"))

describe <- function(data, variable) {
  do.call(rbind, lapply(split(data[[variable]], data$strategy), function(x) {
    data.frame(count = length(x), mean = mean(x), median = median(x), sd = sd(x), var = var(x),
               min = min(x), max = max(x), iqr = unname(diff(quantile(x, c(0.25, 0.75)))))
  }))
}

levene_median <- function(samples) {
  deviations <- unlist(lapply(samples, function(x) abs(x - median(x))))
  group <- factor(rep(names(samples), lengths(samples)))
  oneway.test(deviations ~ group, var.equal = TRUE)$p.value
}

check_assumptions <- function(samples) {
  shapiro <- sapply(samples, function(x) shapiro.test(x)$p.value)
  levene <- levene_median(samples)
  list(normal = all(shapiro >= ALPHA), equal_variances = levene >= ALPHA,
       shapiro_p = shapiro, levene_p = levene)
}

# A test result: name, statistic (with its symbol) and degrees of freedom, p-value.
test_result <- function(test, symbol, result, df1 = NA, df2 = NA) {
  list(test = test, statistic_name = symbol, statistic = unname(result$statistic),
       df1 = df1, df2 = df2, p = result$p.value, ci = result$conf.int)
}

# W is the Mann-Whitney U of the first sample.
two_sample_test <- function(a, b, normal, equal_variances) {
  if (!normal) return(test_result("Mann-Whitney U", "U", wilcox.test(a, b, exact = FALSE, correct = TRUE)))
  result <- t.test(a, b, var.equal = equal_variances)
  test_result(if (equal_variances) "Student's t" else "Welch's t", "t", result, unname(result$parameter))
}

omnibus <- function(samples, normal, equal_variances) {
  if (length(samples) == 2) return(two_sample_test(samples[[1]], samples[[2]], normal, equal_variances))
  values <- unlist(samples)
  group <- factor(rep(names(samples), lengths(samples)))
  if (!normal) {
    result <- kruskal.test(values, group)
    return(test_result("Kruskal-Wallis", "H", result, unname(result$parameter)))
  }
  result <- oneway.test(values ~ group, var.equal = equal_variances)
  test_result(if (equal_variances) "one-way ANOVA" else "Welch's ANOVA", "F", result,
              unname(result$parameter[1]), unname(result$parameter[2]))
}

cohens_d <- function(a, b) {
  pooled_sd <- sqrt(((length(a) - 1) * var(a) + (length(b) - 1) * var(b)) / (length(a) + length(b) - 2))
  (mean(a) - mean(b)) / pooled_sd
}

# P(a > b) - P(a < b) over all pairs; -1..1.
cliffs_delta <- function(a, b) mean(sign(outer(a, b, "-")))

# Differences are in the original units (samples); tests and effect sizes use the
# values that were tested (the samples or their logarithm). First strategy minus second,
# in the order of PAIRS (R - L, R - S, S - L).
pairwise <- function(r) {
  pairs <- Filter(function(pair) all(pair %in% names(r$samples)), PAIRS)
  do.call(rbind, lapply(pairs, function(pair) {
    a <- r$samples[[pair[1]]]
    b <- r$samples[[pair[2]]]
    row <- data.frame(variable = r$variable, rq = r$rq, comparison = paste(pair[1], "-", pair[2]),
                      mean_difference = mean(a) - mean(b),
                      percent_vs_second = 100 * (mean(a) / mean(b) - 1),
                      test = NA, statistic_name = NA, statistic = NA, df = NA, p = NA,
                      ci95_low = NA, ci95_high = NA, effect_size = NA, effect = NA)
    a <- r$tested[[pair[1]]]
    b <- r$tested[[pair[2]]]
    result <- two_sample_test(a, b, r$normal, r$equal_variances)
    row$test <- result$test
    row$statistic_name <- result$statistic_name
    row$statistic <- result$statistic
    row$df <- result$df1
    row$p <- result$p
    if (r$normal) {
      if (r$transform != "log") {  # a confidence interval of log values is not in original units
        row$ci95_low <- result$ci[1]
        row$ci95_high <- result$ci[2]
      }
      row$effect_size <- cohens_d(a, b)
      row$effect <- "Cohen's d"
    } else {
      row$effect_size <- cliffs_delta(a, b)
      row$effect <- "Cliff's delta"
    }
    row
  }))
}

# Assumption checks and omnibus test for one variable.
analyse <- function(data, variable) {
  strategies <- if (is.null(COMPARED[[variable]])) STRATEGIES else COMPARED[[variable]]
  samples <- split(data[[variable]], data$strategy)[strategies]
  result <- list(variable = variable, rq = RESEARCH_QUESTIONS[[variable]], strategies = strategies,
                 transform = "", shapiro_p = c(), levene_p = NA, test = "descriptive only (constant)",
                 statistic_name = NA, statistic = NA, df1 = NA, df2 = NA, p = NA)
  if (all(sapply(samples, sd) == 0)) return(result)
  tested <- samples
  transform <- "none"
  assumptions <- check_assumptions(samples)
  if (!assumptions$normal) {
    logged <- lapply(samples, log)
    log_assumptions <- check_assumptions(logged)
    if (log_assumptions$normal) {
      tested <- logged
      transform <- "log"
      assumptions <- log_assumptions
    }
  }
  test <- omnibus(tested, assumptions$normal, assumptions$equal_variances)
  modifyList(result, c(assumptions, test[c("test", "statistic_name", "statistic", "df1", "df2", "p")],
                       list(transform = transform, samples = samples, tested = tested)))
}

# Benjamini-Hochberg adjusted p-values, within each family.
bh_by <- function(p, family) {
  adjusted <- p
  for (f in unique(family)) {
    i <- family == f & !is.na(p)
    adjusted[i] <- p.adjust(p[i], method = "BH")
  }
  adjusted
}

# Accuracy (RQ2), per question: Cochran's Q across the three strategies, exact McNemar per pair
# (binomial test on the questions where exactly one of the two strategies is correct).
PAIRS <- list(c("R", "L"), c("R", "S"), c("S", "L"))

accuracy_tests <- function(answers) {
  outcomes <- as.matrix(answers[STRATEGIES])
  k <- ncol(outcomes)
  q <- (k - 1) * (k * sum(colSums(outcomes)^2) - sum(outcomes)^2) /
    (k * sum(outcomes) - sum(rowSums(outcomes)^2))
  mcnemar <- do.call(rbind, lapply(PAIRS, function(pair) {
    first <- answers[[pair[1]]]
    second <- answers[[pair[2]]]
    only_first <- sum(first == 1 & second == 0)
    only_second <- sum(first == 0 & second == 1)
    data.frame(comparison = paste(pair[1], "-", pair[2]),
               accuracy_difference_pp = 100 * (mean(first) - mean(second)),
               only_first_correct = only_first, only_second_correct = only_second,
               exact_mcnemar_p = binom.test(only_first, only_first + only_second)$p.value)
  }))
  list(q = q, df = k - 1, p = pchisq(q, k - 1, lower.tail = FALSE), mcnemar = mcnemar)
}

# All run-level tests on a set of runs, with accuracy in the RQ2 families.
run_tests <- function(data, accuracy) {
  results <- lapply(setNames(names(RUN_VARIABLES), names(RUN_VARIABLES)), function(v) analyse(data, v))
  omnibus_table <- do.call(rbind, lapply(results, function(r) {
    shapiro <- function(s) if (s %in% names(r$shapiro_p)) r$shapiro_p[[s]] else NA
    data.frame(variable = r$variable, rq = r$rq, strategies = paste(r$strategies, collapse = ", "),
               transform = r$transform, shapiro_p_S = shapiro("S"), shapiro_p_L = shapiro("L"),
               shapiro_p_R = shapiro("R"), levene_p = r$levene_p, test = r$test,
               statistic_name = r$statistic_name, statistic = r$statistic, df1 = r$df1, df2 = r$df2, p = r$p)
  }))
  omnibus_table <- rbind(omnibus_table, data.frame(
    variable = "accuracy", rq = "RQ2", strategies = "S, L, R", transform = "", shapiro_p_S = NA,
    shapiro_p_L = NA, shapiro_p_R = NA, levene_p = NA, test = "Cochran's Q",
    statistic_name = "Q", statistic = accuracy$q, df1 = accuracy$df, df2 = NA, p = accuracy$p))
  omnibus_table$p_bh <- bh_by(omnibus_table$p, omnibus_table$rq)
  rownames(omnibus_table) <- NULL

  significant <- omnibus_table$variable[!is.na(omnibus_table$p_bh) & omnibus_table$p_bh < ALPHA]
  pairwise_table <- do.call(rbind, lapply(results[intersect(names(results), significant)], pairwise))
  accuracy_pairs <- accuracy$mcnemar
  p_bh <- bh_by(c(pairwise_table$p, accuracy_pairs$exact_mcnemar_p),
                c(pairwise_table$rq, rep("RQ2", nrow(accuracy_pairs))))
  pairwise_table$p_bh <- head(p_bh, nrow(pairwise_table))
  accuracy_pairs$p_bh <- tail(p_bh, nrow(accuracy_pairs))
  rownames(pairwise_table) <- NULL
  list(omnibus = omnibus_table, pairwise = pairwise_table, accuracy = accuracy_pairs)
}

# AUC of predicting a 0/1 outcome from a score (Mann-Whitney formulation, ties count half).
auc <- function(outcome, score) {
  ranks <- rank(score)
  positives <- sum(outcome == 1)
  negatives <- length(outcome) - positives
  (sum(ranks[outcome == 1]) - positives * (positives + 1) / 2) / (positives * negatives)
}
