# ai-personal-assistant

자연어로 일상을 입력하면 일정·지출·투두로 분류해 계정별로 저장하고, 백그라운드 스케줄러가 알림을 관리하는 개인 비서 서버.

## 프로젝트 목적

백엔드 측면에서 다음 두 가지를 학습하고 검증하기 위한 프로젝트.

1. **다중 사용자 동시성 처리** — 여러 사용자가 동시에 같은 API를 사용할 때 발생하는 DB 커넥션 풀, 트랜잭션 충돌, 락 경합 같은 백엔드 고유의 문제를 직접 경험하고 해결한다.
2. **부하 테스트 기반 성능 개선** — 최적화 없이 만든 baseline 서버에 부하를 걸어 병목을 측정하고, 캐싱·비동기 처리·인덱싱 등으로 개선한 뒤 재측정해 정량적인 비교 결과를 남긴다.

부하 테스트는 두 가지 모드로 진행한다.
- **Mock 모드** (`MOCK_LLM=true`): LLM 호출을 스텁으로 대체해 DB·동시성 로직만 순수하게 측정
- **실제 LLM 모드** (`MOCK_LLM=false`): OpenAI GPT-4o-mini 실호출까지 포함해 프로덕션 유사 환경 측정

## 주요 기능

- 자연어 입력 → 일정 / 지출 / 투두 자동 분류 및 저장
- 계정별 데이터 격리 (JWT 인증)
- 자연어에 포함된 알림 시간 자동 추출 (예: "내일 3시 회의, 10분 전에 알려줘")
- 백그라운드 스케줄러가 주기적으로 스캔해 알림 생성
- 지난 일정 자동 follow-up ("그 약속 어떻게 됐어?")
- 일정 상태 관리 (예정 / 완료 / 취소)
- 대화형 웹 UI (로그인, 자연어 입력, 카테고리별 목록, 실시간 알림 폴링)

## 기술 스택

| 구분 | 사용 도구 |
|---|---|
| 백엔드 | FastAPI, SQLAlchemy, Alembic |
| 데이터베이스 | PostgreSQL |
| 캐싱 | Redis (Phase 5에서 도입 예정) |
| 스케줄러 | APScheduler |
| LLM | GPT-4o-mini (JSON 모드 분류) |
| 인증 | JWT (python-jose) + bcrypt |
| 프런트엔드 | HTML / Vanilla JS |
| 부하 테스트 | Locust |
| 인프라 | Docker Compose |

## 아키텍처

```
웹 UI (대화형 입력)
    │
    ▼
FastAPI 서버
    ├─ 입력 처리 API  (자연어 → LLM 분류 → DB 저장)
    └─ 조회 API      (알림 및 목록 조회)
    │
    ▼
PostgreSQL DB
    │ (계정별 일정 · 지출 · 투두 · 알림)
    ▲
    │
백그라운드 스케줄러 (APScheduler)
  - 알림 생성 (1분 주기 스캔)
  - 지난 일정 follow-up (1분 주기 스캔)
```

## 진행 상황

| Phase | 내용 | 상태 |
|---|---|---|
| 1 | 기반 셋업 + 분류 API | 완료 |
| 2 | JWT 인증 + 웹 UI | 완료 |
| 3 | 스케줄러 + 알림 | 완료 |
| 4 | Baseline 부하 테스트 | 완료 |
| 5 | 분석 및 개선 | 진행 예정 |
| 6 | 재측정 및 비교 | 진행 예정 |

세부 계획은 [PLAN.md](./PLAN.md), 부하 테스트 결과는 [loadtest/results/](./loadtest/results/) 참고.

## Baseline 측정 결과 요약

Mock 모드와 실제 LLM 모드를 각각 10 / 20 / 50 동시 사용자 기준으로 5분씩 측정.

### Mock 모드 (LLM 없이 DB·서버 로직만 측정)

50 동시 사용자에서도 응답시간이 안정적으로 유지됨. `/input` p95는 유저 수와 무관하게 약 50ms 수준.

### 실제 LLM 모드

- **`/input` p50: 1,300ms** — LLM 호출이 지배적인 병목
- **50 사용자 조회 API p95: 280–330ms** (10 사용자 대비 약 40–50배 증가) — DB 동시 접근 시 조회 지연 발생
- **에러율 0%** — 정상 처리는 유지되나 응답 지연이 심함

### 확인된 병목

1. LLM 호출 지연 (동일 문장 반복 호출도 매번 API 요청)
2. 조회 API의 동시 접근 성능 저하 (인덱스 및 커넥션 풀 구성 재검토 필요)

전체 raw 데이터 및 차트는 [loadtest/results/baseline/](./loadtest/results/baseline/) 참고.

## 실행 방법

### 사전 준비

`.env.example`을 복사해 `.env` 생성 후 값 채우기.

```bash
cp .env.example .env
```

주요 환경변수:
- `DATABASE_URL` — PostgreSQL 접속 정보
- `OPENAI_API_KEY` — OpenAI API 키
- `MOCK_LLM` — 부하 테스트 시 LLM 호출 모킹 여부 (`true` / `false`)

### 서버 실행

```bash
docker compose up --build -d
```

- 웹 UI: `http://localhost:8000/static/login.html`
- API 문서: `http://localhost:8000/docs`

### 마이그레이션

DB 스키마 변경 시 (컨테이너 외부에서 실행):

```bash
set DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_assistant
alembic upgrade head
```

### 부하 테스트

```bash
# 1. 테스트용 계정 생성 (최초 1회)
cd loadtest
python create_test_users.py

# 2. Locust 실행
cd ..
locust -f loadtest/locustfile.py --host=http://localhost:8000
```

브라우저에서 `http://localhost:8089` 접속 후 사용자 수 / ramp up / run time 설정.

## 라이선스

MIT