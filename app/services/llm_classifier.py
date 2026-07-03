import json
import random
import hashlib
import numpy as np
from datetime import datetime, timedelta

from openai import OpenAI

from app.config import settings
from app.schemas.input import ClassificationResult

client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

CACHE_TTL = 60 * 60 * 24
SIMILARITY_THRESHOLD = 0.95

SYSTEM_PROMPT = (
    "You are an assistant that classifies Korean daily life sentences into one of three categories: "
    "schedule, expense, or todo. "
    "Current time is {now}. "
    "For relative date expressions (tomorrow, next Monday, etc.), convert them to absolute datetime based on current time. "
    "For schedule, if the sentence contains a notification request like '30 minutes before' or '1 hour before', "
    "calculate notify_at by subtracting that time from start_at. If no notification is requested, set notify_at to null. "
    "Respond ONLY in the following JSON format with no additional text:\n"
    '{{"category": "schedule" | "expense" | "todo", '
    '"title": "schedule title or null", '
    '"start_at": "ISO 8601 datetime or null", '
    '"notify_at": "ISO 8601 datetime or null", '
    '"amount": "expense amount as number or null", '
    '"item": "expense item name or null", '
    '"content": "todo content or null"}}'
)


def _get_embedding(text: str) -> list[float]:
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def _find_similar_cache(redis_client, embedding: list[float]) -> dict | None:
    keys = redis_client.keys("llm_embed:*")
    best_score = 0.0
    best_result = None

    for key in keys:
        cached = redis_client.get(key)
        if not cached:
            continue
        try:
            data = json.loads(cached)
            score = _cosine_similarity(embedding, data["embedding"])
            if score > best_score:
                best_score = score
                best_result = data["result"]
        except Exception:
            continue

    if best_score >= SIMILARITY_THRESHOLD:
        return best_result
    return None


def _mock_classify(text: str) -> ClassificationResult:
    category = random.choice(["schedule", "expense", "todo"])
    if category == "schedule":
        start = datetime.now() + timedelta(days=1)
        return ClassificationResult(
            category="schedule",
            title=text[:30],
            start_at=start,
            notify_at=start - timedelta(minutes=30),
        )
    elif category == "expense":
        return ClassificationResult(
            category="expense",
            item=text[:30],
            amount=float(random.randint(1000, 50000)),
        )
    else:
        return ClassificationResult(
            category="todo",
            content=text[:50],
        )


def classify(text: str) -> ClassificationResult:
    if settings.mock_llm or client is None:
        return _mock_classify(text)

    from app.core.redis_client import redis_client

    try:
        embedding = _get_embedding(text)
        cached_result = _find_similar_cache(redis_client, embedding)
        if cached_result:
            return ClassificationResult(**cached_result)

        now = datetime.now().isoformat()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT.format(now=now)},
                {"role": "user", "content": text},
            ],
        )
        raw = response.choices[0].message.content
        parsed = json.loads(raw)

        cache_key = "llm_embed:" + hashlib.sha256(text.encode()).hexdigest()
        redis_client.setex(
            cache_key,
            CACHE_TTL,
            json.dumps({"embedding": embedding, "result": parsed}),
        )

        return ClassificationResult(**parsed)

    except Exception:
        now = datetime.now().isoformat()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT.format(now=now)},
                {"role": "user", "content": text},
            ],
        )
        raw = response.choices[0].message.content
        parsed = json.loads(raw)
        return ClassificationResult(**parsed)