# ai-personal-assistant

자연어로 일상을 입력하면 일정·지출·투두로 분류해 계정별로 저장하고, 백그라운드 스케줄러가 알림을 관리하는 개인 비서 SaaS 서버.

## 프로젝트 목적

백엔드 측면에서 다음 두 가지를 학습하고 검증하기 위한 프로젝트.

1. **다중 사용자 동시성 처리** — 여러 사용자가 동시에 같은 API를 사용할 때 발생하는 DB 커넥션 풀, 트랜잭션 충돌, 락 경합 같은 백엔드 고유의 문제를 직접 경험하고 해결한다.
2. **부하 테스트 기반 성능 개선** — 최적화 없이 만든 baseline 서버에 부하를 걸어 병목을 측정하고, 캐싱 전략으로 개선한 뒤 재측정해 정량적인 비교 결과를 남긴다.

## 주요 기능

- 자연어 입력 → 일정 / 지출 / 투두 자동 분류 및 저장
- 계정별 데이터 격리 (JWT 인증)
- 자연어에 포함된 알림 시간 자동 추출 (예: "내일 3시 회의, 10분 전에 알려줘")
- 백그라운드 스케줄러가 주기적으로 스캔해 알림 생성 (APScheduler)
- 지난 일정 자동 follow-up ("그 약속 어떻게 됐어?")
- 일정 상태 관리 (예정 / 완료 / 취소)
- 대화형 웹 UI (로그인, 자연어 입력, 카테고리별 목록, 실시간 알림 폴링)

## 기술 스택

| 구분 | 사용 도구 |
|---|---|
| 백엔드 | FastAPI, SQLAlchemy, Alembic |
| 데이터베이스 | PostgreSQL + pgvector |
| 캐싱 | Redis |
| 스케줄러 | APScheduler |
| LLM | GPT-4o-mini (JSON 모드 분류) |
| 임베딩 | text-embedding-3-small |
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
    ├─ 입력 처리 API
    │   자연어 → 임베딩 생성 → pgvector 유사도 검색
    │   → 캐시 히트: 즉시 반환 / 캐시 미스: LLM 분류 → DB 저장
    └─ 조회 API (알림 및 목록 조회)
    │
    ▼
PostgreSQL (pgvector 확장)
    ├─ 계정별 일정 · 지출 · 투두 · 알림
    └─ embedding_cache (임베딩 벡터 + 분류 결과)
    ▲
    │
백그라운드 스케줄러 (APScheduler)
  - 알림 생성 (1분 주기 스캔)
  - 지난 일정 follow-up (1분 주기 스캔)
```

## 진행 상황

| Phase | 내용 | 상태 |
|---|---|---|
| 1 | 기반 셋업 + 분류 API | ✅ 완료 |
| 2 | JWT 인증 + 웹 UI | ✅ 완료 |
| 3 | 스케줄러 + 알림 | ✅ 완료 |
| 4 | Baseline 부하 테스트 | ✅ 완료 |
| 5 | 캐싱 전략 적용 및 측정 | ✅ 완료 |
| 6 | 비교 그래프 및 최종 정리 | ✅ 완료 |

세부 계획은 [PLAN.md](./PLAN.md) 참고.

---

## 부하 테스트 결과

### 테스트 설계

초기에는 10개 고정 문장으로 테스트했으나, 캐시 히트율이 비현실적으로 높게 나오는 문제를 발견했다. 이후 실제 사용자 입력 패턴을 반영한 랜덤 문장 생성기(`input_generator.py`)로 테스트 설계를 개선했다. 생성기는 카페·식사·교통 등 생활 밀착형 지출, 업무·병원·약속 일정, 생활·학습 투두를 다양한 표현으로 조합해 매 요청마다 다른 문장을 생성한다.

### 버전별 측정 결과 (50명 동시 사용자, 5분)

| 버전 | /input p50 | /input p95 | 캐시 히트율 | RPS | 에러율 |
|---|---|---|---|---|---|
| no_cache | 1,500ms | 2,800ms | - | 16.9 | 2.2% |
| exact_cache (Redis) | 1,300ms | 2,100ms | 11.5% | 18.7 | 4.1% |
| embedding_naive (Redis 전체 스캔) | 4,600ms | 15,000ms | - | 5.0 | 4.5% |
| **embedding_pgvector** | **1,600ms** | **2,800ms** | **18.2%** | **19.0** | 3.5% |

### 비교 그래프

![Caching Strategy Comparison](loadtest/results/comparison.png)

### 캐싱 전략 개선 과정

**Step 1 — 완전 일치 캐싱 (Redis exact_cache)**
입력 문장의 SHA256 해시를 키로 Redis에 저장. 히트율 11.5%로 응답시간 소폭 개선. 단, "커피 4500원"과 "아까 커피 한 잔 4500원"처럼 같은 의미지만 표현이 다른 경우 캐시 미스가 발생해 개선 효과가 제한적이었다.

**Step 2 — 임베딩 유사도 캐싱 naive (Redis 전체 스캔)**
입력 문장을 `text-embedding-3-small`로 벡터화 후 Redis에 저장된 모든 벡터와 코사인 유사도 비교. 의미 기반 캐싱이 가능해졌으나 Redis 키 전체를 순차 스캔하는 O(N) 구조로 인해 캐시가 쌓일수록 오히려 LLM 호출보다 느려지는 현상이 발생했다 (p50 4,600ms).

**Step 3 — 임베딩 유사도 캐싱 pgvector (인덱스 검색)**
PostgreSQL `pgvector` 확장 도입. 임베딩 벡터를 DB에 저장하고 HNSW 인덱스 기반 코사인 거리 검색(O(log N))으로 교체. 히트율 18.2%로 exact_cache 대비 개선되었으며 응답시간도 no_cache 수준으로 안정화됐다.

### 한계 및 개선 여지

5분 부하 테스트는 캐시가 거의 비어있는 콜드 스타트 상태를 측정한 것이다. 임베딩 캐싱은 캐시가 충분히 쌓일수록 효과가 커지는 구조라, 실제 서비스에서 하루 이상 운영하면 자주 입력되는 표현들이 누적되어 히트율이 40~60% 수준까지 올라갈 것으로 예상된다. 그 시점에서는 응답시간 개선 효과도 더 뚜렷하게 나타난다.

추가 개선 방향:
- **비동기 처리 (Celery)** — LLM 호출을 백그라운드로 분리해 사용자 체감 응답시간 단축
- **Rate Limiting** — OpenAI API 보호 및 서버 안정성 확보
- **DB 인덱스 최적화** — 조회 API p95 개선 (user_id + created_at 복합 인덱스)

---

## 실행 방법

### 사전 준비

`.env.example`을 복사해 `.env` 생성 후 값 채우기:

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

```bash
set DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_assistant
alembic upgrade head
```

pgvector 확장 활성화 (최초 1회):
```bash
docker exec -it ai-personal-assistant-db-1 psql -U postgres -d ai_assistant -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 부하 테스트

각 버전 측정 전 초기화 순서:
```bash
docker compose down -v
docker compose up -d db redis
alembic upgrade head
cd loadtest && python create_test_users.py && cd ..
docker compose up --build -d
docker exec -it ai-personal-assistant-redis-1 redis-cli flushall
docker exec -it ai-personal-assistant-redis-1 redis-cli config resetstat
```

Locust 실행:
```bash
locust -f loadtest/locustfile.py --host=http://localhost:8000
```

`http://localhost:8089` 접속 후 Users: 50, Ramp up: 2, Run time: 5m 설정.

## 라이선스

MIT