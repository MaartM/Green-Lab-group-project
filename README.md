# LLM routing: when is a larger model worth it?

Green Lab 2026/2027 (VU Amsterdam), team 42. We compare the energy use and accuracy of three ways to answer GSM8K math questions:

- **S**: every question goes to Qwen3.5 2B.
- **L**: every question goes to Qwen3.5 9B.
- **R**: a router sends each question to one of the two models.

The router is a logistic regression on TF-IDF and question features that predicts whether 2B answers a question correctly. R uses 2B when that probability is above 0.55.

## Layout

| Path | Contents |
|---|---|
| `llm-routing/` | Experiment: Experiment Runner config, Ollama servers, query script, answer checking |
| `llm-routing/questions_500.jsonl` | The 500 GSM8K test questions of the main experiment |
| `llm-routing/questions.jsonl` | The 100 GSM8K test questions of the first experiment |
| `llm-routing/router/` | Router features, training and evaluation |
| `scripts/` | Download GSM8K, sample questions, label questions, plot the router figure |
| `analysis/` | R analysis: data preparation, exploration, hypothesis tests, accuracy and trade-off (`main.R`) |
| `data/experiments/llm_routing_500/` | Raw results of the main experiment (500 questions) |
| `data/experiments/llm_routing/` | Raw results of the first experiment (100 questions) |
| `data/labels/` | Whether each model answers each GSM8K question correctly |
| `data/router_model/router.joblib` | The trained router |
| `data/analysis/` | Processed data, test results and figures, per experiment |
| `experiment-runner/` | [Experiment Runner](https://github.com/S2-group/experiment-runner), submodule pinned to `56620fa` |

## Setup

On your laptop, with [uv](https://docs.astral.sh/uv/) installed:

```bash
git clone --recurse-submodules https://github.com/MaartM/Green-Lab-group-project.git
cd Green-Lab-group-project
uv sync
```

The testbed needs Ollama 0.34.4, [EnergiBridge](https://github.com/tdurieux/EnergiBridge), Python 3.12 and two NVIDIA GPUs. Add it to `~/.ssh/config` as `glg2` with key login. Then download the models once:

```bash
scp -O llm-routing/config.py llm-routing/ollama_server.py glg2:
ssh glg2 'python3 ollama_server.py pull'
```

## Run the experiment

Main experiment (500 questions, results in `data/experiments/llm_routing_500/`):

```bash
EXPERIMENT_NAME=llm_routing_500 QUESTIONS=questions_500.jsonl \
  caffeinate -i uv run python experiment-runner/experiment-runner/ llm-routing/RunnerConfig.py
```

First experiment (100 questions, results in `data/experiments/llm_routing/`):

```bash
caffeinate -i uv run python experiment-runner/experiment-runner/ llm-routing/RunnerConfig.py
```

`caffeinate -i` keeps a Mac awake (on Linux use `systemd-inhibit`). The laptop must stay connected for the whole run: about 15 hours for 500 questions, 4.5 hours for 100.

The runner copies the code to the testbed, warms it up for 5 minutes, then does 3 strategies × 30 repetitions = 90 runs in random order with 60 s between runs. 9B runs on GPU 0 and 2B on GPU 1, each in its own Ollama server. Models are loaded before EnergiBridge starts, so the energy covers only answering the questions.

## Results

Each experiment folder in `data/experiments/` contains:

- `run_table.csv`: one row per run. `run_0` is S, `run_1` is L, `run_2` is R.
- `run_<i>_repetition_<j>/energibridge.csv`: EnergiBridge samples (every 200 ms).
- `run_<i>_repetition_<j>/queries.csv`: one row per question, with the model used, latency, tokens, correctness and the answer.

| `run_table.csv` column | Meaning |
|---|---|
| `strategy` | S, L or R |
| `cpu_energy_j`, `gpu_energy_j` | CPU energy and energy of both GPUs (J) |
| `runtime_s` | Measured time (s) |
| `gpu0_util_pct`, `gpu1_util_pct` | Mean utilization of GPU 0 (9B) and GPU 1 (2B) (%) |
| `ram_peak_mib`, `vram_peak_mib` | Peak host memory and peak GPU memory (MiB) |
| `correct` | Correct answers |
| `sent_to_large` | Questions answered by 9B |
| `tokens` | Generated tokens |
| `latency_mean_s`, `latency_p95_s` | Mean and 95th-percentile latency per question (s) |

## Analysis

```bash
Rscript analysis/main.R                # main experiment; needs R with ggplot2
Rscript analysis/main.R llm_routing    # first experiment
```

See [analysis/README.md](analysis/README.md).

## Router

The committed router was trained on `data/labels/train_small.jsonl`. GSM8K is downloaded at a pinned revision.

```bash
uv run download_dataset   # GSM8K into data/dataset/
uv run train_router       # overwrites data/router_model/router.joblib
uv run evaluate_router    # scores it on data/labels/test_small.jsonl
```

Retraining from the committed labels gives the same router. To regenerate labels (needs Ollama):

```bash
uv run label_questions --split train --models small
uv run label_questions --split test --models small large
```

Model answers differ slightly between machines, so new labels may not match the committed ones.

The question files were made with:

```bash
uv run sample_test_questions                                     # llm-routing/questions.jsonl
uv run sample_test_questions --n 500 --include llm-routing/questions.jsonl --out llm-routing/questions_500.jsonl
```
