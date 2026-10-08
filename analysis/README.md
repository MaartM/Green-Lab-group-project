# Analysis

Notebooks that analyse `data/experiments/llm_routing/`
They are saved with their outputs, so you should be able to read them without running them.

Shared code:

- `experiment_data.py` turns the data per-run files into one row, with energy.
- `stats.py` contains the statistical procedure of Section 4.5.
- `style.py` contains the plot colors.

## Running

```bash
uv sync --group analysis
uv run jupyter lab analysis/
```

Open the notebooks from the `analysis/` folder, so that `experiment_data`, `stats` and `style` can be imported.
