"""Label GSM8K questions with whether each model answers them correctly.

Uses the experiment's own prompt, generation options and answer checker
(llm-routing/config.py, ollama_server.ask, answers.is_correct), so labels
describe the models exactly as the experiment runs them. Results are appended
to one JSONL file per model and split, so an interrupted run resumes where it
stopped.

  uv run python scripts/label_questions.py --split test --models small large
  uv run python scripts/label_questions.py --questions llm-routing/questions.jsonl --name experiment
"""

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "llm-routing"))

import config  # noqa: E402
import ollama_server  # noqa: E402
from answers import is_correct  # noqa: E402

LABELS_DIR = REPO_ROOT / "data" / "labels"


def load_questions(path: Path, id_field: str | None) -> list[dict]:
    rows = [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]
    for index, row in enumerate(rows):
        row["qid"] = row[id_field] if id_field else index
    return rows


def label(model: str, questions: list[dict], out_path: Path) -> None:
    done = set()
    if out_path.exists():
        done = {json.loads(line)["qid"] for line in out_path.open(encoding="utf-8")}
    todo = [q for q in questions if q["qid"] not in done]
    print(f"{model}: {len(done)} labelled, {len(todo)} to go -> {out_path}", flush=True)
    started = time.monotonic()
    with out_path.open("a", encoding="utf-8") as stream:
        for count, q in enumerate(todo, start=1):
            result = ollama_server.ask(model, q["question"])
            response = result["message"]["content"]
            stream.write(json.dumps({
                "qid": q["qid"], "model": config.MODELS[model]["tag"],
                "correct": int(is_correct(response, q["answer"])),
                "tokens": result.get("eval_count"), "response": response,
            }, ensure_ascii=False) + "\n")
            stream.flush()
            if count % 50 == 0 or count == len(todo):
                rate = (time.monotonic() - started) / count
                print(f"  {model}: {count}/{len(todo)}, {rate:.2f} s/question", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--split", choices=["train", "test"], help="GSM8K split in data/dataset/")
    source.add_argument("--questions", type=Path, help="a JSONL file with question and answer fields")
    parser.add_argument("--name", help="output name for --questions (default: file stem)")
    parser.add_argument("--models", nargs="+", default=["small", "large"], choices=list(config.MODELS))
    args = parser.parse_args()

    if args.split:
        questions = load_questions(REPO_ROOT / "data" / "dataset" / f"{args.split}.jsonl", None)
        name = args.split
    else:
        questions = load_questions(args.questions, "qid")
        name = args.name or args.questions.stem
    LABELS_DIR.mkdir(parents=True, exist_ok=True)

    for model in args.models:
        if not ollama_server.is_up(model):
            ollama_server.start(model)
            ollama_server.warm_up(model)
        try:
            label(model, questions, LABELS_DIR / f"{name}_{model}.jsonl")
        finally:
            ollama_server.stop_all()


if __name__ == "__main__":
    main()
