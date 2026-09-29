# LLM routing: When is a larger model worth it?

Green Lab 2026/2027, team 42, Vrije Universiteit Amsterdam.

This repository contains the experiment that compares three inference strategies on GSM8K math questions: always using a small LLM, always using a large LLM, and routing each question to one of the two before generation. It measures energy consumption, accuracy, latency, GPU utilization and memory usage.

## Repository structure

| Path | Contents |
|---|---|
| `llm-routing/config.py` | Models, strategies, generation options and prompt |
| `llm-routing/sample_test_questions.py` | Samples the fixed set of GSM8K test questions used in every run |
| `llm-routing/gsm8k_test.jsonl` | The GSM8K test split the sample is drawn from |
| `llm-routing/ollama_server.py` | Starts, warms up and stops one Ollama server per model, each on its own GPU |
| `llm-routing/run_queries.py` | Answers every question with one strategy and logs one row per question |
| `llm-routing/RunnerConfig.py` | Experiment Runner configuration: run table, randomization, cool-down, measurement |
| `experiment-runner/` | [Experiment Runner](https://github.com/S2-group/experiment-runner), included as a git submodule pinned to commit `56620fa` |

## Setup

Clone with the submodule:

```bash
git clone --recurse-submodules https://github.com/MaartM/Green-Lab-group-project.git
cd Green-Lab-group-project
```

If you already cloned without it:

```bash
git submodule update --init
```

Create a Python environment and install the dependencies:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

The experiment also needs [Ollama](https://ollama.com) and [EnergiBridge](https://github.com/tdurieux/EnergiBridge) on the measured machine.

## Run

Sample the test questions once:

```bash
.venv/bin/python llm-routing/sample_test_questions.py --n 100 --seed 42
```

Run the experiment from the repository root:

```bash
.venv/bin/python experiment-runner/experiment-runner/ llm-routing/RunnerConfig.py
```

Results are written to `llm-routing/experiments/`.
