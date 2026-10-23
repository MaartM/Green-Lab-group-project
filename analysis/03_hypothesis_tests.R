# 3. Run-level hypothesis tests (RQ1, RQ3, and efficiency for RQ2), with BH correction.

section("3. Run-level hypothesis tests")

cat("\n3.1 Assumptions and omnibus tests (p_bh: Benjamini-Hochberg within each research question)\n")
accuracy <- accuracy_tests(answers)
tests <- run_tests(runs, accuracy)
print(tests$omnibus, row.names = FALSE, digits = 3)
write.csv(tests$omnibus, file.path(TESTS, "omnibus_tests.csv"), row.names = FALSE)

qq <- do.call(rbind, lapply(STRATEGIES, function(strategy) {
  values <- sort(runs$energy_per_query_j[runs$strategy == strategy])
  data.frame(strategy = LABELS[[strategy]], theoretical = qnorm(ppoints(length(values))), value = values)
}))
qq$strategy <- factor(qq$strategy, levels = LABELS)
# Stack the strategies so labels remain readable at a single journal-column width.
qq_plot <- ggplot(qq, aes(theoretical, value, colour = strategy)) +
  geom_point(size = 1.2) +
  geom_smooth(method = "lm", formula = y ~ x, se = FALSE,
              colour = "#898781", linewidth = 0.35) +
  facet_wrap(~strategy, scales = "free_y", ncol = 1) +
  scale_colour_manual(values = setNames(COLORS, LABELS), guide = "none") +
  scale_x_continuous(breaks = -2:2) +
  scale_y_continuous(breaks = scales::breaks_pretty(n = 3)) +
  labs(x = "Theoretical normal quantile", y = "Energy per query (J)") +
  theme_minimal(base_size = 8) +
  theme(
    axis.text = element_text(size = 8, colour = "#444444"),
    axis.title = element_text(size = 9),
    strip.text = element_text(size = 8.5, face = "bold"),
    panel.grid.minor = element_blank(),
    panel.grid.major = element_line(colour = "#e5e5e5", linewidth = 0.25),
    panel.spacing = grid::unit(7, "pt"),
    plot.margin = margin(4, 5, 4, 4),
    plot.background = element_rect(fill = "white", colour = NA),
    legend.position = "none"
  )

# Export the PNG at the intended print size.
ggsave(file.path(EXPLORATORY, "qq_energy_per_query.png"),
       qq_plot, width = 3.35, height = 4.8, units = "in", dpi = 300,
       bg = "white")

cat("\n3.2 Pairwise comparisons\n")
print(tests$pairwise, row.names = FALSE, digits = 4)
write.csv(tests$pairwise, file.path(TESTS, "pairwise_tests.csv"), row.names = FALSE)

cat("\n3.3 Sensitivity: without the first run of the experiment\n")
tests_without_first <- run_tests(runs[runs$order > 0, ], accuracy)
print(tests_without_first$omnibus, row.names = FALSE, digits = 3)

cat("\n3.4 Descriptive only: constant within every strategy (mean, sd)\n")
constant <- tests$omnibus$variable[tests$omnibus$test == "descriptive only (constant)"]
print(aggregate(runs[constant], list(strategy = runs$strategy), function(x) c(mean = mean(x), sd = sd(x))))
