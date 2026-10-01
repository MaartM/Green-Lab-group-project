"""Sample the fixed set of GSM8K test questions used in every run (llm-routing/questions.jsonl).

  uv run sample_test_questions [--n 100] [--seed 42]
"""

import argparse
import json
import random
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TEST_SET = REPO_ROOT / "data" / "dataset" / "test.jsonl"
OUT_QUESTIONS = REPO_ROOT / "llm-routing" / "questions.jsonl"


def load_jsonl(path: Path) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def parse_reference_answer(answer: str) -> str:
    match = re.search(r"####\s*(.+)$", answer.strip())
    if match is None:
        raise ValueError(f"No '####' final answer in: {answer!r}")
    return match.group(1).replace(",", "").strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--n", type=int, default=100, help="number of questions to sample")
    parser.add_argument("--seed", type=int, default=42, help="random seed for sampling")
    args = parser.parse_args()

    test = load_jsonl(TEST_SET)
    qids = sorted(random.Random(args.seed).sample(range(len(test)), args.n))

    with open(OUT_QUESTIONS, "w", encoding="utf-8") as f:
        for qid in qids:
            row = test[qid]
            f.write(json.dumps({"qid": qid,
                                "question": row["question"],
                                "answer": row["answer"],
                                "reference_answer": parse_reference_answer(row["answer"])}) + "\n")

    print(f"Wrote {args.n} questions (seed {args.seed}) to {OUT_QUESTIONS.name}")


if __name__ == "__main__":
    main()
