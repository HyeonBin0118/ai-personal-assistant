import json
from sqlalchemy import text
from openai import OpenAI
from app.config import settings

client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

# 키워드 기반 의도 분류 (LLM 호출 없이 1ms 안에 판단)
QUERY_KEYWORDS = [
    "어때", "얼마", "알려줘", "뭐야", "있어", "정리해줘",
    "요약해줘", "보여줘", "알고싶어", "궁금해", "뭐 했어",
    "얼마나", "몇 번", "몇 개", "어디서", "언제", "어떻게",
    "총", "합계", "평균", "많이", "적게", "자주"
]

RAG_PROMPT = """너는 사용자의 개인 비서야. 아래 데이터를 바탕으로 사용자의 질문에 친근하게 답변해.

[관련 데이터]
{context}

[질문]
{question}

데이터에 없는 내용은 "해당 데이터가 없어요"라고 말해. 있는 데이터만 바탕으로 답변해."""


def classify_intent(text_input: str) -> str:
    """LLM 호출 없이 키워드 기반으로 의도 분류. O(n) 키워드 매칭으로 1ms 안에 판단."""
    if any(kw in text_input for kw in QUERY_KEYWORDS):
        return "query"
    return "save"


def get_embedding(text_input: str) -> list[float]:
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text_input,
    )
    return response.data[0].embedding


def search_relevant_data(db, user_id: int, question: str) -> str:
    """pgvector로 관련 데이터 검색 후 컨텍스트 문자열 생성."""
    embedding = get_embedding(question)
    embedding_str = str(embedding)

    results = []

    # 지출 검색
    expenses = db.execute(text("""
        SELECT item, amount, occurred_at,
               1 - (embedding <=> CAST(:emb AS vector)) AS sim
        FROM expenses
        WHERE user_id = :uid AND embedding IS NOT NULL
          AND 1 - (embedding <=> CAST(:emb AS vector)) >= 0.3
        ORDER BY embedding <=> CAST(:emb AS vector)
        LIMIT 5
    """), {"emb": embedding_str, "uid": user_id}).fetchall()

    for r in expenses:
        results.append(f"[지출] {r.item} {int(r.amount)}원 ({r.occurred_at.strftime('%m/%d')})")

    # 일정 검색
    schedules = db.execute(text("""
        SELECT title, start_at, status,
               1 - (embedding <=> CAST(:emb AS vector)) AS sim
        FROM schedules
        WHERE user_id = :uid AND embedding IS NOT NULL
          AND 1 - (embedding <=> CAST(:emb AS vector)) >= 0.3
        ORDER BY embedding <=> CAST(:emb AS vector)
        LIMIT 5
    """), {"emb": embedding_str, "uid": user_id}).fetchall()

    for r in schedules:
        results.append(f"[일정] {r.title} ({r.start_at.strftime('%m/%d %H:%M')}, {r.status})")

    # 투두 검색
    todos = db.execute(text("""
        SELECT content, is_done,
               1 - (embedding <=> CAST(:emb AS vector)) AS sim
        FROM todos
        WHERE user_id = :uid AND embedding IS NOT NULL
          AND 1 - (embedding <=> CAST(:emb AS vector)) >= 0.3
        ORDER BY embedding <=> CAST(:emb AS vector)
        LIMIT 5
    """), {"emb": embedding_str, "uid": user_id}).fetchall()

    for r in todos:
        status = "완료" if r.is_done else "진행중"
        results.append(f"[투두] {r.content} ({status})")

    if not results:
        return "관련 데이터 없음"

    return "\n".join(results)


def generate_answer(question: str, context: str) -> str:
    """검색된 컨텍스트를 바탕으로 LLM 답변 생성."""
    if client is None:
        return f"관련 데이터: {context}"

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": RAG_PROMPT.format(context=context, question=question),
            }
        ],
    )
    return response.choices[0].message.content


def rag_query(db, user_id: int, question: str) -> str:
    """질문 의도 처리 전체 파이프라인."""
    context = search_relevant_data(db, user_id, question)
    return generate_answer(question, context)