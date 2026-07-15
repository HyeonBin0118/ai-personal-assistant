# ai-personal-assistant

자연어로 일상을 입력하면 일정·지출·투두로 분류해 계정별로 저장하고, 백그라운드 스케줄러가 알림을 관리하는 개인 비서 SaaS 서버. pgvector 기반 RAG 파이프라인으로 저장된 개인 데이터에 대한 자연어 질의응답 기능을 제공한다.

## 프로젝트 목적

1. **다중 사용자 동시성 처리** — 여러 사용자가 동시에 같은 API를 사용할 때 발생하는 DB 커넥션 풀, 트랜잭션 충돌, 락 경합 같은 백엔드 고유의 문제를 직접 경험하고 해결한다.
2. **부하 테스트 기반 성능 개선** — 최적화 없이 만든 baseline 서버에 부하를 걸어 병목을 측정하고, 캐싱 전략과 LLM 호출 최적화로 개선한 뒤 재측정해 정량적인 비교 결과를 남긴다.
3. **RAG 기반 개인 데이터 질의응답** — 저장된 개인 데이터를 pgvector로 임베딩하여 자연어 질문에 답변하는 파이프라인을 구축하고 성능 특성을 측정한다.

## 주요 기능

- 자연어 입력 → 저장/질문 의도 자동 분류 (키워드 기반, ~1ms)
  - 저장 의도: 일정 / 지출 / 투두 분류 후 저장 (임베딩 벡터 포함)
  - 질문 의도: RAG 파이프라인으로 개인 데이터 검색 후 LLM 답변 생성
- 계정별 데이터 격리 (JWT 인증)
- 자연어에 포함된 알림 시간 자동 추출 (예: "내일 3시 회의, 10분 전에 알려줘")
- 백그라운드 스케줄러 기반 알림 (APScheduler, 1분 주기)
- 지난 일정 자동 follow-up
- 대화형 웹 UI (로그인, 자연어 입력, 카테고리별 목록, 실시간 알림 폴링)

## 기술 스택

| 구분 | 사용 도구 |
|---|---|
| 백엔드 | FastAPI, SQLAlchemy, Alembic |
| 데이터베이스 | PostgreSQL + pgvector |
| 캐싱 | Redis |
| 스케줄러 | APScheduler |
| LLM | GPT-4o-mini (분류 + 답변 생성) |
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
    │
    ├─ 저장 의도 (키워드 매칭 ~1ms)
    │   LLM 분류 → 임베딩 생성 → DB 저장 (embedding 컬럼 포함)
    │
    └─ 질문 의도 (RAG)
        임베딩 생성 → pgvector 유사도 검색
        → 관련 데이터 컨텍스트 구성 → LLM 답변 생성
    │
    ▼
PostgreSQL (pgvector)
    ├─ schedules / expenses / todos (embedding 컬럼 포함)
    ├─ notifications
    └─ embedding_cache (LLM 분류 결과 캐시)
    ▲
    │
백그라운드 스케줄러 (APScheduler)
  - 알림 생성 (1분 주기)
  - 지난 일정 follow-up (1분 주기)
