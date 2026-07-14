# PLAN

## 전체 흐름

```
Phase 1~6 완료 → Phase 7 (RAG 추가) 완료 → Phase 8 (RAG 부하 테스트) 완료
→ Phase 9 (RAG 성능 개선) 진행 예정
```

---

## Phase 1~6 (완료)

Phase 1~6 상세 내용은 git 히스토리 및 이전 PLAN 참고.

**핵심 결과 요약:**
- FastAPI + PostgreSQL + pgvector + Redis + APScheduler 기반 서버 구축
- JWT 인증 + 계정별 데이터 격리
- 부하 테스트 캐싱 전략 3단계 비교
  - exact_cache: 히트율 11.5%
  - embedding_naive: O(N) 문제로 p50 4,600ms 악화
  - embedding_pgvector: 히트율 18.2%, 응답시간 안정화
- pytest 5개 통과

---

## Phase 7: RAG 기반 질의응답 추가 (완료)

**구현 내용**

expenses / schedules / todos 테이블에 `embedding vector(1536)` 컬럼 추가. 저장 시 자동으로 임베딩 생성 후 저장.

의도 분류기 추가:
- 저장 의도 → 기존 LLM 분류 + 저장 흐름
- 질문 의도 → RAG 파이프라인

RAG 파이프라인 (`app/services/rag_service.py`):
```
질문 입력
→ 의도 분류 (LLM)
→ 질문 임베딩 생성
→ pgvector로 expenses/schedules/todos 유사도 검색 (유사도 ≥ 0.3)
→ 검색된 데이터를 컨텍스트로 LLM 답변 생성
```

**동작 확인:**
- "오늘 커피 4500원" → expense 저장 + 임베딩 생성
- "이번 달 커피값 어때?" → RAG 검색 → "이번 달 커피값은 총 18,000원이야! (4500원 x 4회)"

---

## Phase 8: RAG 포함 부하 테스트 (완료)

**시나리오**
저장 요청(가중치 4) + 질문 요청(가중치 2) + 조회 API(가중치 5) 혼합.

**결과 (50명, 5분)**

| 지표 | no_cache (RAG 전) | RAG 추가 후 | 변화 |
|---|---|---|---|
| /input p50 | 1,500ms | 2,800ms | 87% 증가 |
| /input p95 | 2,800ms | 5,100ms | 82% 증가 |
| /input 에러율 | 2.2% | 22.9% | 급증 |
| 조회 API p95 | 580~690ms | 1,900~2,200ms | 3배 증가 |
| RPS | 16.9 | 14.5 | 감소 |

**원인 분석**

1. **LLM 호출 2회** — 의도 분류(1회) + 답변 생성(1회). 기존 저장 흐름 대비 API 호출 2배 증가
2. **에러율 22.9%** — OpenAI RPD 10,000건/일 한도 초과 추정. RAG 질문 요청이 LLM 2회 호출하므로 한도 소진 2배 빠름
3. **조회 API 지연** — 저장 시 임베딩 생성 + DB 저장이 동시에 일어나면서 커넥션 경합 발생

원본 데이터: [loadtest/results/rag/](../loadtest/results/rag/)

---

## Phase 9: RAG 성능 개선 (진행 예정)

**목표**
Phase 8에서 발견된 병목을 개선하고 재측정.

### 가설 1: 의도 분류를 키워드 기반으로 교체하면 LLM 호출이 줄어 성능이 개선된다

**현재 문제**
LLM으로 의도 분류하면 요청마다 GPT-4o-mini 호출이 1번 추가됨. 단순 규칙으로도 충분히 판단 가능한 작업에 LLM을 쓰는 게 낭비.

**개선안**
```python
# LLM 대신 키워드 기반 의도 분류
QUERY_KEYWORDS = ["어때", "얼마", "알려줘", "뭐야", "있어", "정리해줘", "요약해줘"]

def classify_intent_fast(text: str) -> str:
    if any(kw in text for kw in QUERY_KEYWORDS):
        return "query"
    return "save"
```

**예상 효과**
- 의도 분류 시간: ~200ms(LLM) → ~1ms(키워드)
- LLM 호출 횟수: 저장 1회, 질문 1회 (기존 대비 절반)
- RPD 한도 소진 속도 절반으로 감소 → 에러율 급감 예상

### 가설 2: RAG 결과를 캐싱하면 동일 질문 반복 시 성능이 개선된다

**개선안**
동일 또는 유사한 질문의 답변을 Redis에 캐싱 (TTL: 5분). pgvector로 질문 유사도 검색 후 캐시 히트 시 LLM 재호출 없이 반환.

**측정 방법**
- 개선 전: Phase 8 결과 (p50 2,800ms, 에러율 22.9%)
- 개선 후: 동일 시나리오 재측정
- 비교: /input p50, 에러율, LLM 호출 횟수

---

## 부하 테스트 측정 체크리스트

```
① 코드 변경 적용
② docker compose down -v
③ docker compose up -d db redis
④ (10초 대기)
⑤ alembic upgrade head
⑥ CREATE EXTENSION IF NOT EXISTS vector
⑦ docker compose up --build -d
⑧ redis-cli flushall + config resetstat
⑨ create_test_users.py 실행
⑩ Locust 50명 5분 실행
⑪ 결과 저장
```

---

## Future

- CI/CD (GitHub Actions)
- AWS EC2 배포
- Rate Limiting
- Prometheus / Grafana 모니터링