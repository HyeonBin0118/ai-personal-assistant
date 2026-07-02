# PLAN

ai-personal-assistant 개발 계획 문서. 각 Phase 완료 시 결과 및 결정사항을 업데이트한다.

## 전체 흐름

```
Phase 1  →  Phase 2  →  Phase 3  →  Phase 4  →  Phase 5  →  Phase 6
 기반        인증/UI     스케줄러    Baseline    분석/개선     재측정
 완료        완료        완료        완료        진행 중        예정
```

---

## Phase 1: 기반 셋업 및 분류 API (완료)

**결과**
- FastAPI + PostgreSQL + Docker Compose 구성
- SQLAlchemy + Alembic 마이그레이션 셋업
- 5개 테이블 스키마 (`users`, `schedules`, `expenses`, `todos`, `notifications`)
- `POST /input` — 자연어 입력을 LLM으로 분류 후 카테고리별 저장
- `GET /schedules`, `GET /expenses`, `GET /todos` 조회 API
- LLM 분류는 GPT-4o-mini JSON 응답 모드 사용
- `MOCK_LLM` 환경변수로 LLM 모킹 ON/OFF 설계에 처음부터 반영

---

## Phase 2: 인증 및 웹 UI (완료)

**결과**
- JWT 기반 회원가입 / 로그인 API
- 계정별 데이터 격리 검증 완료
- HTML + Vanilla JS 기반 대화형 UI (로그인/회원가입 토글, 메인 입력 화면)
- 토큰 localStorage 보관, 만료 시 자동 리다이렉트

**주요 이슈**
- `bcrypt 5.0.0`과 `passlib 1.7.4` 호환 문제 → `bcrypt==4.0.1` 고정으로 해결
- `EmailStr` 사용을 위해 `email-validator` 추가
- 윈도우 환경 CP949 인코딩 문제로 한글 포함 파일 저장 시 주의 필요 → 프롬프트를 영어로 변경

---

## Phase 3: 스케줄러 및 알림 (완료)

**결과**
- APScheduler를 FastAPI `lifespan`에 연결
- 1분 주기 작업 2개:
  - `check_due_notifications` — `notify_at` 도래한 pending 일정에 알림 생성
  - `check_overdue_followups` — 시작 후 10분 지난 pending 일정에 follow-up 알림
- LLM 프롬프트 확장: "N분 전에 알려줘" 표현에서 `notify_at` 자동 계산
- `PATCH /schedules/{id}/status` — 일정 상태 업데이트 API
- 웹 UI 알림 폴링 (15초 주기)

---

## Phase 4: Baseline 부하 테스트 (완료)

**목표**
최적화 없이 만든 현재 서버의 성능 한계를 정량적으로 측정.

**테스트 설계 개선 과정**

초기에는 10개 고정 문장으로 측정했으나 (baseline_fixed), 캐싱 효과 검증 시 캐시 히트율이 비현실적으로 높게 나오는 문제 발견. 실제 사용자 입력 패턴을 반영한 랜덤 문장 생성기(input_generator.py)로 설계 개선 후 재측정(baseline_random).

**baseline_fixed 결과 요약 (10개 고정 문장)**

| 버전 | /input p50 | /input p95 | 조회 p95 | 에러율 |
|---|---|---|---|---|
| Mock 50명 | 48ms | 51ms | 6ms | 0% |
| 실제 LLM 10명 | 1,300ms | 2,600ms | 7ms | 0% |
| 실제 LLM 50명 | 1,300ms | 2,100ms | 330ms | 0% |

**baseline_random 결과 요약 (랜덤 생성 문장, 50명)**

| 버전 | /input p50 | /input p95 | 조회 p95 | 히트율 | 에러율 |
|---|---|---|---|---|---|
| no_cache | 1,500ms | 2,800ms | 580~690ms | - | 2.2% |
| exact_cache | 측정 예정 | - | - | - | - |
| embedding_cache | 측정 예정 | - | - | - | - |

