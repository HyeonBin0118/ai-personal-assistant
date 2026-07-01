"""
같은 계정으로 거의 동시에 여러 쓰기 요청을 보냈을 때
race condition이나 데이터 유실이 발생하는지 확인하는 시나리오.
"""
from locust import HttpUser, task, between, constant

TEST_INPUTS = [
    "회의비 30000원",
    "점심 9000원",
    "커피 5000원",
    "택시비 12000원",
    "간식 3500원",
]


class RaceUser(HttpUser):
    # 대기 없이 연속 요청 — race condition 유발 목적
    wait_time = constant(0)

    def on_start(self):
        self.token = None
        res = self.client.post(
            "/auth/login",
            data={"username": "loadtest_user_1@test.com", "password": "loadtest1234"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if res.status_code == 200:
            self.token = res.json().get("access_token")

    @task
    def rapid_expense_input(self):
        """같은 계정으로 지출을 쉬지 않고 계속 입력."""
        if not self.token:
            return

        import random
        self.client.post(
            "/input",
            json={"text": random.choice(TEST_INPUTS)},
            headers={"Authorization": f"Bearer {self.token}"},
            name="/input (race)",
        )