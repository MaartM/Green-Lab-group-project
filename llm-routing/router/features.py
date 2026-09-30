"""Hand-crafted question features used by the router next to TF-IDF.

This lives in its own module because the saved router refers to it as
router.features.question_features: the experiment needs it to load the router.
"""

import re
from math import log1p


def question_features(questions):
    features = []
    for question in questions:
        text = question.lower()
        words = text.split()
        numbers = [float(n.replace(",", "")) for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text)]
        values = [
            len(words),
            len(text),
            len(numbers),
            sum(c.isdigit() for c in text),
            max(numbers, default=0),
            len(re.findall(r"\d+\.\d+", text)),
            len(re.findall(r"\d+/\d+", text)),
            len(re.findall(r"%|percent", text)),
            sum(w in {"each", "per", "every"} for w in words),
            sum(w in {"more", "less", "than", "twice", "half"} for w in words),
        ]
        features.append([log1p(value) for value in values])
    return features
