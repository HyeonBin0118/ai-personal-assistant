# PLAN

ai-personal-assistant 개발 계획 문서. 각 Phase 완료 시 결과 및 결정사항을 업데이트한다.

## 전체 흐름

```
Phase 1  →  Phase 2  →  Phase 3  →  Phase 4  →  Phase 5  →  Phase 6
 기반        인증/UI     스케줄러    Baseline    캐싱 개선     비교 그래프
 완료        완료        완료        완료         완료          진행 중
```

---

## Phase 1: 기반 셋업 및 분류 API (완료)

**결과**
- FastAPI + PostgreSQL + Docker Compose 구성
- SQLAlchemy + Alembic 마이그레이션 셋업
- 5개 테이블 스키마 (`users`, `schedules`, `expenses`, `todos`, `notifications`)
- `POST /input` — 자연어 입력을 LLM으로 분류 후 카테고리별 저장
- LLM 분류는 GPT-4o-mini JSON 응답 모드 사용
- `MOCK_LLM` 환경변수로 LLM 모킹 ON/OFF 처음부터 설계에 반영

---

## Phase 2: 인증 및 웹 UI (완료)

**결과**
- JWT 기반 회원가입 / 로그인 API
- 계정별 데이터 격리 검증 완료
- HTML + Vanilla JS 기반 대화형 UI

**주요 이슈**
- `bcrypt 5.0.0`과 `passlib 1.7.4` 호환 문제 → `bcrypt==4.0.1` 고정으로 해결
- 윈도우 CP949 인코딩 문제 → LLM 프롬프트를 영어로 변경

---

## Phase 3: 스케줄러 및 알림 (완료)

**결과**
- APScheduler를 FastAPI `lifespan`에 연결
- 1분 주기 작업 2개:
  - `check_due_notifications` — `notify_at` 도래한 pending 일정에 알림 생성
  - `check_overdue_followups` — 시작 후 10분 지난 pending 일정에 follow-up 알림
- LLM 프롬프트 확장: "N분 전에 알려줘" 표현에서 `notify_at` 자동 계산
- 웹 UI 알림 폴링 (15초 주기)

---

## Phase 4: Baseline 부하 테스트 (완료)

**테스트 설계 개선 과정**

초기에는 10개 고정 문장으로 측정했으나 (baseline_fixed), 캐싱 효과 검증 시 캐시 히트율이 비현실적으로 높게 나오는 문제 발견. 실제 사용자 입력 패턴을 반영한 랜덤 문장 생성기(`input_generator.py`)로 설계 개선 후 재측정 (baseline_random).

**baseline_random no_cache 결과 (50명, 5분)**

| 지표 | 수치 |
|---|---|
| /input p50 | 1,500ms |
| /input p95 | 2,800ms |
| /input p99 | 5,200ms |
| 조회 API p95 | 580~690ms |
| RPS | 16.9 |
| 에러율 | 2.2% |

**확인된 병목**
1. LLM 호출 지연 — `/input` p50 1,500ms (Mock 대비 31배)
2. 조회 API 동시 접근 지연 — 50명에서 p95 580~690ms

**측정 시 주의사항 (발견된 문제)**
- 매 버전 측정 전 `docker compose down -v`로 DB 초기화 필수
- `redis-cli flushall` + `config resetstat` 필수
- OpenAI RPD(일일 요청 한도) 10,000건 초과 시 테스트 불가

---

## Phase 5: 캐싱 전략 적용 및 측정 (완료)

**목표**
LLM 호출 병목을 캐싱으로 개선하고 각 전략의 효과를 정량 측정.

### Step 1: 완전 일치 캐싱 — exact_cache

**구현**
입력 문장을 `strip().lower()` 정규화 후 SHA256 해시를 키로 Redis에 저장.

**결과**
- 히트율: 11.5%
- /input p50: 1,300ms (no_cache 1,500ms 대비 소폭 개선)
- /input p95: 2,100ms

**한계**
히트율이 낮아 응답시간 개선 효과가 제한적. "커피 4500원"과 "아까 커피 한 잔 4500원"처럼 같은 의미지만 표현이 달라 캐시 미스 발생.

### Step 2: 임베딩 유사도 캐싱 naive — embedding_naive

**구현**
`text-embedding-3-small`로 벡터화 후 Redis에 저장된 모든 벡터와 코사인 유사도 순차 비교.

**결과**
- /input p50: 4,600ms (no_cache보다 3배 느림)
- /input p95: 15,000ms
- RPS: 5.0 (no_cache 16.9 대비 급감)

**원인**
Redis 전체 키 순차 스캔(O(N)) 구조. 캐시가 쌓일수록 선형으로 느려져 LLM 호출보다 비교 로직이 더 오래 걸리는 역효과 발생.

### Step 3: 임베딩 유사도 캐싱 pgvector — embedding_pgvector

**구현**
PostgreSQL `pgvector` 확장 도입. 임베딩 벡터를 `embedding_cache` 테이블에 저장하고 HNSW 인덱스 기반 코사인 거리 검색(O(log N))으로 교체.

```sql
SELECT result, 1 - (embedding <=> CAST(:embedding AS vector)) AS similarity
FROM embedding_cache
WHERE 1 - (embedding <=> CAST(:embedding AS vector)) >= 0.95
ORDER BY embedding <=> CAST(:embedding AS vector)
LIMIT 1
```

**결과**
- 히트율: 18.2% (exact_cache 11.5% 대비 개선)
- /input p50: 1,600ms (no_cache 수준으로 안정화)
- /input p95: 2,800ms
- RPS: 19.0 (최고치)

**최종 비교**

| 버전 | /input p50 | /input p95 | 히트율 | RPS |
|---|---|---|---|---|
| no_cache | 1,500ms | 2,800ms | - | 16.9 |
| exact_cache | 1,300ms | 2,100ms | 11.5% | 18.7 |
| embedding_naive | 4,600ms | 15,000ms | - | 5.0 |
| embedding_pgvector | 1,600ms | 2,800ms | 18.2% | 19.0 |

---

## Phase 6: 비교 그래프 및 최종 정리 (진행 중)

**목표**
측정 결과를 시각화하고 프로젝트를 마무리한다.

**할 일**
- [ ] Python matplotlib으로 버전별 비교 그래프 생성
  - 버전별 /input p50/p95 비교 (막대 그래프)
  - 캐시 히트율 비교 (막대 그래프)
  - RPS 비교
- [ ] 생성된 그래프 이미지를 README에 삽입
- [ ] PLAN.md 최종 정리
- [ ] 프로필 README 최종 수치 업데이트

---

## 부하 테스트 측정 체크리스트

매 버전 측정 전 반드시 순서 준수:

```
① llm_classifier.py 해당 버전 코드로 교체
② docker compose down -v
③ docker compose up -d db redis
④ (10초 대기)
⑤ alembic upgrade head
⑥ docker compose up --build -d
⑦ redis-cli flushall
⑧ redis-cli config resetstat
⑨ create_test_users.py 실행
⑩ Locust 50명 5분 실행
⑪ 결과 저장 (CSV, HTML, 스크린샷)
⑫ 히트율 기록
```

---

## Future (포커스 아님, 여유 시 진행)

- 비동기 처리 (Celery) — LLM 호출을 백그라운드로 분리해 체감 응답 개선
- Rate Limiting — OpenAI API 보호 및 서버 안정성 확보
- CI/CD (GitHub Actions)
- Prometheus / Grafana 모니터링
- AWS EC2 배포
- Discord webhook 알림 옵션