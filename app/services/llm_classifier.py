import json
import random
import hashlib
from datetime import datetime, timedelta

from openai import OpenAI
from sqlalchemy import text

from app.config import settings
from app.schemas.input import ClassificationResult

client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

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


def _get_embedding(text_input: str) -> list[float]:
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text_input,
    )
    return response.data[0].embedding


def _find_similar_in_db(db, embedding: list[float]) -> dict | None:
    try:
        result = db.execute(
            text("""
                SELECT result, 1 - (embedding <=> CAST(:embedding AS vector)) AS similarity
                FROM embedding_cache
                WHERE 1 - (embedding <=> CAST(:embedding AS vector)) >= :threshold
                ORDER BY embedding <=> CAST(:embedding AS vector)
                LIMIT 1
            """),
            {
                "embedding": str(embedding),
                "threshold": SIMILARITY_THRESHOLD,
            }
        ).fetchone()

        if result:
            return json.loads(result.result)
        return None
    except Exception:
        db.rollback()
        return None


def _save_to_db(db, text_input: str, embedding: list[float], parsed: dict) -> None:
    try:
        text_hash = hashlib.sha256(text_input.encode()).hexdigest()
        db.execute(
            text("""
                INSERT INTO embedding_cache (text_hash, original_text, embedding, result)
                VALUES (:hash, :original, CAST(:embedding AS vector), :result)
                ON CONFLICT (text_hash) DO NOTHING
            """),
            {
                "hash": text_hash,
                "original": text_input,
                "embedding": str(embedding),
                "result": json.dumps(parsed),
            }
        )
        db.commit()
    except Exception:
        db.rollback()


def _call_llm(text_input: str) -> dict:
    now = datetime.now().isoformat()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.format(now=now)},
            {"role": "user", "content": text_input},
        ],
    )
    return json.loads(response.choices[0].message.content)


def _mock_classify(text_input: str) -> ClassificationResult:
    category = random.choice(["schedule", "expense", "todo"])
    if category == "schedule":
        start = datetime.now() + timedelta(days=1)
        return ClassificationResult(
            category="schedule",
            title=text_input[:30],
            start_at=start,
            notify_at=start - timedelta(minutes=30),
        )
    elif category == "expense":
        return ClassificationResult(
            category="expense",
            item=text_input[:30],
            amount=float(random.randint(1000, 50000)),
        )
    else:
        return ClassificationResult(
            category="todo",
            content=text_input[:50],
        )


def classify(text_input: str, db=None) -> ClassificationResult:
    if settings.mock_llm or client is None:
        return _mock_classify(text_input)

    # 1. 임베딩 생성
    try:
        embedding = _get_embedding(text_input)
    except Exception:
        # 임베딩 실패 시 LLM 직접 호출
        return ClassificationResult(**_call_llm(text_input))

    # 2. pgvector 유사도 검색
    if db:
        cached = _find_similar_in_db(db, embedding)
        if cached:
            return ClassificationResult(**cached)

    # 3. LLM 호출
    parsed = _call_llm(text_input)

    # 4. DB에 저장 (별도 트랜잭션)
    if db:
        _save_to_db(db, text_input, embedding, parsed)

    return ClassificationResult(**parsed)