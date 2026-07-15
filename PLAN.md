# PLAN

## 전체 흐름

```
Phase 1~6 (서버 구축 + 캐싱 전략) → Phase 7~9 (RAG 추가 + 최적화) → 완료
```

---

## Phase 1~6 (완료)

**핵심 결과:**
- FastAPI + PostgreSQL + pgvector + Redis + APScheduler 기반 서버
- JWT 인증 + 계정별 데이터 격리
- 캐싱 전략 3단계 비교 (exact → naive → pgvector)
- pytest 5개 통과

---

## Phase 7: RAG 기반 질의응답 추가 (완료)

**구현 내용**
- expenses / schedules / todos 테이블에 `embedding vector(1536)` 컬럼 추가
- 저장 시 자동 임베딩 생성 후 저장
- 의도 분류기: 저장 vs 질문 판단
- RAG 파이프라인 (`app/services/rag_service.py`):
  ```
  질문 → 임베딩 → pgvector 검색 (유사도 ≥ 0.3) → LLM 답변 생성
  ```

**동작 확인:**
- "오늘 커피 4500원" → expense 저장 + 임베딩 생성
- "이번 달 커피값 어때?" → RAG → "이번 달 커피값은 총 18,000원이야!"

---

## Phase 8: RAG 포함 부하 테스트 (완료)

**결과 (50명, 5분)**

| 지표 | no_cache | RAG+LLM분류 | 변화 |
|---|---|---|---|
| /input p50 | 1,500ms | 2,800ms | 87% 증가 |
| /input p95 | 2,800ms | 5,100ms | 82% 증가 |
| /input 에러율 | 2.2% | **22.9%** | 급증 |
| RPS | 16.9 | 14.5 | 감소 |

**원인 분석**
1. LLM 의도 분류(1회) + RAG 답변 생성(1회) = 요청마다 LLM 2회 호출
2. OpenAI RPD 10,000건/일 한도 초과 → 에러율 22.9%
3. 임베딩 저장 + 조회 API DB 커넥션 경합

---

## Phase 9: RAG 성능 개선 (완료)

**가설: 의도 분류를 LLM 대신 키워드 기반으로 교체하면 LLM 호출이 절감되어 에러율이 감소한다**

**개선 내용**

LLM 의도 분류 (~200ms) → 키워드 기반 분류 (~1ms):

```python
QUERY_KEYWORDS = [
    "어때", "얼마", "알려줘", "뭐야", "있어", "정리해줘",
    "요약해줘", "보여줘", "알고싶어", "궁금해", "얼마나",
    "몇 번", "몇 개", "어디서", "언제", "총", "합계"
]

def classify_intent(text_input: str) -> str:
    if any(kw in text_input for kw in QUERY_KEYWORDS):
        return "query"
    return "save"
```

**설계 원칙:** LLM이 잘하는 일(복잡한 분류, 자연어 생성)은 LLM에 맡기고, 단순 패턴 매칭은 코드로 처리한다.

**결과 (50명, 5분)**

| 지표 | RAG+LLM분류 | RAG+키워드분류 | 변화 |
|---|---|---|---|
| /input p50 | 2,800ms | **2,100ms** | 25% 개선 |
| /input p95 | 5,100ms | **3,600ms** | 29% 개선 |
| /input 에러율 | 22.9% | **1.9%** | **급감** |
| RPS | 14.5 | **17.6** | no_cache 수준 회복 |

**가설 검증:** 확인. LLM 호출 횟수 절감으로 RPD 한도 소진 속도가 절반으로 줄어 에러율이 22.9% → 1.9%로 급감했다.

---

## 전체 성능 개선 히스토리

```
no_cache (기준)
  → exact_cache: 히트율 11.5%, 효과 제한적
  → embedding_naive: O(N) 스캔으로 p50 4,600ms 악화
  → embedding_pgvector: 히트율 18.2%, 응답시간 안정화
  → RAG 추가: 에러율 22.9% 급증 (LLM 2회 호출)
  → 키워드 의도분류: 에러율 1.9%, RPS 회복
```

---

## Future

- 비동기 임베딩 저장 (Celery)
- DB 인덱스 최적화 (user_id + created_at 복합 인덱스)
- CI/CD (GitHub Actions)
- AWS EC2 배포
- Rate Limiting
- Prometheus / Grafana 모니터링