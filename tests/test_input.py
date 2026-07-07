import pytest
from unittest.mock import patch
from app.schemas.input import ClassificationResult
from datetime import datetime, timedelta


MOCK_SCHEDULE = ClassificationResult(
    category="schedule",
    title="치과 예약",
    start_at=datetime.now() + timedelta(days=1),
    notify_at=None,
)

MOCK_EXPENSE = ClassificationResult(
    category="expense",
    item="커피",
    amount=4500.0,
)

MOCK_TODO = ClassificationResult(
    category="todo",
    content="운동하기",
)


def test_input_unauthorized(client):
    """인증 없으면 401 반환."""
    res = client.post("/input", json={"text": "내일 3시 치과"})
    assert res.status_code == 401


def test_input_schedule(client, auth_headers):
    """일정 분류 후 schedules 테이블에 저장."""
    with patch("app.routers.input.classify", return_value=MOCK_SCHEDULE):
        res = client.post("/input", json={"text": "내일 3시 치과"}, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["category"] == "schedule"
    assert "saved_id" in res.json()


def test_input_expense(client, auth_headers):
    """지출 분류 후 expenses 테이블에 저장."""
    with patch("app.services.llm_classifier.classify", return_value=MOCK_EXPENSE):
        res = client.post("/input", json={"text": "커피 4500원"}, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["category"] == "expense"


def test_input_todo(client, auth_headers):
    """투두 분류 후 todos 테이블에 저장."""
    with patch("app.services.llm_classifier.classify", return_value=MOCK_TODO):
        res = client.post("/input", json={"text": "운동하기"}, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["category"] == "todo"


def test_account_isolation(client, auth_headers):
    """다른 계정의 일정이 조회되지 않아야 함."""
    # 첫 번째 계정으로 일정 등록
    with patch("app.services.llm_classifier.classify", return_value=MOCK_SCHEDULE):
        client.post("/input", json={"text": "내일 3시 치과"}, headers=auth_headers)

    # 두 번째 계정 생성 후 조회
    client.post("/auth/signup", json={"email": "other@test.com", "password": "other1234"})
    res = client.post(
        "/auth/login",
        data={"username": "other@test.com", "password": "other1234"},
    )
    other_token = res.json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}

    schedules = client.get("/schedules", headers=other_headers)
    assert schedules.status_code == 200
    assert schedules.json() == []  # 다른 계정 일정이 보이면 안 됨