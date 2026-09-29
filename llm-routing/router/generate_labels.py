import argparse
import json
import re
from decimal import Decimal
from pathlib import Path

from config import SMALL_MODEL
from ollama_client import chat


ROOT = Path(__file__).resolve().parents[2]


def extract_answer(text):
    matches = re.findall(r"####\s*([-+]?\d[\d,]*(?:\.\d+)?)", text)
    if matches:
        return Decimal(matches[-1].replace(",", ""))
    return None


def generate_labels(model):
    model_dir = ROOT / "data" / "dataset" / model
    model_dir.mkdir(parents=True, exist_ok=True)
    splits = {}

    for split in ("train", "test"):
        with (ROOT / "data" / "dataset" / f"{split}.jsonl").open(encoding="utf-8") as stream:
            rows = [json.loads(line) for line in stream]

        labels_path = model_dir / f"{split}.jsonl"
        cached = {}
        if labels_path.exists():
            with labels_path.open(encoding="utf-8") as stream:
                for line in stream:
                    row = json.loads(line)
                    cached[row["question"]] = row

        labels = []
        with labels_path.open("a", encoding="utf-8") as stream:
            for index, row in enumerate(rows, start=1):
                question = row["question"]
                if question not in cached:
                    response = chat(model, question)
                    answer = response["message"]["content"]
                    predicted = extract_answer(answer)
                    reference = extract_answer(row["answer"])
                    cached[question] = {
                        "model": model,
                        "question": question,
                        "answer": answer,
                        "correct": int(predicted is not None and predicted == reference),
                    }
                    stream.write(json.dumps(cached[question], ensure_ascii=False) + "\n")
                    stream.flush()
                    print(f"{split}: labeled {index}/{len(rows)}", flush=True)
                labels.append(cached[question])

        splits[split] = labels
        print(f"Using {len(labels)} {split} labels from {labels_path}", flush=True)

    return splits


def main():
    parser = argparse.ArgumentParser(description="Generate reusable train and test labels for an Ollama model.")
    parser.add_argument("--model", default=SMALL_MODEL, help="Ollama model name (default: %(default)s).")
    args = parser.parse_args()
    generate_labels(args.model)


if __name__ == "__main__":
    main()
