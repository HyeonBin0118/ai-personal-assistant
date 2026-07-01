# PLAN

ai-personal-assistant 개발 계획 문서. 각 Phase 완료 시 결과 및 결정사항을 업데이트한다.

## 전체 흐름

```
Phase 1  →  Phase 2  →  Phase 3  →  Phase 4  →  Phase 5  →  Phase 6
 기반        인증/UI     스케줄러    Baseline    분석/개선     재측정
 완료        완료        완료        완료         진행 예정      진행 예정
```

핵심 목표는 Phase 4~6의 **부하 테스트 기반 성능 개선 사이클**이다. Phase 1~3은 이 사이클을 돌리기 위한 최소 기능 서버를 만드는 단계였다.

---

## Phase 1: 기반 셋업 및 분류 API (완료)

**목표**
최소 동작 가능한 서버를 띄우고 자연어 입력을 분류·저장하는 API까지 동작 확인.

**결과**
- FastAPI + PostgreSQL + Docker Compose 구성
- SQLAlchemy + Alembic 마이그레이션 셋업
- 5개 테이블 스키마 구축 (`users`, `schedules`, `expenses`, `todos`, `notifications`)
- `POST /input` — 자연어 입력을 LLM으로 분류 후 카테고리별 테이블에 저장
- `GET /schedules`, `GET /expenses`, `GET /todos` 조회 API
- LLM 분류는 GPT-4o-mini의 JSON 응답 모드 사용
- 부하 테스트를 위한 `MOCK_LLM` 환경변수 처음부터 설계에 반영

---

## Phase 2: 인증 및 웹 UI (완료)

**목표**
계정별 데이터 격리와 대화형 입력 UI 구성.

**결과**
- JWT 기반 회원가입 / 로그인 API (`python-jose` + `bcrypt`)
- 모든 데이터 API에 `Depends(get_current_user)`로 인증 강제
- 계정별 데이터 격리 검증 (서로 다른 계정의 데이터가 조회에 안 섞이는 것 확인)
- HTML + Vanilla JS 기반 대화형 UI
  - 로그인 / 회원가입 페이지 (모드 토글)
  - 메인 페이지 (자연어 입력, 카테고리 탭, 목록 렌더링, 알림 배너)
- 토큰은 `localStorage` 보관, 만료 시 자동 로그인 페이지 리다이렉트

**주요 이슈 및 해결**
- `bcrypt 5.0.0`과 `passlib 1.7.4` 호환성 문제 → `bcrypt==4.0.1` 고정으로 해결
- `EmailStr` 사용을 위해 `email-validator` 추가

---

## Phase 3: 스케줄러 및 알림 (완료)

**목표**
백그라운드에서 주기적으로 일정을 스캔해 알림을 생성하고, 지난 일정에 대해 follow-up.

**결과**
- APScheduler를 FastAPI `lifespan`에 연결 (앱 시작 시 자동 실행)
- 1분 주기 작업 2개:
  - `check_due_notifications` — `notify_at`이 도래한 pending 일정에 대해 알림 생성
  - `check_overdue_followups` — 시작 후 10분 지난 pending 일정에 follow-up 알림 생성
- LLM 프롬프트 확장: 문장에 "N분 전에 알려줘" 같은 표현이 있으면 `notify_at` 자동 계산
- `POST /input` 응답 메시지에 알림 시각 안내 포함
- `PATCH /schedules/{id}/status` — 일정 상태 업데이트 (완료 / 취소) API
- 웹 UI 알림 폴링 (15초 주기, 안 읽은 알림을 배너로 표시 후 자동 읽음 처리)

---

## Phase 4: Baseline 부하 테스트 (완료)

**목표**
최적화 없이 만든 현재 서버의 성능 한계를 정량적으로 측정.

**결과**

Locust 시나리오 구성:
- 50개 고정 테스트 계정 사전 생성
- 4개 엔드포인트에 가중치 부여 (`/input`, `/schedules`, `/expenses`, `/notifications`)
- 사용자당 1~3초 대기 시간 (실사용 흐름 모방)

두 가지 모드로 각각 10 / 20 / 50 동시 사용자, 5분씩 측정.

**Mock 모드 결과 요약**