**확인된 병목**
1. LLM 호출 지연 — `/input` p50 1,500ms (Mock 대비 31배)
2. 조회 API 동시 접근 지연 — 50명에서 p95 580~690ms (DB 커넥션 경합)
3. 완전 일치 캐싱 한계 — 히트율 약 10% (사람마다 표현이 달라서)

**측정 시 주의사항 (발견된 문제)**
- 매 버전 측정 전 `docker compose down -v`로 DB 초기화 필수 (데이터 누적 시 조회 API 급격히 느려짐)
- `redis-cli config resetstat`으로 stats 초기화 필수 (누적값이 섞이면 히트율 신뢰도 하락)
- OpenAI RPD(일일 요청 한도) 10,000건 초과 시 테스트 불가 → 하루 측정 가능한 버전 수 제한

원본 데이터: [loadtest/results/](../loadtest/results/)

---

## Phase 5: 분석 및 개선 (진행 중)

**목표**
Phase 4에서 측정한 병목의 원인을 가설로 정리하고 검증 후 개선.

### Step 1: 완전 일치 캐싱 (exact_cache) — 측정 예정

**가설**
Redis에 입력 문장 해시를 키로 캐싱하면 LLM 재호출을 줄일 수 있다.

**한계 확인**
- 히트율 약 10% 예상 (랜덤 입력 기준)
- "커피 4500원"과 "아까 커피 4500원"은 다른 키 → 캐시 미스
- p50 응답시간 개선 제한적 (미스 요청이 여전히 LLM 호출)

### Step 2: 임베딩 유사도 캐싱 (embedding_cache) — 구현 완료, 측정 예정

**가설**
입력 문장을 벡터화해서 의미가 유사한 문장끼리 캐시를 공유하면 히트율을 높일 수 있다.

**구현 방식**
- `text-embedding-3-small`로 입력 문장 벡터화
- Redis에 저장된 벡터들과 코사인 유사도 계산
- 유사도 0.95 이상이면 캐시 히트로 처리
- 캐시 미스 시 LLM 호출 후 벡터 + 결과 같이 저장

**예상 효과**
- 히트율 50~70% (의미 기반이라 표현이 달라도 히트 가능)
- 캐시 히트 요청: 임베딩 API 호출(~20ms) + Redis 조회 → 총 ~30ms
- 캐시 미스 요청: 임베딩(~20ms) + LLM(~1,500ms) → ~1,520ms

**측정 예정 (OpenAI RPD 리셋 후)**

### Step 3: DB 인덱스 + 커넥션 풀 튜닝 — 예정

조회 API p95가 50명에서 580~690ms로 올라가는 문제 해결.
- `user_id + created_at` 복합 인덱스 추가
- SQLAlchemy 커넥션 풀 크기 조정 (기본 5 → 20)

---

## Phase 6: 재측정 및 비교 (예정)

**할 일**
- Phase 4와 동일 시나리오로 재측정 (`loadtest/results/optimized/`에 저장)
- Python 스크립트로 baseline vs optimized 비교 그래프 생성 (matplotlib)
  - 버전별 /input p50/p95 비교 (꺾은선)
  - 캐시 히트율 비교 (막대)
  - RPS 비교
- README에 결과 요약 추가

---

## 부하 테스트 측정 체크리스트

매 버전 측정 전 반드시 순서 준수:

```
① llm_classifier.py 해당 버전 코드로 교체
② docker compose down -v
③ docker compose up -d db redis
④ alembic upgrade head
⑤ python create_test_users.py
⑥ docker compose up --build -d
⑦ redis-cli config resetstat
⑧ Locust 50명 5분 실행
⑨ 결과 저장 (CSV, HTML, 스크린샷)
⑩ 히트율 기록
```

---

## Future (포커스 아님, 여유 시 진행)

- 비동기 처리 (Celery) — LLM 호출을 백그라운드로 분리해 체감 응답 개선
- Rate Limiting — OpenAI API 보호 및 서버 안정성 확보
- CI/CD (GitHub Actions)
- Prometheus / Grafana 모니터링
- AWS EC2 배포
- Discord webhook 알림 옵션