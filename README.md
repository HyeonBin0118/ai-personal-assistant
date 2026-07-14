# ai-personal-assistant

자연어로 일상을 입력하면 일정·지출·투두로 분류해 계정별로 저장하고, 백그라운드 스케줄러가 알림을 관리하는 개인 비서 SaaS 서버.

## 프로젝트 목적

백엔드 측면에서 다음 두 가지를 학습하고 검증하기 위한 프로젝트.

1. **다중 사용자 동시성 처리** — 여러 사용자가 동시에 같은 API를 사용할 때 발생하는 DB 커넥션 풀, 트랜잭션 충돌, 락 경합 같은 백엔드 고유의 문제를 직접 경험하고 해결한다.
2. **부하 테스트 기반 성능 개선** — 최적화 없이 만든 baseline 서버에 부하를 걸어 병목을 측정하고, 캐싱 전략으로 개선한 뒤 재측정해 정량적인 비교 결과를 남긴다.
3. **RAG 기반 개인 데이터 질의응답** — 저장된 개인 데이터(일정·지출·투두)를 pgvector로 임베딩해 자연어 질문에 답변하는 파이프라인을 구축한다.

## 주요 기능

- 자연어 입력 → 저장/질문 의도 분류
  - 저장 의도: 일정 / 지출 / 투두 자동 분류 및 저장
  - 질문 의도: RAG 파이프라인으로 개인 데이터 검색 후 LLM 답변 생성
- 계정별 데이터 격리 (JWT 인증)
- 자연어에 포함된 알림 시간 자동 추출
- 백그라운드 스케줄러가 주기적으로 스캔해 알림 생성 (APScheduler)
- 지난 일정 자동 follow-up
- 일정 상태 관리 (예정 / 완료 / 취소)
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
    ├─ 저장 의도
    │   자연어 → LLM 분류 → 임베딩 생성 → DB 저장 (embedding 컬럼 포함)
    │
    └─ 질문 의도 (RAG)
        자연어 → 임베딩 생성 → pgvector 유사도 검색
        → 관련 데이터 컨텍스트 구성 → LLM 답변 생성
    │
    ▼
PostgreSQL (pgvector 확장)
    ├─ schedules / expenses / todos (embedding 컬럼 포함)
    ├─ notifications
    └─ embedding_cache (LLM 분류 결과 캐시)
    ▲
    │
백그라운드 스케줄러 (APScheduler)
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
| 7 | RAG 기반 질의응답 추가 | 🔄 진행 중 |
| 8 | RAG 포함 부하 테스트 | 예정 |

세부 계획은 [PLAN.md](./PLAN.md) 참고.

---

## 부하 테스트 결과 (Phase 4~6)

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

**Step 1 — 완전 일치 캐싱 (Redis)**
히트율 11.5%로 개선 효과 제한적. 표현이 달라지면 캐시 미스 발생.

**Step 2 — 임베딩 유사도 캐싱 naive (Redis 전체 스캔)**
Redis 전체 키 순차 스캔(O(N)) 구조로 오히려 p50 4,600ms로 악화.

**Step 3 — 임베딩 유사도 캐싱 pgvector**
HNSW 인덱스 기반 O(log N) 검색으로 교체. 히트율 18.2%, 응답시간 안정화.

### 한계 및 개선 여지

5분 부하 테스트는 콜드 스타트 상태 기준이다. 테스트 시간을 5분으로 제한한 이유는 OpenAI API의 일일 요청 한도(RPD 10,000건) 때문으로, 50명 동시 사용자 기준 5분 측정만으로도 약 2,500건의 LLM 호출이 발생한다. 실제 서비스에서 캐시가 충분히 쌓이면 히트율이 40~60%까지 올라갈 것으로 예상된다.

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

```bash
cd loadtest
python create_test_users.py
cd ..
locust -f loadtest/locustfile.py --host=http://localhost:8000
```

## 라이선스

MIT