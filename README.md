# LLM routing: When is a larger model worth it?

Replication package of a Green Lab 2026/2027 experiment (Vrije Universiteit Amsterdam). It compares the energy consumption and accuracy of three inference strategies on 100 GSM8K math questions:

- **S**: every question goes to the small model, Qwen3.5 2B.
- **L**: every question goes to the large model, Qwen3.5 9B.
- **R**: a router picks one of the two models per question, before generation.

The router is a logistic regression on TF-IDF and question features. It predicts whether the small model answers a question correctly, and R uses the small model when that probability is above 0.55.

## Repository structure

| Location | Contents |
|---|---|
| `llm-routing/config.py` | Models, GPUs, prompt, generation options, router threshold, warm-up, testbed paths |
| `llm-routing/RunnerConfig.py` | Experiment Runner configuration: run table, hooks, measurements |
| `llm-routing/testbed.py` | Runs commands on the testbed and copies files to and from it over SSH |
| `llm-routing/ollama_server.py` | Starts and stops one Ollama server per model, each on its own GPU; machine warm-up |
| `llm-routing/run_queries.py` | Answers the questions with one strategy and logs one row per question |
| `llm-routing/answers.py` | Scores answers: only the number after `####` counts |
| `llm-routing/questions.jsonl` | The 100 sampled GSM8K test questions used in every run |
| `llm-routing/testbed-requirements.txt` | Python libraries installed on the testbed (pinned to `uv.lock`) |
| `llm-routing/router/` | Router: labelling, features, training, evaluation |
| `scripts/` | GSM8K download and question sampling |
| `data/router_model/router.joblib` | The trained router used in the experiment |
| `data/experiments/llm_routing/` | Experiment results (see [Results](#results)) |
| `experiment-runner/` | [Experiment Runner](https://github.com/S2-group/experiment-runner), git submodule pinned to commit `56620fa` (v1.0.1 + 13 commits) |

## Setup

On the laptop that runs Experiment Runner (macOS or Linux), install [uv](https://docs.astral.sh/uv/), then:

```bash
git clone --recurse-submodules https://github.com/MaartM/Green-Lab-group-project.git
cd Green-Lab-group-project
uv sync
```

The testbed needs [Ollama](https://ollama.com) 0.34.4 or newer, [EnergiBridge](https://github.com/tdurieux/EnergiBridge), Python 3.12 and two NVIDIA GPUs. Add it to `~/.ssh/config` under the host alias `glg2`, following the course's server usage guide; `ssh glg2` must log in without a password.

Download the two models on the testbed once:

```bash
scp -O llm-routing/config.py llm-routing/ollama_server.py glg2:
ssh glg2 'python3 ollama_server.py pull'
```

## Run the experiment

From the repository root, on the laptop:

```bash
caffeinate -i uv run python experiment-runner/experiment-runner/ llm-routing/RunnerConfig.py
```

`caffeinate -i` keeps a Mac awake; on Linux use `systemd-inhibit`. The laptop must stay on and connected for the whole experiment (about 4.5 hours).

What happens:

1. Experiment Runner copies the files the testbed needs to `~/green-lab` on the testbed, creates a Python environment there, and warms up the machine for 5 minutes with both models.
2. It runs 3 strategies × 30 repetitions = 90 runs in random order. Each run starts the strategy's Ollama servers and loads the models, answers the 100 questions under EnergiBridge, stops the servers and copies the run's files back.
3. It waits 60 seconds between runs.

Testbed details:

- The large model runs on GPU 0 and the small model on GPU 1, each in its own Ollama server.
- Models are loaded and warmed up before EnergiBridge starts; energy covers only answering the questions.

## Results

see `data/experiments/llm_routing/` has one row per run:

| Column | Meaning |
|---|---|
| `strategy` | S, L or R |
| `cpu_energy_j`, `gpu_energy_j` | CPU energy and energy of both GPUs during the run (J) |
| `runtime_s` | Duration of the measured interval (s) |
| `gpu0_util_pct`, `gpu1_util_pct` | Mean utilization of GPU 0 (large model) and GPU 1 (small model) (%) |
| `ram_peak_mib`, `vram_peak_mib` | Peak host memory and peak GPU memory of both GPUs (MiB) |
| `correct` | Correct answers out of 100 |
| `sent_to_large` | Questions answered by the large model |
| `tokens` | Generated tokens |
| `latency_mean_s`, `latency_p95_s` | Mean and 95th-percentile latency per question, including routing (s) |

## Rebuild the router (optional)

The experiment uses the committed `data/router_model/router.joblib`. It was trained on the committed labels in `data/labels/train_small.jsonl` (whether the small model answers each GSM8K training question correctly). To rebuild it:

```bash
uv run download_dataset       # GSM8K (pinned revision) into data/dataset/
uv run train_router           # trains on data/labels/, overwrites data/router_model/router.joblib
uv run evaluate_router        # router accuracy on the GSM8K test split (data/labels/test_small.jsonl)
```

Retraining from the committed labels reproduces the committed router exactly. To regenerate the labels themselves (with Ollama installed): `uv run label_questions --split train --models small`. Model answers can differ slightly between machines, so regenerated labels, and a router trained on them, may differ from the committed ones.

The question sample is committed too; `uv run sample_test_questions` recreates it from the downloaded test split.
