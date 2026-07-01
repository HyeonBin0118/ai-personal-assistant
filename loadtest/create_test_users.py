import requests

BASE_URL = "http://localhost:8000"
NUM_USERS = 50


def create_test_users():
    created = 0
    skipped = 0

    for i in range(1, NUM_USERS + 1):
        email = f"loadtest_user_{i}@test.com"
        password = "loadtest1234"

        res = requests.post(
            f"{BASE_URL}/auth/signup",
            json={"email": email, "password": password},
        )

        if res.status_code == 201:
            created += 1
        elif res.status_code == 400:
            skipped += 1  # 이미 존재하는 계정
        else:
            print(f"[ERROR] {email}: {res.status_code} {res.text}")

    print(f"완료: {created}개 생성, {skipped}개 이미 존재")


if __name__ == "__main__":
    create_test_users()