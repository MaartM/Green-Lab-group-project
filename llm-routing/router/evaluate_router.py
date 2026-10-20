import argparse
from pathlib import Path

import joblib
from sklearn.metrics import accuracy_score, confusion_matrix

import config
from config import ROUTER_THRESHOLD
from router import labelled


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a saved router model.")
    parser.add_argument(
        "--model", type=Path, default=config.ROUTER_FILE,
        help="Path to a router .joblib file (default: the experiment's router, %(default)s).",
    )
    args = parser.parse_args()
    model_path = args.model
    if not model_path.is_file():
        parser.error(f"Router model not found: {model_path}. Run train_router first.")

    print(f"Loading router from {model_path}")
    router = joblib.load(model_path)
    questions, labels = labelled.load("test")
    probabilities = router.predict_proba(questions)[:, 1]
    predictions = (probabilities > ROUTER_THRESHOLD).astype(int)

    tn, fp, fn, tp = confusion_matrix(labels, predictions, labels=[0, 1]).ravel()
    total = len(labels)
    baseline = max(sum(labels), total - sum(labels)) / total
    accuracy = accuracy_score(labels, predictions)
    small_count = int(predictions.sum())
    print(f"\nTest questions: {total}")
    print(f"Small model: {config.MODELS['small']['tag']}")
    print(f"Small-model success probability threshold: > {ROUTER_THRESHOLD}")
    print(f"Routed to small model: {small_count} ({small_count / total:.2%})")
    print(f"Redirected to large model: {total - small_count} ({1 - small_count / total:.2%})")
    selected_accuracy = f"{tp / small_count:.2%}" if small_count else "N/A"
    print(f"Small-model answer accuracy on routed questions: {selected_accuracy}")
    print(f"Small-model answer accuracy: {sum(labels) / total:.2%}")
    print(f"Majority-class baseline: {baseline:.2%}")
    print(f"Router test accuracy: {accuracy:.2%}")
    print(f"Improvement over baseline: {100 * (accuracy - baseline):+.2f} percentage points")
    print(f"Correctly predicted small-model success: {tp}")
    print(f"Correctly predicted small-model failure: {tn}")
    print(f"Predicted success, but small model failed: {fp} ({fp / total:.2%} of questions)")
    print(f"Predicted failure, but small model succeeded: {fn} ({fn / total:.2%} of questions)")


if __name__ == "__main__":
    main()
