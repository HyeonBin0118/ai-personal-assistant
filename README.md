# ai-personal-assistant

자연어로 일상을 입력하면 일정·지출·투두로 분류해 계정별로 저장하고, 백그라운드 스케줄러가 알림을 관리하는 개인 비서 SaaS 서버. pgvector 기반 RAG 파이프라인으로 저장된 개인 데이터에 대한 자연어 질의응답 기능을 제공한다.

## 프로젝트 목적

1. **다중 사용자 동시성 처리** — 여러 사용자가 동시에 같은 API를 사용할 때 발생하는 DB 커넥션 풀, 트랜잭션 충돌, 락 경합 같은 백엔드 고유의 문제를 직접 경험하고 해결한다.
2. **부하 테스트 기반 성능 개선** — 최적화 없이 만든 baseline 서버에 부하를 걸어 병목을 측정하고, 캐싱 전략으로 개선한 뒤 재측정해 정량적인 비교 결과를 남긴다.
3. **RAG 기반 개인 데이터 질의응답** — 저장된 개인 데이터를 pgvector로 임베딩하여 자연어 질문에 답변하는 파이프라인을 구축하고 성능 특성을 측정한다.

## 주요 기능

- 자연어 입력 → 저장/질문 의도 자동 분류
  - 저장 의도: 일정 / 지출 / 투두 분류 후 저장 (임베딩 벡터 포함)
  - 질문 의도: RAG 파이프라인으로 개인 데이터 검색 후 LLM 답변 생성
- 계정별 데이터 격리 (JWT 인증)
- 자연어에 포함된 알림 시간 자동 추출
- 백그라운드 스케줄러 기반 알림 (APScheduler)
- 지난 일정 자동 follow-up
- 대화형 웹 UI

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
    │   LLM 분류 → 임베딩 생성 → DB 저장 (embedding 컬럼 포함)
    │
    └─ 질문 의도 (RAG)
        의도 분류(LLM) → 임베딩 생성 → pgvector 유사도 검색
        → 관련 데이터 컨텍스트 구성 → LLM 답변 생성
    │
    ▼
PostgreSQL (pgvector)
    ├─ schedules / expenses / todos (embedding 컬럼 포함)
    ├─ notifications
    └─ embedding_cache (LLM 분류 결과 캐시)
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
| 7 | RAG 기반 질의응답 추가 | ✅ 완료 |
| 8 | RAG 포함 부하 테스트 | ✅ 완료 |
| 9 | RAG 성능 개선 | 🔄 진행 예정 |

---

## 부하 테스트 결과 요약

### Phase 4~6: 캐싱 전략 비교 (50명, 5분)

| 버전 | /input p50 | /input p95 | 캐시 히트율 | RPS | 에러율 |
|---|---|---|---|---|---|
| no_cache | 1,500ms | 2,800ms | - | 16.9 | 2.2% |
| exact_cache (Redis) | 1,300ms | 2,100ms | 11.5% | 18.7 | 4.1% |
| embedding_naive (Redis O(N)) | 4,600ms | 15,000ms | - | 5.0 | 4.5% |
| **embedding_pgvector** | **1,600ms** | **2,800ms** | **18.2%** | **19.0** | 3.5% |

![Caching Strategy Comparison](loadtest/results/comparison.png)

### Phase 8: RAG 파이프라인 추가 후 (50명, 5분)

| 지표 | no_cache (기존) | RAG 추가 후 | 변화 |
|---|---|---|---|
| /input p50 | 1,500ms | **2,800ms** | 87% 증가 |
| /input p95 | 2,800ms | **5,100ms** | 82% 증가 |
| /input 에러율 | 2.2% | **22.9%** | 급증 |
| 조회 API p95 | 580~690ms | **1,900~2,200ms** | 3배 증가 |
| RPS | 16.9 | **14.5** | 감소 |

**RAG 추가로 인한 병목 원인:**
1. LLM 호출 2회 — 의도 분류(1회) + 답변 생성(1회)으로 기존 대비 API 호출량 2배
2. 에러율 급증 — OpenAI RPD(일일 10,000건) 한도 초과 추정
3. 조회 API 지연 — 임베딩 저장 작업과 DB 커넥션 경합

**개선 방향 (Phase 9):**
- 의도 분류를 LLM 대신 키워드 기반으로 교체 → LLM 호출 1회 절감
- RAG 결과 캐싱 → 동일 질문 반복 시 LLM 재호출 방지

### 캐싱 전략 개선 과정 요약

**Step 1 — 완전 일치 캐싱 (Redis):** 히트율 11.5%, 효과 제한적
**Step 2 — 임베딩 naive (Redis O(N)):** p50 4,600ms로 악화 (선형 스캔 문제)
**Step 3 — 임베딩 pgvector:** 히트율 18.2%, 응답시간 안정화

### 한계 및 개선 여지

5분 부하 테스트는 콜드 스타트 상태 기준이다. OpenAI API 일일 요청 한도(RPD 10,000건)로 인해 5분으로 제한했으며, RAG 파이프라인 추가 후에는 LLM 호출이 2배로 늘어 한도 초과가 더 빠르게 발생한다. 실제 서비스에서는 의도 분류를 키워드 기반으로 교체하고 RAG 결과를 캐싱하면 API 호출량을 크게 줄일 수 있다.

---

## 실행 방법

```bash
cp .env.example .env
docker compose up --build -d
```

마이그레이션:
```bash
set DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_assistant
alembic upgrade head
docker exec -it ai-personal-assistant-db-1 psql -U postgres -d ai_assistant -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

- 웹 UI: `http://localhost:8000/static/login.html`
- API 문서: `http://localhost:8000/docs`

## 라이선스

MIT