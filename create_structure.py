import os

# 생성할 폴더 목록
directories = [
    "app/models",
    "app/schemas",
    "app/routers",
    "app/services",
    "app/core",
    "app/static",
    "alembic/versions",
    "tests",
    "loadtest/scenarios",
    "loadtest/results/baseline",
    "loadtest/results/optimized",
    "docs",
]

# 생성할 빈 파일 목록 (touch만 함, 내용은 나중에 채움)
files = [
    "app/__init__.py",
    "app/main.py",
    "app/config.py",
    "app/database.py",
    "app/models/__init__.py",
    "app/models/user.py",
    "app/models/schedule.py",
    "app/models/expense.py",
    "app/models/todo.py",
    "app/models/notification.py",
    "app/schemas/__init__.py",
    "app/schemas/user.py",
    "app/schemas/input.py",
    "app/schemas/schedule.py",
    "app/schemas/expense.py",
    "app/schemas/todo.py",
    "app/schemas/notification.py",
    "app/routers/__init__.py",
    "app/routers/auth.py",
    "app/routers/input.py",
    "app/routers/schedules.py",
    "app/routers/expenses.py",
    "app/routers/todos.py",
    "app/routers/notifications.py",
    "app/services/__init__.py",
    "app/services/llm_classifier.py",
    "app/services/auth_service.py",
    "app/services/scheduler.py",
    "app/core/__init__.py",
    "app/core/security.py",
    "app/core/deps.py",
    "app/core/middleware.py",
    "app/static/index.html",
    "app/static/login.html",
    "app/static/app.js",
    "app/static/style.css",
    "tests/__init__.py",
    "tests/conftest.py",
    "tests/test_auth.py",
    "tests/test_input.py",
    "tests/test_scheduler.py",
    "loadtest/locustfile.py",
    "loadtest/scenarios/multi_user.py",
    "loadtest/scenarios/same_user_race.py",
    "docs/architecture.md",
    "docs/api.md",
    "docs/loadtest_report.md",
]

def main():
    for d in directories:
        os.makedirs(d, exist_ok=True)
        print(f"[DIR]  {d}")

    for f in files:
        os.makedirs(os.path.dirname(f), exist_ok=True)
        if not os.path.exists(f):
            with open(f, "w", encoding="utf-8") as fp:
                pass
            print(f"[FILE] {f}")
        else:
            print(f"[SKIP] {f} (already exists)")

    # loadtest/results는 git에 안 올릴 거라 .gitkeep만 남김
    for d in ["loadtest/results/baseline", "loadtest/results/optimized"]:
        gitkeep = os.path.join(d, ".gitkeep")
        with open(gitkeep, "w") as fp:
            pass

    print("\n✅ 폴더 구조 생성 완료")

if __name__ == "__main__":
    main()