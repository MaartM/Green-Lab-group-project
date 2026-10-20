# 4. Accuracy and the energy-accuracy trade-off (RQ2), and the router on the full test split.

section("4. Accuracy and the energy-accuracy trade-off")

cat("\n4.1 Accuracy and paired outcomes (tests computed with section 3's RQ2 family)\n")
cat("correct answers:", paste(STRATEGIES, colSums(answers[STRATEGIES]), sep = " = ", collapse = ", "), "\n")
for (pair in PAIRS) {
  print(table(factor(answers[[pair[1]]], 1:0, paste(pair[1], c("correct", "wrong"))),
              factor(answers[[pair[2]]], 1:0, paste(pair[2], c("correct", "wrong"))), dnn = NULL))
}
accuracy_omnibus <- tests$omnibus[tests$omnibus$variable == "accuracy", ]
cat(sprintf("Cochran's Q = %.1f, p = %.2g, p_bh = %.2g\n", accuracy$q, accuracy_omnibus$p, accuracy_omnibus$p_bh))
print(tests$accuracy, row.names = FALSE, digits = 3)
write.csv(tests$accuracy, file.path(TESTS, "accuracy_tests.csv"), row.names = FALSE)

outcomes <- as.matrix(answers[STRATEGIES])

# Bootstrap: resample the questions with replacement, keeping each question's three outcomes together.
set.seed(42)
ci <- function(values) round(unname(quantile(values, c(0.025, 0.975))), 1)
boot <- replicate(10000, colMeans(outcomes[sample(nrow(outcomes), replace = TRUE), ]) * 100)
for (pair in PAIRS[1:2]) {
  point <- 100 * (mean(answers[[pair[1]]]) - mean(answers[[pair[2]]]))
  cat(sprintf("accuracy %s - %s = %+.1f pp, 95%% CI [%.1f, %.1f]\n", pair[1], pair[2], point,
              ci(boot[pair[1], ] - boot[pair[2], ])[1], ci(boot[pair[1], ] - boot[pair[2], ])[2]))
}

cat("\n4.2 Energy saving, efficiency and routing share\n")
energy_of <- split(runs$energy_j, runs$strategy)
saving <- 100 * (1 - mean(energy_of$R) / mean(energy_of$L))
boot_saving <- replicate(10000, 100 * (1 - mean(sample(energy_of$R, replace = TRUE)) /
                                          mean(sample(energy_of$L, replace = TRUE))))
cat(sprintf("energy saving SE = 100 x (1 - E_R / E_L) = %.2f%%, 95%% CI [%.2f, %.2f]\n", saving,
            quantile(boot_saving, 0.025), quantile(boot_saving, 0.975)))
cat(sprintf("absolute saving: %.0f J per run, %.1f J per question\n", mean(energy_of$L) - mean(energy_of$R),
            (mean(energy_of$L) - mean(energy_of$R)) / runs$n_queries[1]))
routed_run <- runs[runs$strategy == "R", ][1, ]
cat(sprintf("questions routed to the large model: %.0f%%\n", 100 * routed_run$n_to_large / routed_run$n_queries))
means <- aggregate(cbind(accuracy_pct, energy_per_query_j, efficiency_correct_per_kj) ~ strategy, runs, mean)
print(means, row.names = FALSE, digits = 4)

save_plot(ggplot(means, aes(energy_per_query_j, accuracy_pct, colour = strategy)) +
            geom_point(size = 3) +
            geom_text(aes(label = LABELS[as.character(strategy)]), hjust = -0.15, colour = "#52514e", size = 3.2) +
            scale_colour_manual(values = COLORS, guide = "none") +
            scale_x_continuous(limits = c(0, max(means$energy_per_query_j) * 1.35)) +
            scale_y_continuous(limits = c(0, 100)) +
            labs(x = "Energy per question (J)", y = "Accuracy (%)", title = "Energy-accuracy trade-off"),
          FINAL_FIGURES, "tradeoff.png", 5.5, 3.8)

cat("\n4.3 Routing decisions and the energy of R\n")
routed <- first_queries$R[order(first_queries$R$qid), ]
print(table(routed_to = routed$model, S_correct = answers$S, L_correct = answers$L))
cat(sprintf("router AUC on the experiment questions: %.2f\n", auc(answers$S, routed$p_small_correct)))
per_question <- setNames(means$energy_per_query_j, means$strategy)
share_large <- mean(routed$model == "large")
mix <- share_large * per_question[["L"]] + (1 - share_large) * per_question[["S"]]
cat(sprintf("weighted mix of S and L costs: %.0f J/question; measured R: %.0f J/question\n", mix, per_question[["R"]]))

cat("\n4.4 The router on the full test split\n")
# Router predictions come from the Python router; scripts/plot_router_test_split.py writes them.
predictions_file <- ROUTER_PREDICTIONS
if (!file.exists(predictions_file)) {
  stop(predictions_file, " not found; run scripts/plot_router_test_split.py first")
} else {
  predictions <- read.csv(predictions_file)
  predictions <- predictions[order(predictions$qid), ]
  threshold <- unique(predictions$threshold)  # the threshold of llm-routing/config.py
  cat("router threshold:", threshold, "\n")
  router_summary <- function(qids) {
    p <- predictions[predictions$qid %in% qids, ]
    to_small <- p$p_small_correct > threshold
    boot_auc <- replicate(5000, {
      sample_rows <- sample(nrow(p), replace = TRUE)
      y <- p$small_correct[sample_rows]
      if (sum(y) > 0 && sum(y) < length(y)) auc(y, p$p_small_correct[sample_rows]) else NA
    })
    share_small <- mean(to_small)
    c(questions = nrow(p),
      AUC = auc(p$small_correct, p$p_small_correct),
      AUC_ci95_low = unname(quantile(boot_auc, 0.025, na.rm = TRUE)),
      AUC_ci95_high = unname(quantile(boot_auc, 0.975, na.rm = TRUE)),
      sent_to_small_pct = 100 * share_small,
      S_accuracy_pct = 100 * mean(p$small_correct),
      S_accuracy_on_sent_to_small_pct = 100 * mean(p$small_correct[to_small]),
      L_accuracy_pct = 100 * mean(p$large_correct),
      R_accuracy_pct = 100 * mean(ifelse(to_small, p$small_correct, p$large_correct)),
      random_routing_same_share_pct = 100 * (share_small * mean(p$small_correct) +
                                               (1 - share_small) * mean(p$large_correct)))
  }
  print(round(data.frame(full_test_split = router_summary(predictions$qid),
                         experiment_questions = router_summary(answers$qid)), 3))
}
