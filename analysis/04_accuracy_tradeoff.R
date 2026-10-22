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

# Bootstrap: resample questions with replacement, keeping each question's outcomes together.
set.seed(42)
ci <- function(values) round(unname(quantile(values, c(0.025, 0.975))), 1)
boot <- replicate(10000, colMeans(outcomes[sample(nrow(outcomes), replace = TRUE), ]) * 100)
for (pair in PAIRS[1:2]) {
  point <- 100 * (mean(answers[[pair[1]]]) - mean(answers[[pair[2]]]))
  pair_boot <- boot[pair[1], ] - boot[pair[2], ]
  pair_ci <- ci(pair_boot)
  cat(sprintf("accuracy %s - %s = %+.1f pp, 95%% CI [%.1f, %.1f]\n",
              pair[1], pair[2], point, pair_ci[1], pair_ci[2]))
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
means$strategy <- as.character(means$strategy)
print(means, row.names = FALSE, digits = 4)

# Question-bootstrap 95% CIs for accuracy, paired by question.
accuracy_ci <- data.frame(
  strategy = STRATEGIES,
  lower = vapply(STRATEGIES, function(s) unname(quantile(boot[s, ], 0.025)), numeric(1)),
  upper = vapply(STRATEGIES, function(s) unname(quantile(boot[s, ], 0.975)), numeric(1))
)
plot_means <- merge(means, accuracy_ci, by = "strategy", sort = FALSE)
plot_means$strategy <- factor(plot_means$strategy, levels = STRATEGIES)

# Reference point supplied for 59% routing to L. This is proportional mixing,
# not a prediction of the non-random router's actual selected subset.
mix_point <- data.frame(energy = 237.9, accuracy = 71.3, label = "59% to L\n(proportional mix)")
mix_line <- data.frame(
  x = c(means$energy_per_query_j[means$strategy == "S"],
        means$energy_per_query_j[means$strategy == "L"]),
  y = c(means$accuracy_pct[means$strategy == "S"],
        means$accuracy_pct[means$strategy == "L"])
)
ray_efficiencies <- c(S = 3.37, L = 2.87, R = 2.63)
ray_xmax <- max(means$energy_per_query_j) * 1.08
rays <- do.call(rbind, lapply(names(ray_efficiencies), function(s) {
  data.frame(strategy = s, x = c(0, ray_xmax),
             y = c(0, ray_efficiencies[[s]] * ray_xmax / 10))
}))

tradeoff_plot <- ggplot() +
  geom_line(data = rays, aes(x = x, y = y, linetype = strategy),
            colour = "#8b8985", linewidth = 0.55, alpha = 0.8) +
  geom_segment(data = data.frame(x = mix_line$x[1], y = mix_line$y[1],
                                 xend = mix_line$x[2], yend = mix_line$y[2]),
               aes(x = x, y = y, xend = xend, yend = yend),
               inherit.aes = FALSE, colour = "#686762", linetype = "dashed", linewidth = 0.8) +
  geom_errorbar(data = plot_means,
                aes(x = energy_per_query_j, ymin = lower, ymax = upper, colour = strategy),
                width = 5, linewidth = 0.7) +
  geom_point(data = plot_means, aes(energy_per_query_j, accuracy_pct, colour = strategy), size = 3) +
  geom_text(data = plot_means,
            aes(energy_per_query_j, accuracy_pct, label = LABELS[strategy]),
            hjust = -0.12, vjust = -0.7, colour = "#52514e", size = 3) +
  geom_point(data = mix_point, aes(energy, accuracy), shape = 21, fill = "white",
             colour = "#686762", size = 2.8, stroke = 0.9) +
  geom_text(data = mix_point, aes(energy, accuracy, label = label),
            hjust = 1.08, vjust = 1.25, colour = "#52514e", size = 2.8) +
  # Place efficiency labels in the middle-left of the plot, away from R's point label.
  # White label backgrounds keep the text legible where the rays pass underneath.
  annotate("label", x = ray_xmax * 0.58, y = ray_efficiencies[["S"]] * ray_xmax * 0.58 / 10,
           label = "3.37 correct/kJ", hjust = 0, vjust = -0.25, size = 2.7,
           colour = "#333333", fill = "white", label.size = 0, label.padding = unit(0.10, "lines")) +
  annotate("label", x = ray_xmax * 0.58, y = ray_efficiencies[["L"]] * ray_xmax * 0.58 / 10,
           label = "2.87 correct/kJ", hjust = 0, vjust = -0.25, size = 2.7,
           colour = "#333333", fill = "white", label.size = 0, label.padding = unit(0.10, "lines")) +
  annotate("label", x = ray_xmax * 0.58, y = ray_efficiencies[["R"]] * ray_xmax * 0.58 / 10,
           label = "2.63 correct/kJ", hjust = 0, vjust = -0.25, size = 2.7,
           colour = "#333333", fill = "white", label.size = 0, label.padding = unit(0.10, "lines")) +
  scale_colour_manual(values = COLORS, guide = "none") +
  scale_linetype_manual(values = c(S = "solid", L = "solid", R = "solid"), guide = "none") +
  coord_cartesian(xlim = c(0, ray_xmax), ylim = c(0, 100), clip = "off") +
  labs(x = "Energy per question (J)", y = "Accuracy (%)",
       title = "Energy–accuracy trade-off",
       subtitle = "Points: measured strategies with question-bootstrap 95% CIs; dashed line: proportional-mixing reference",
       caption = "Mixing assumes random routing; the router selects a non-random subset. Iso-efficiency rays pass through the origin.") +
  theme(plot.margin = margin(5.5, 24, 5.5, 5.5))

save_plot(tradeoff_plot, FINAL_FIGURES, "tradeoff.png", 7.2, 4.8)

cat("\n4.3 Routing decisions and the energy of R\n")
routed <- first_queries$R[order(first_queries$R$qid), ]
print(table(routed_to = routed$model, S_correct = answers$S, L_correct = answers$L))
cat(sprintf("router AUC on the experiment questions: %.2f\n", auc(answers$S, routed$p_small_correct)))
per_question <- setNames(means$energy_per_query_j, means$strategy)
share_large <- mean(routed$model == "large")
mix <- share_large * per_question[["L"]] + (1 - share_large) * per_question[["S"]]
cat(sprintf("weighted mix of S and L costs: %.0f J/question; measured R: %.0f J/question\n", mix, per_question[["R"]]))

# Router decision quality: one deterministic routing decision per question.
# Join by qid explicitly so row ordering cannot silently misalign outcomes.
router_decisions <- data.frame(
  qid = routed$qid,
  routed_model = as.character(routed$model),
  S_correct = answers$S[match(routed$qid, answers$qid)],
  L_correct = answers$L[match(routed$qid, answers$qid)]
)
if (anyNA(router_decisions$S_correct) || anyNA(router_decisions$L_correct)) {
  stop("Could not match every R routing decision to S and L correctness by qid")
}
router_decisions$group <- with(router_decisions, ifelse(
  S_correct == 1 & L_correct == 1, "Both correct",
  ifelse(S_correct == 0 & L_correct == 1, "Only L correct",
         ifelse(S_correct == 1 & L_correct == 0, "Only S correct", "Both wrong")
  )
))
router_decisions$group <- factor(router_decisions$group,
                                 levels = c("Both correct", "Only L correct", "Only S correct", "Both wrong"))
router_decisions$routed_to <- ifelse(router_decisions$routed_model == "small", "S", "L")
routing_counts <- as.data.frame(table(group = router_decisions$group, routed_to = router_decisions$routed_to))
names(routing_counts)[3] <- "n"
routing_counts <- merge(routing_counts,
                        aggregate(n ~ group, routing_counts, sum),
                        by = "group", suffixes = c("", "_group"))
routing_counts$share_pct <- ifelse(routing_counts$n_group > 0,
                                   100 * routing_counts$n / routing_counts$n_group, 0)
routing_counts$group <- factor(routing_counts$group, levels = levels(router_decisions$group))
routing_counts$routed_to <- factor(routing_counts$routed_to, levels = c("S", "L"))

n_both_correct_to_l <- sum(router_decisions$S_correct == 1 & router_decisions$L_correct == 1 &
                             router_decisions$routed_to == "L")
n_only_l_to_s <- sum(router_decisions$S_correct == 0 & router_decisions$L_correct == 1 &
                       router_decisions$routed_to == "S")
cat(sprintf("both-correct questions routed to L (wasted energy cases): %d\n", n_both_correct_to_l))
cat(sprintf("only-L-correct questions routed to S (lost accuracy cases): %d\n", n_only_l_to_s))

decision_plot <- ggplot(routing_counts, aes(x = group, y = share_pct, fill = routed_to)) +
  geom_col(width = 0.72, colour = "white", linewidth = 0.3) +
  geom_text(aes(label = ifelse(share_pct >= 8, sprintf("%.0f%%", share_pct), "")),
            position = position_stack(vjust = 0.5), size = 3, colour = "white") +
  scale_fill_manual(values = c(S = COLORS[["S"]], L = COLORS[["L"]]),
                    breaks = c("S", "L"), labels = c("Routed to S", "Routed to L")) +
  scale_y_continuous(limits = c(0, 100), breaks = seq(0, 100, 25),
                     labels = function(x) paste0(x, "%"), expand = expansion(mult = c(0, 0.02))) +
  labs(x = NULL, y = "Routing decisions within group", fill = NULL,
       title = "Router decision quality",
       subtitle = "Groups defined by whether S and L answer each question correctly",
       caption = sprintf("Both correct → L: %d wasted-energy cases. Only L correct → S: %d lost-accuracy cases.",
                         n_both_correct_to_l, n_only_l_to_s)) +
  theme(axis.text.x = element_text(angle = 0, hjust = 0.5),
        plot.caption = element_text(hjust = 0))

save_plot(decision_plot, FINAL_FIGURES, "router_decision_quality.png", 7.0, 4.4)

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
