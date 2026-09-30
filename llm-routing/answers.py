"""Score answers.

Only a number after '####' counts, for model answers and GSM8K reference
answers alike. An answer without it is wrong, so an unfinished calculation is
never scored from one of its intermediate numbers.
"""

import re
from decimal import Decimal

MARKED_ANSWER = re.compile(r"####\s*([-+]?\d[\d,]*(?:\.\d+)?)")


def extract_answer(text: str) -> Decimal | None:
    matches = MARKED_ANSWER.findall(text)
    return Decimal(matches[-1].replace(",", "")) if matches else None


def is_correct(response: str, gsm8k_answer: str) -> bool:
    predicted = extract_answer(response)
    return predicted is not None and predicted == extract_answer(gsm8k_answer)
