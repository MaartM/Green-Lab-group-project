"""Sample the fixed set of GSM8K test questions used in every run (llm-routing/questions.jsonl).

  uv run sample_test_questions [--n 100] [--seed 42]

A larger sample that keeps an existing one (here: the 100 questions plus 400 more):

  uv run sample_test_questions --n 500 --include llm-routing/questions.jsonl --out llm-routing/questions_500.jsonl
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
    parser.add_argument("--include", type=Path, help="keep the questions of this sample and add new ones")
    parser.add_argument("--out", type=Path, default=OUT_QUESTIONS, help="output file (default: %(default)s)")
    args = parser.parse_args()

    test = load_jsonl(TEST_SET)
    if args.include:
        kept = [row["qid"] for row in load_jsonl(args.include)]
        rest = sorted(set(range(len(test))) - set(kept))
        qids = sorted(kept + random.Random(args.seed).sample(rest, args.n - len(kept)))
    else:
        qids = sorted(random.Random(args.seed).sample(range(len(test)), args.n))

    with open(args.out, "w", encoding="utf-8") as f:
        for qid in qids:
            row = test[qid]
            f.write(json.dumps({"qid": qid,
                                "question": row["question"],
                                "answer": row["answer"],
                                "reference_answer": parse_reference_answer(row["answer"])}) + "\n")

    print(f"Wrote {len(qids)} questions (seed {args.seed}) to {args.out}")


if __name__ == "__main__":
    main()
