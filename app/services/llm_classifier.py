import json
import random
from datetime import datetime, timedelta

from openai import OpenAI

from app.config import settings
from app.schemas.input import ClassificationResult

client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

SYSTEM_PROMPT = """너는 사용자의 일상 문장을 분석해서 일정, 지출, 투두 중 하나로 분류하는 비서야.
현재 시각은 {now} 이고, 문장에 상대적인 날짜 표현(내일, 다음 주 화요일 등)이 있으면 이 시각을 기준으로 절대 시각으로 변환해.

일정(schedule)인 경우, 문장에 "N분 전에 알려줘", "1시간 전에 알림" 같은 알림 요청이 있으면 start_at에서 해당 시간만큼 뺀 시각을 notify_at으로 계산해.
알림 요청이 명시되어 있지 않으면 notify_at은 null로 둬.

반드시 아래 JSON 형식으로만 응답해. 다른 설명은 절대 붙이지 마.

{{
  "category": "schedule" | "expense" | "todo",
  "title": "일정일 경우 제목, 아니면 null",
  "start_at": "일정일 경우 ISO 8601 형식 시각, 아니면 null",
  "notify_at": "일정이고 알림 요청이 있으면 ISO 8601 형식 시각, 아니면 null",
  "amount": "지출일 경우 금액(숫자), 아니면 null",
  "item": "지출일 경우 항목명, 아니면 null",
  "content": "투두일 경우 할 일 내용, 아니면 null"
}}
"""


def _mock_classify(text: str) -> ClassificationResult:
    """부하 테스트용 모킹."""
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