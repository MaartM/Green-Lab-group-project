import argparse
import re
from datetime import datetime, timezone
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import FeatureUnion, make_pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

from router.features import question_features
from router.generate_labels import generate_labels


ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(description="Train and save a named router model.")
    parser.add_argument(
        "--name", default="tfidf-logreg",
        help="Model ID used in the saved filename (default: %(default)s).",
    )
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", args.name):
        parser.error("--name must start with a letter or digit and contain only letters, digits, underscores or hyphens")

    rows = generate_labels()["train"]
    questions = [row["question"] for row in rows]
    labels = [row["correct"] for row in rows]
    X_train, X_test, y_train, y_test = train_test_split(
        questions, labels, test_size=0.2, stratify=labels, random_state=42
    )
    router = make_pipeline(
        FeatureUnion([
            ("text", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
            ("structure", make_pipeline(FunctionTransformer(question_features), StandardScaler())),
        ]),
        LogisticRegression(C=1, max_iter=1000, random_state=42),
    )
    router.fit(X_train, y_train)
    baseline = max(sum(y_test), len(y_test) - sum(y_test)) / len(y_test)
    print(f"Holdout majority-class baseline: {baseline:.2%}")
    print(f"Router holdout accuracy: {router.score(X_test, y_test):.2%}")

    router.fit(questions, labels)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    model_path = ROOT / "data" / "router_model" / f"router-{args.name}-{timestamp}.joblib"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(router, model_path)
    print(f"Saved router to {model_path}")


if __name__ == "__main__":
    main()
