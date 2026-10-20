from pathlib import Path

from datasets import load_dataset

# Pinned GSM8K version: the question samples and labels refer to questions by position.
REVISION = "740312add88f781978c0658806c59bc2815b9866"


def main() -> None:
    data_dir = Path(__file__).resolve().parents[1] / "data" / "dataset"
    dataset = load_dataset("openai/gsm8k", "main", revision=REVISION)
    data_dir.mkdir(parents=True, exist_ok=True)

    for split_name, split in dataset.items():
        output_path = data_dir / f"{split_name}.jsonl"
        split.to_json(output_path, orient="records", lines=True, force_ascii=False)
        print(f"Saved {len(split)} questions to {output_path}")


if __name__ == "__main__":
    main()
