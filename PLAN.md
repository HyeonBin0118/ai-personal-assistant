# PLAN

ai-personal-assistant 개발 계획 문서.

## 전체 흐름

```
Phase 1~6 완료 → Phase 7 (RAG 추가) → Phase 8 (RAG 포함 부하 테스트)
```

---

## Phase 1: 기반 셋업 및 분류 API (완료)

- FastAPI + PostgreSQL + Docker Compose
- SQLAlchemy + Alembic 마이그레이션
- `POST /input` — 자연어 분류 후 저장
- `MOCK_LLM` 환경변수로 LLM 모킹 설계

---

## Phase 2: 인증 및 웹 UI (완료)

- JWT 기반 회원가입 / 로그인
- 계정별 데이터 격리 검증
- HTML + Vanilla JS 대화형 UI

**주요 이슈**
- `bcrypt 5.0.0` + `passlib 1.7.4` 호환 문제 → `bcrypt==4.0.1` 고정
- 윈도우 CP949 인코딩 문제 → 프롬프트 영어로 변경

---

## Phase 3: 스케줄러 및 알림 (완료)

- APScheduler 1분 주기 작업 2개
- `notify_at` 자동 계산
- 웹 UI 알림 폴링 (15초 주기)

---

## Phase 4: Baseline 부하 테스트 (완료)

**테스트 설계 개선**
초기 10개 고정 문장 → 랜덤 문장 생성기(`input_generator.py`)로 개선.

**baseline_random no_cache 결과 (50명, 5분)**

| 지표 | 수치 |
|---|---|
| /input p50 | 1,500ms |
| /input p95 | 2,800ms |
| 조회 API p95 | 580~690ms |
| RPS | 16.9 |
| 에러율 | 2.2% |

**확인된 병목**
1. LLM 호출 지연 — p50 1,500ms
2. 조회 API 동시 접근 지연

**측정 주의사항**
- 매 버전 `docker compose down -v` 필수
- `redis-cli flushall` + `config resetstat` 필수
- OpenAI RPD 10,000건/일 한도 → 5분 측정 기준 채택

---

## Phase 5: 캐싱 전략 적용 및 측정 (완료)

### Step 1: exact_cache (Redis 완전 일치)
- 히트율: 11.5%
- /input p50: 1,300ms
- 한계: 표현이 달라지면 캐시 미스

### Step 2: embedding_naive (Redis 전체 스캔)
- /input p50: 4,600ms (오히려 악화)
- 원인: O(N) 순차 스캔이 LLM보다 느림

### Step 3: embedding_pgvector
- 히트율: 18.2%
- /input p50: 1,600ms (안정화)
- HNSW 인덱스 O(log N) 검색

**최종 비교**

| 버전 | /input p50 | /input p95 | 히트율 | RPS |
|---|---|---|---|---|
| no_cache | 1,500ms | 2,800ms | - | 16.9 |
| exact_cache | 1,300ms | 2,100ms | 11.5% | 18.7 |
| embedding_naive | 4,600ms | 15,000ms | - | 5.0 |
| embedding_pgvector | 1,600ms | 2,800ms | 18.2% | 19.0 |

---

## Phase 6: 비교 그래프 및 최종 정리 (완료)

- matplotlib 비교 그래프 생성 (`loadtest/results/comparison.png`)
- README에 그래프 삽입
- pytest 5개 통과

---

## Phase 7: RAG 기반 질의응답 추가 (진행 중)

**목표**
저장된 개인 데이터(일정·지출·투두)를 pgvector로 임베딩하여 자연어 질문에 답변하는 RAG 파이프라인 구축.

**배경**
지금까지는 "저장"만 가능했다. RAG를 추가하면 진짜 비서처럼 "이번 달 지출 어때?", "다음 주 일정 뭐 있어?" 같은 질문에 답할 수 있게 된다. 이미 pgvector 인프라가 있어서 자연스러운 확장이다.

**할 일**

- [x] expenses / schedules / todos 테이블에 `embedding vector(1536)` 컬럼 추가
- [ ] Alembic 마이그레이션
- [ ] 의도 분류기 추가 — 입력이 "저장"인지 "질문"인지 판단
- [ ] 저장 시 임베딩 생성 후 같이 저장
- [ ] RAG 서비스 구현
  - 질문 임베딩 생성
  - pgvector로 관련 데이터 검색
  - 검색된 데이터를 컨텍스트로 LLM 답변 생성
- [ ] `POST /query` 엔드포인트 추가
- [ ] 웹 UI에 질의응답 기능 추가

**예시 흐름**
```
사용자: "이번 달 커피값 얼마야?"
→ 의도 분류: 질문
→ 질문 임베딩 생성
→ expenses 테이블에서 pgvector 유사도 검색
→ "커피 4500원", "라떼 5000원" 등 관련 데이터 추출
→ LLM: "이번 달 커피류 지출은 총 X원이에요"
```

---

## Phase 8: RAG 포함 부하 테스트 (예정)

**목표**
RAG 파이프라인(임베딩 생성 + 벡터 검색 + LLM 답변)의 성능을 측정하고 병목을 찾아 개선.

**예상 병목**
- 임베딩 API 호출 (~50ms)
- pgvector 검색 (데이터 많을수록 느려질 수 있음)
- LLM 답변 생성 (~1,500ms)
→ 세 단계가 순차적으로 쌓여서 기존보다 무거운 시나리오

**측정 방향**
- 저장 vs 질문 요청 비율별 성능 비교
- 데이터 누적량에 따른 벡터 검색 속도 변화
- 캐싱 전략 적용 여지 탐색

---

## 부하 테스트 측정 체크리스트

```
① llm_classifier.py 해당 버전으로 교체
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

## Future

- CI/CD (GitHub Actions)
- AWS EC2 배포
- Rate Limiting
- Prometheus / Grafana 모니터링
- Discord webhook 알림