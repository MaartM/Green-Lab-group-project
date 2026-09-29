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
| `llm-routing/testbed.py` | Runs commands on the testbed and copies files to and from it, over SSH |
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

Experiment Runner runs on your laptop and drives the testbed (`glg2`) over SSH, as the course requires. Add the testbed to `~/.ssh/config` as described in the server usage guide. You will know if the setup was done correctly when you can do: `ssh glg2`   in a shell and it works without a password.

```
Host glgate
    Hostname 145.108.225.3
    Port 42224
    User gl_team42
    IdentityFile ~/.ssh/<your_private_key>
    IdentitiesOnly yes

Host glg2
    User gl_team42
    ProxyJump glgate
```

## Run

Sample the test questions once:

```bash
.venv/bin/python llm-routing/sample_test_questions.py --n 100 --seed 42
```

Run the experiment from the repository root, on your laptop:

```bash
.venv/bin/python experiment-runner/experiment-runner/ llm-routing/RunnerConfig.py
```

Per run, Experiment Runner starts the strategy's Ollama servers on the testbed, runs `run_queries.py` there under EnergiBridge, stops the servers and copies the run's files back. The experiment files are copied to `~/llm-routing` on the testbed at the start of the experiment. Results are written to `llm-routing/experiments/` on the laptop.
