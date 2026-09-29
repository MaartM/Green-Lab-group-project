import json
from urllib.request import Request, urlopen


def chat(model: str, question: str) -> dict:
    body = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Solve the math word problem using at most three short calculation lines. "
                    "Do not repeat the question. On the final line write exactly #### followed "
                    "by the numeric answer, without units or commas."
                ),
            },
            {"role": "user", "content": question},
        ],
        "stream": False,
        "think": False,
        "keep_alive": -1,
        "options": {"temperature": 0, "seed": 42, "num_ctx": 4096, "num_predict": 512},
    }
    request = Request(
        "http://127.0.0.1:11434/api/chat",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=600) as response:
        return json.load(response)
