import json
import random
import hashlib
from datetime import datetime, timedelta

from openai import OpenAI

from app.config import settings
from app.schemas.input import ClassificationResult

client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

CACHE_TTL = 60 * 60 * 24  # 24시간

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


def _make_cache_key(text: str) -> str:
    normalized = text.strip().lower()
    return "llm_cache:" + hashlib.sha256(normalized.encode()).hexdigest()


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
    cache_key = _make_cache_key(text)

    try:
        cached = redis_client.get(cache_key)
        if cached:
            return ClassificationResult(**json.loads(cached))
    except Exception:
        pass

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

    try:
        redis_client.setex(cache_key, CACHE_TTL, json.dumps(parsed))
    except Exception:
        pass

    return ClassificationResult(**parsed)