import argparse
import json
from pathlib import Path

import config
import ollama_server
from answers import is_correct


ROOT = Path(__file__).resolve().parents[2]


def generate_labels():
    """Label each GSM8K question with whether the small model answers it correctly.

    Labels are cached per question. Delete the cache after changing the model,
    prompt or options in config.py, or old labels are silently reused.
    """
    model = config.MODELS["small"]["tag"]
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
                    response = ollama_server.ask("small", question)
                    answer = response["message"]["content"]
                    cached[question] = {
                        "model": model,
                        "question": question,
                        "answer": answer,
                        "correct": int(is_correct(answer, row["answer"])),
                    }
                    stream.write(json.dumps(cached[question], ensure_ascii=False) + "\n")
                    stream.flush()
                    print(f"{split}: labeled {index}/{len(rows)}", flush=True)
                labels.append(cached[question])

        splits[split] = labels
        print(f"Using {len(labels)} {split} labels from {labels_path}", flush=True)

    return splits


def main():
    argparse.ArgumentParser(description="Label GSM8K train and test questions with the small model.").parse_args()
    # Use the small model's own server, as in the experiment. Start it here if
    # it is not running, and stop it again afterwards.
    if not ollama_server.is_up("small"):
        ollama_server.start_strategy("S")
    try:
        generate_labels()
    finally:
        ollama_server.stop_all()


if __name__ == "__main__":
    main()
