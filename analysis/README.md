# Analysis

Notebooks for the 500-question experiment in `data/experiments/llm_routing_500/`. They are saved with their outputs.

| Notebook | Contents |
|---|---|
| `01_data_preparation.ipynb` | Completeness, timeline, energy per run, determinism |
| `02_exploration.ipynb` | Descriptive statistics, distributions, temporal dependence, outliers |
| `03_hypothesis_tests.ipynb` | Run-level hypothesis tests between S, L and R (RQ1, RQ3) |
| `04_accuracy_and_tradeoff.ipynb` | Accuracy, energy–accuracy trade-off (RQ2), router on the full test split |

Shared code:

- `experiment_data.py`: loads the runs.
- `stats.py`: the statistical tests.
- `style.py`: plot colours.

## Run

```bash
uv sync --group analysis
uv run jupyter lab analysis/
```
