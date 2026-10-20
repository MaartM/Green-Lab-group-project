"""Questions of a GSM8K split with the committed correctness labels of one model (data/labels/)."""

import json

import config


def load(split: str, model: str = "small") -> tuple[list[str], list[int]]:
    """Return the split's questions and, for each, whether the model answered it correctly."""
    dataset = config.REPO_ROOT / "data" / "dataset" / f"{split}.jsonl"
    labels = config.REPO_ROOT / "data" / "labels" / f"{split}_{model}.jsonl"
    questions = [json.loads(line)["question"] for line in open(dataset, encoding="utf-8")]
    rows = sorted(map(json.loads, open(labels, encoding="utf-8")), key=lambda row: row["qid"])
    if [row["qid"] for row in rows] != list(range(len(questions))):
        raise ValueError(f"{labels.name} does not label every question of the {split} split exactly once")
    return questions, [int(row["correct"]) for row in rows]
