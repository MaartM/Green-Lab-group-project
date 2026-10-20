# Analysis of one experiment in data/experiments/ (default: llm_routing_500).
#
#   Rscript analysis/main.R [experiment]
#   or, in R from the repository root: source("analysis/main.R")
#
# Prints every result, and writes to data/analysis_results/<experiment folder>/:
#   processed_data/        one row per run, correctness per question
#   statistical_tests/     omnibus, pairwise and accuracy tests
#   figures/final/         figures for the report
#   figures/exploratory/   exploratory figures

# Folder of this script: from Rscript's --file, or from source(), or analysis/ under the working directory.
script <- sub("^--file=", "", grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE))
if (!length(script)) script <- tryCatch(sys.frame(1)$ofile, error = function(e) NULL)
if (is.null(script) || !length(script)) script <- file.path(getwd(), "analysis", "main.R")
ANALYSIS_DIR <- normalizePath(dirname(script))
REPO_ROOT <- normalizePath(file.path(ANALYSIS_DIR, ".."))

if (!exists("EXPERIMENT")) EXPERIMENT <- c(commandArgs(trailingOnly = TRUE), "llm_routing_500")[1]
EXPERIMENT_DIR <- file.path(REPO_ROOT, "data", "experiments", EXPERIMENT)
if (!dir.exists(EXPERIMENT_DIR)) stop("no experiment folder ", EXPERIMENT_DIR)
# Output folder per experiment (other experiments use their own name).
RESULTS_DIR <- file.path(REPO_ROOT, "data", "analysis_results")
OUTPUT_NAMES <- c(llm_routing_500 = "main_experiment_500_questions", llm_routing = "first_experiment_100_questions")
OUT_DIR <- file.path(RESULTS_DIR, if (EXPERIMENT %in% names(OUTPUT_NAMES)) OUTPUT_NAMES[[EXPERIMENT]] else EXPERIMENT)
PROCESSED <- file.path(OUT_DIR, "processed_data")
TESTS <- file.path(OUT_DIR, "statistical_tests")
FINAL_FIGURES <- file.path(OUT_DIR, "figures", "final")
EXPLORATORY <- file.path(OUT_DIR, "figures", "exploratory")
for (dir in c(PROCESSED, TESTS, FINAL_FIGURES, EXPLORATORY)) dir.create(dir, recursive = TRUE, showWarnings = FALSE)
ROUTER_PREDICTIONS <- file.path(RESULTS_DIR, "router_full_test_split", "router_predictions.csv")

for (file in c("config.R", "load_data.R", "stats.R",
               "01_data_preparation.R", "02_exploration.R", "03_hypothesis_tests.R", "04_accuracy_tradeoff.R")) {
  source(file.path(ANALYSIS_DIR, file))
}

cat("\n\n")
print(sessionInfo())
