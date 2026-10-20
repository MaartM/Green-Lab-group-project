# Analysis of one experiment in data/experiments/ (default: llm_routing_500).
#
#   Rscript analysis/main.R [experiment]
#   or, in R from the repository root: source("analysis/main.R")
#
# Prints every result, and writes to data/analysis/<experiment>/:
#   *.csv                  processed data and test results
#   figures/*.png          final figures
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
OUT_DIR <- file.path(REPO_ROOT, "data", "analysis", EXPERIMENT)
FIGURES <- file.path(OUT_DIR, "figures")
EXPLORATORY <- file.path(FIGURES, "exploratory")
dir.create(EXPLORATORY, recursive = TRUE, showWarnings = FALSE)

for (file in c("config.R", "load_data.R", "stats.R",
               "01_data_preparation.R", "02_exploration.R", "03_hypothesis_tests.R", "04_accuracy_tradeoff.R")) {
  source(file.path(ANALYSIS_DIR, file))
}

cat("\n\n")
print(sessionInfo())
