# Analysis

`main.R` analyses one experiment in `data/experiments/`: the main one, `llm_routing_500`, by default. It recomputes everything from the raw per-run files.

| File | Contents |
|---|---|
| `main.R` | Entry point: sets the experiment and paths, runs the files below in order |
| `config.R` | Constants, variable names, plot theme |
| `load_data.R` | One row per run and correctness per question, from the raw files |
| `stats.R` | Statistical tests, Benjamini-Hochberg correction per research question |
| `01_data_preparation.R` | Completeness, timeline, energy per run, determinism |
| `02_exploration.R` | Descriptive statistics, distributions, temporal dependence, outliers |
| `03_hypothesis_tests.R` | Run-level tests between S, L and R |
| `04_accuracy_tradeoff.R` | Accuracy tests, energy saving (RQ2), router on the full test split |

The script reports results only; interpretation is in the report.

## Run

Tested with R 4.6.1 and ggplot2 4.0.3; the versions used are printed at the end of the output.

```bash
Rscript -e 'install.packages("ggplot2", repos = "https://cloud.r-project.org")'   # once
Rscript analysis/main.R               # data/experiments/llm_routing_500
Rscript analysis/main.R llm_routing   # data/experiments/llm_routing
```

Run it from the repository root, with `Rscript` as above or with `source("analysis/main.R")` in R.

Section 4.4 reads the committed router predictions, `data/analysis/router_test_predictions.csv`. To regenerate them:

```bash
uv run download_dataset
uv run --group analysis python scripts/plot_router_test_split.py
```

Results are printed. Output files, with `<experiment>` the experiment's folder name:

| Path | Contents |
|---|---|
| `data/analysis/<experiment>/runs.csv` | One row per run with all run-level variables |
| `data/analysis/<experiment>/answers.csv` | Correctness per question and strategy |
| `data/analysis/<experiment>/tests_omnibus.csv` | Assumption checks and omnibus test per variable |
| `data/analysis/<experiment>/tests_pairwise.csv` | Pairwise tests and effect sizes |
| `data/analysis/<experiment>/tests_accuracy.csv` | McNemar tests on accuracy |
| `data/analysis/router_test_predictions.csv` | Router predictions, threshold and both models' correctness on all 1,319 test questions (from the Python script) |
| `data/analysis/<experiment>/figures/` | Final figures |
| `data/analysis/<experiment>/figures/exploratory/` | Exploratory figures |
| `data/analysis/figures/router_test_split.png` | Router figure (from the Python script) |
