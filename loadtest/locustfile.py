import random
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner

# 테스트용 계정 정보
NUM_USERS = 50
BASE_EMAIL = "loadtest_user_{}@test.com"
PASSWORD = "loadtest1234"

# 테스트 입력 문장 (랜덤으로 하나씩 사용)
TEST_INPUTS = [
    "내일 3시에 치과 예약",
    "오늘 점심 8500원",
    "주간 보고서 작성하기",
    "다음주 월요일 팀 미팅",
    "어제 커피 4500원",
    "헬스장 가기",
    "친구 생일 선물 사기",
    "이번 달 교통비 50000원",
    "독서 30분 하기",
    "오늘 저녁 장보기 15000원",
]


class AssistantUser(HttpUser):
    wait_time = between(1, 3)  # 요청 사이 1~3초 대기

    def on_start(self):
        """각 가상 유저가 시작할 때 고유 계정으로 로그인."""
        user_id = random.randint(1, NUM_USERS)
        self.email = BASE_EMAIL.format(user_id)
        self.token = None
        self._login()

    def _login(self):
        res = self.client.post(
            "/auth/login",
            data={"username": self.email, "password": PASSWORD},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            name="/auth/login",
        )
        if res.status_code == 200:
            self.token = res.json().get("access_token")
        else:
            self.token = None

    def _auth_headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task(5)
    def post_input(self):
        """핵심 시나리오: 자연어 입력 등록 (가중치 5 — 제일 자주 실행)."""
        if not self.token:
            self._login()
            return

        text = random.choice(TEST_INPUTS)
        res = self.client.post(
            "/input",
            json={"text": text},
            headers=self._auth_headers(),
            name="/input",
        )
        if res.status_code == 401:
            self._login()

    @task(2)
    def get_schedules(self):
        """일정 조회."""
        if not self.token:
            return
        self.client.get(
            "/schedules",
            headers=self._auth_headers(),
            name="/schedules",
        )

    @task(2)
    def get_expenses(self):
        """지출 조회."""
        if not self.token:
            return
        self.client.get(
            "/expenses",
            headers=self._auth_headers(),
            name="/expenses",
        )

    @task(1)
    def get_notifications(self):
        """알림 조회 (가중치 1 — 폴링 흉내)."""
        if not self.token:
            return
        self.client.get(
            "/notifications",
            headers=self._auth_headers(),
            name="/notifications",
        )