```

## 진행 상황

| Phase | 내용 | 상태 |
|---|---|---|
| 1 | 기반 셋업 + 분류 API | ✅ 완료 |
| 2 | JWT 인증 + 웹 UI | ✅ 완료 |
| 3 | 스케줄러 + 알림 | ✅ 완료 |
| 4 | Baseline 부하 테스트 | ✅ 완료 |
| 5 | 캐싱 전략 적용 및 측정 | ✅ 완료 |
| 6 | 비교 그래프 및 정리 | ✅ 완료 |
| 7 | RAG 기반 질의응답 추가 | ✅ 완료 |
| 8 | RAG 포함 부하 테스트 | ✅ 완료 |
| 9 | RAG 성능 개선 | ✅ 완료 |

세부 계획은 [PLAN.md](./PLAN.md) 참고.

---

## 부하 테스트 결과

### Phase 4~6: 캐싱 전략 비교

![Caching Strategy Comparison](loadtest/results/comparison_cache.png)

| 버전 | 설명 | /input p50 | /input p95 | 캐시 히트율 | RPS | 에러율 |
|---|---|---|---|---|---|---|
| no_cache | 캐싱 없음 | 1,500ms | 2,800ms | - | 16.9 | 2.2% |
| exact_cache | Redis 완전 일치 캐싱 | 1,300ms | 2,100ms | 11.5% | 18.7 | 4.1% |
| embedding_naive | Redis 임베딩 O(N) 스캔 | 4,600ms | 15,000ms | N/A | 5.0 | 4.5% |
| **embedding_pgvector** | **pgvector HNSW 인덱스** | **1,600ms** | **2,800ms** | **18.2%** | **19.0** | **3.5%** |

**개선 과정:**
- 완전 일치 캐싱(exact_cache): 히트율 11.5%로 효과 제한적. 표현이 달라지면 캐시 미스 발생
- 임베딩 naive: Redis 전체 키 순차 스캔(O(N))으로 캐시가 쌓일수록 LLM보다 느려지는 역효과
- pgvector: HNSW 인덱스 기반 O(log N) 검색으로 교체하여 히트율 18.2%, 응답시간 안정화

### Phase 7~9: RAG 파이프라인 추가 및 최적화

![RAG Pipeline Comparison](loadtest/results/comparison_rag.png)

| 버전 | 설명 | /input p50 | /input p95 | RPS | 에러율 |
|---|---|---|---|---|---|
| no_cache | 기준선 | 1,500ms | 2,800ms | 16.9 | 2.2% |
| RAG + LLM 의도분류 | RAG 추가, LLM 2회 호출 | 2,800ms | 5,100ms | 14.5 | **22.9%** |
| **RAG + 키워드 의도분류** | **LLM 호출 최적화** | **2,100ms** | **3,600ms** | **17.6** | **1.9%** |

**개선 과정:**
- RAG 추가 시 의도 분류를 LLM으로 처리 → 요청마다 LLM 2회 호출 → OpenAI RPD 한도 초과 → 에러율 22.9%
- 의도 분류를 키워드 기반으로 교체 (200ms → 1ms, LLM 호출 절감) → 에러율 1.9%로 급감, RPS 회복
- 설계 원칙: LLM이 잘하는 일(복잡한 분류, 자연어 생성)은 LLM에, 단순 패턴 매칭은 코드로 처리

### 한계 및 개선 여지

5분 부하 테스트는 콜드 스타트 상태 기준이다. OpenAI API 일일 요청 한도(RPD 10,000건)로 인해 5분으로 제한했으며, 50명 동시 사용자 기준 약 2,500건의 LLM 호출이 발생한다. 실제 서비스에서 캐시가 충분히 쌓이면 pgvector 캐싱 히트율이 40~60%까지 올라갈 것으로 예상된다.

추가 개선 방향:
- **비동기 임베딩 저장** — 저장 시 임베딩 생성을 백그라운드로 분리해 응답시간 단축
- **DB 인덱스 최적화** — user_id + created_at 복합 인덱스로 조회 API 개선
- **CI/CD** — GitHub Actions 기반 자동 배포

---

## 실행 방법

### 사전 준비

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
docker exec -it ai-personal-assistant-db-1 psql -U postgres -d ai_assistant -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 부하 테스트

각 버전 측정 전 초기화 순서:
```bash
docker compose down -v
docker compose up -d db redis
alembic upgrade head
docker exec -it ai-personal-assistant-db-1 psql -U postgres -d ai_assistant -c "CREATE EXTENSION IF NOT EXISTS vector;"
docker compose up --build -d
docker exec -it ai-personal-assistant-redis-1 redis-cli flushall
docker exec -it ai-personal-assistant-redis-1 redis-cli config resetstat
cd loadtest && python create_test_users.py && cd ..
```

Locust 실행:
```bash
locust -f loadtest/locustfile.py --host=http://localhost:8000
```

`http://localhost:8089` 접속 후 Users: 50, Ramp up: 2, Run time: 5m 설정.

## 라이선스

MIT