| 사용자 | /input p50 | /input p95 | 조회 p95 | RPS | 에러율 |
|---|---|---|---|---|---|
| 10 | 48ms | 50ms | 5ms | 4.95 | 0% |
| 20 | 48ms | 50ms | 6ms | ~10 | 0% |
| 50 | 48ms | 51ms | 6ms | 24.4 | 0% |

LLM을 스텁으로 대체한 상태에서는 50 사용자에서도 병목 없이 안정적으로 처리됨.

**실제 LLM 모드 결과 요약**

| 사용자 | /input p50 | /input p95 | 조회 p95 | RPS | 에러율 |
|---|---|---|---|---|---|
| 10 | 1,300ms | 2,600ms | 7ms | 2.0 | 0% |
| 20 | 1,300ms | ~2,400ms | ~150ms | ~4 | 0% |
| 50 | 1,300ms | 2,100ms | 280–330ms | 7.8 | 0% |

**확인된 병목**

1. **LLM 호출 지연** — `/input` p50이 Mock 대비 27배(48ms → 1,300ms) 증가. LLM API 호출이 단일 요청 지연의 지배적인 요인.
2. **조회 API 지연 급증** — 50 사용자에서 `/schedules`, `/expenses`, `/notifications`의 p95가 10 사용자 대비 약 40–50배 증가. 동시 DB 접근 시 커넥션 경합 및 인덱스 부재로 인한 지연.

원본 데이터: [loadtest/results/baseline/](../loadtest/results/baseline/)

---

## Phase 5: 분석 및 개선 (진행 예정)

**목표**
Phase 4에서 측정한 병목의 원인을 가설로 정리하고 검증 후 개선.

**가설 및 개선 방향**

### 가설 1: LLM 호출이 `/input`의 주요 병목이다

**검증 방법**
Mock 모드 vs 실제 LLM 모드 응답시간 비교 (이미 확인됨: 48ms → 1,300ms).

**개선안**
Redis 캐싱 도입. 동일하거나 정규화 후 동일한 입력 문장에 대해 LLM 재호출 없이 캐시된 분류 결과 반환.
- 캐시 키: 입력 문장 해시
- TTL: 24시간
- 예상 효과: 캐시 히트 시 응답시간 1,300ms → 5ms 수준 (99% 단축)

### 가설 2: 조회 API의 p95 급증은 인덱스 부재와 커넥션 풀 크기 때문이다

**검증 방법**
- `EXPLAIN ANALYZE`로 현재 쿼리 실행 계획 확인
- SQLAlchemy 커넥션 풀 크기 조정 실험 (기본 5 → 20)

**개선안**
- 자주 조회되는 컬럼에 인덱스 추가 (`user_id + created_at`, `user_id + occurred_at` 등 복합 인덱스)
- 커넥션 풀 크기 및 max_overflow 조정
- 스케줄러 스캔 쿼리를 배치화 (현재는 유저별 개별 쿼리)

### 개선 적용 순서

1. Redis 캐싱 (LLM 결과)
2. DB 인덱스 추가 (Alembic 마이그레이션)
3. 커넥션 풀 튜닝
4. (필요 시) 스케줄러 쿼리 배치화

각 개선 항목별로 개별 커밋 및 변경 전·후 비교 자료 정리.

---

## Phase 6: 재측정 및 비교 (진행 예정)

**목표**
개선 전·후를 동일한 부하 시나리오로 측정해 정량적 비교.

**할 일**
- Phase 4와 동일한 시나리오로 재측정 (`loadtest/results/optimized/`에 저장)
- Python 스크립트로 baseline vs optimized 비교 그래프 생성
  - 동시 사용자별 응답시간 변화 (꺾은선)
  - 엔드포인트별 p95 비교 (막대)
  - 개선 전후 RPS 비교
- README에 결과 요약 추가 (예: "동시 사용자 50명 기준 `/input` p95 XX% 감소")
- 한계 및 추가 개선 여지 정리

**검증 기준**
"가설 → 검증 → 개선 → 재측정"의 사이클이 문서와 그래프로 남는지.

---

## Future (포커스 아님, 여유 시 진행)

- LLM 분류를 OpenAI Function Calling으로 정밀화
- Discord webhook 알림 옵션
- CI/CD (GitHub Actions)
- Prometheus / Grafana 모니터링
- Kafka 기반 이벤트 큐 도입
- AWS EC2 배포