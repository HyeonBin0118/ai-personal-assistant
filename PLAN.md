# PLAN

ai-personal-assistant 개발 계획 문서. 각 Phase 완료 시 결과 및 결정사항을 업데이트한다.

## 전체 흐름

```
Phase 1  →  Phase 2  →  Phase 3  →  Phase 4  →  Phase 5  →  Phase 6
 기반        인증/UI     스케줄러    Baseline    분석/개선     재측정
```

핵심 목표는 Phase 4~6의 **부하 테스트 기반 성능 개선 사이클**이다. Phase 1~3은 이 사이클을 돌리기 위한 최소 기능 서버를 만드는 단계.

---

## Phase 1: 기반 셋업 및 분류 API

**목표**
최소 동작 가능한 서버를 띄우고 자연어 입력을 분류·저장하는 API까지 동작 확인.

**할 일**
- [ ] FastAPI 프로젝트 구조 셋업
- [ ] Docker Compose로 PostgreSQL + 앱 컨테이너 구성
- [ ] SQLAlchemy + Alembic 마이그레이션 설정
- [ ] DB 스키마 설계
  - `users`, `schedules`, `expenses`, `todos`, `notifications` 테이블
- [ ] `POST /input` 엔드포인트 — 자연어 입력 받아 LLM으로 분류 후 해당 테이블에 저장
- [ ] `GET /schedules`, `GET /expenses`, `GET /todos` 조회 API
- [ ] 기본 pytest 테스트

**검증 기준**
curl로 "내일 3시 치과" 입력 시 schedules 테이블에 적절한 레코드가 들어가는지 확인.

---

## Phase 2: 인증 및 웹 UI

**목표**
계정별 데이터 격리와 대화형 입력 UI 구성.

**할 일**
- [ ] JWT 기반 회원가입 / 로그인 API
- [ ] 모든 데이터 API에 `user_id` 필터링 적용
- [ ] HTML + Vanilla JS 기반 대화형 입력 화면
- [ ] 폴링 방식 알림 조회 UI (`GET /notifications`)
- [ ] 분류된 항목 목록 표시 화면

**검증 기준**
서로 다른 두 계정으로 접속해 데이터가 섞이지 않는지 확인.

---

## Phase 3: 스케줄러 및 알림

**목표**
백그라운드에서 주기적으로 일정을 스캔해 알림을 생성하고, 지난 일정에 대해 follow-up.

**할 일**
- [ ] APScheduler 통합 (FastAPI lifespan에서 시작)
- [ ] 주기 작업 1: 알림 시간이 도래한 일정을 찾아 `notifications` 테이블에 추가
- [ ] 주기 작업 2: 일정 시간이 지났는데 상태 미확인인 건에 대해 follow-up 알림 생성
- [ ] 일정 등록 시 알림 시간 필드 추가
- [ ] 일정 상태 업데이트 API (`완료` / `취소`)

**검증 기준**
3분 뒤 알림 설정해 등록한 일정에 대해 3분 후 `/notifications`에 새 알림이 보이는지 확인.

---

## Phase 4: Baseline 부하 테스트

**목표**
최적화 없이 만든 현재 서버의 성능 한계를 정량적으로 측정.

**할 일**
- [ ] Locust 시나리오 작성
  - 다중 사용자가 각자 다른 계정으로 `POST /input` 요청
  - 동시 사용자 1, 5, 10, 20, 50, 100 단계별 측정
- [ ] LLM 호출 모킹 버전 별도 작성 (DB·동시성 로직만 측정)
- [ ] 측정 지표: p50 / p95 / p99 latency, RPS, error rate, CPU·메모리 사용량
- [ ] 같은 계정에 동시 쓰기 시나리오 별도 작성 (race condition 확인)
- [ ] 결과 raw 데이터 및 그래프 저장

**검증 기준**
"동시 사용자 N명부터 응답시간 급격 증가" 같은 명확한 변곡점을 찾았는지.

---

## Phase 5: 분석 및 개선

**목표**
Phase 4에서 측정한 병목의 원인을 가설로 정리하고 검증 후 개선.

**할 일**
- [ ] 병목 가설 작성 (예: DB 커넥션 풀 한계, 동기 블로킹, 인덱스 부재 등)
- [ ] 가설별 검증 방법 정의
- [ ] 개선 적용 (해당하는 항목만)
  - DB 커넥션 풀 크기 조정
  - 동기 호출 → `run_in_threadpool` 또는 async
  - 자주 조회되는 데이터 Redis 캐싱
  - 적절한 인덱스 추가
  - 스케줄러 스캔 쿼리 배치화
- [ ] 각 개선 항목별 변경 전·후 비교 자료 정리

**검증 기준**
"가설 → 검증 → 개선" 사이클이 문서로 남아 있는지.

---

## Phase 6: 재측정 및 비교

**목표**
개선 전·후를 동일한 부하 시나리오로 측정해 정량적 비교.

**할 일**
- [ ] Phase 4와 동일한 시나리오로 재측정
- [ ] 개선 전 / 후 그래프 한 화면에 비교
- [ ] README에 결과 요약 추가
- [ ] 한계 및 추가 개선 여지 정리

**검증 기준**
"동시 사용자 N명 기준 p95 latency XX% 감소" 같은 한 줄 요약이 가능해야 함.

---

## Future (포커스 아님, 여유 시 진행)

- LLM 분류를 OpenAI Function Calling으로 정밀화
- 로컬 모델(coder-llm-finetune) 활용 옵션 추가
- Discord webhook 알림 옵션
- CI/CD (GitHub Actions)
- Prometheus / Grafana 모니터링
- Kafka 기반 이벤트 큐 도입