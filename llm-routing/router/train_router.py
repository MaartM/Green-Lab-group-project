import argparse

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import FeatureUnion, make_pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

import config
from router.features import question_features
from router.generate_labels import generate_labels


def main() -> None:
    argparse.ArgumentParser(description="Train the router and save it as the experiment's router.").parse_args()

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
    config.ROUTER_FILE.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(router, config.ROUTER_FILE)
    print(f"Saved router to {config.ROUTER_FILE}")


if __name__ == "__main__":
    main()
