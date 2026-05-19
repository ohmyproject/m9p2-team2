# Beauty Guard — Ingredient Intelligence Dashboard

화장품 MD를 위한 성분 기반 시장 분석 대시보드입니다.  
네이버 DataLab 검색 트렌드, 올리브영 리뷰 감성 분석, 수요-공급 매트릭스를 하나의 화면에서 제공합니다.

---

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| 프론트엔드 | Next.js 14, React 18, TypeScript |
| 백엔드 | FastAPI (Python), uvicorn |
| 데이터베이스 | Supabase (PostgreSQL) |
| 감성 분석 모델 | `nlptown/bert-base-multilingual-uncased-sentiment` (HuggingFace) |
| AI 인사이트 | OpenAI `gpt-4.1-mini` |
| 외부 API | 네이버 DataLab |

---

## 실행 방법

### 사전 요구사항

- Node.js 18+
- Python 3.10+ (conda 환경 권장)
- conda 환경명 `project` 또는 uvicorn이 PATH에 있어야 함

### 패키지 설치

```bash
# 프론트엔드
npm install

# 백엔드 (conda 환경 또는 venv에서)
pip install -r backend/requirements.txt
```

### 환경변수 설정

프로젝트 루트에 `.env` 파일과 `.env.local` 파일을 만듭니다.

**.env** (FastAPI 백엔드용)
```env
NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=
OPENAI_API_KEY=
HF_TOKEN=
PORT=8000
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

**.env.local** (Next.js 프론트엔드용)
```env
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=
NEXT_PUBLIC_DATALAB_API_BASE_URL=http://localhost:8000
```

### 개발 서버 시작 (프론트 + 백엔드 동시 실행)

```bash
npm run dev
```

- Next.js: http://localhost:3000
- FastAPI: http://localhost:8000
- FastAPI 문서: http://localhost:8000/docs

### 개별 실행

```bash
# Next.js만
next dev

# FastAPI만
uvicorn backend.fastapi_app:app --reload --port 8000
```

### 프로덕션 빌드

```bash
npm run build
npm start
```

---

## 화면 구성

### 01 시장 요약
- 성분별 수요-공급 매트릭스 (기회 / 성장 / 공급 과잉 / 관찰)
- 성분 인기 순위 TOP 5 (네이버 / 올리브영 기준 선택 가능)
- 주요 성분 10ml당 가격 분포
- GPT 기반 MD 인사이트 2~5개 자동 생성

### 02 검색 트렌드 분석
- 네이버 DataLab 기반 성분 검색 관심도 추이 (주/월/분기 선택)
- 연령대별 피부 고민 집중도 히트맵 (주름/잡티/트러블/건조/모공)
- 주요 성분 vs 기회 성분 비교
- GPT 기반 트렌드 인사이트 자동 생성

### 03 소비자 리뷰 분석
성분을 선택하면 Supabase의 `product_reviews` 데이터를 분석합니다.

- **감성 도넛 차트**: 긍정 / 중립 / 부정 비율
- **주요 키워드 분석**: 긍정/부정 TOP 5 키워드 + 등장 횟수 및 비율
- **리뷰 반응 상위 제품 TOP 3**: 순위·평점·긍정률·리뷰 수 복합 스코어링
- **피부 타입별 감정 비율**: 건성/복합성/지성/민감성/트러블성 분류
- **GPT 기반 기회 인사이트**: MD가 상세페이지 메시지, 타깃 피부 타입, 성분 조합에 바로 활용 가능한 문장

### 04 경보
- 수요-공급 격차, 부정 리뷰 이슈, 재고 리스크를 자동 감지
- 신제품 기회 후보 / 재고 리스크 성분 / 부정 리뷰 이슈 건수 요약

### 05 AI Agent
- 자연어로 데이터를 질의하는 AI 에이전트 인터페이스

---

## 주요 로직 설명

### 감성 분석 흐름 (03 리뷰 분석)

```
Supabase product_reviews
    ↓ 성분 별칭 포함 검색 (최대 1,000건)
    ↓ 최신순 정렬 후 상위 300건 선택
    ↓ FastAPI /sentiment 엔드포인트 호출 (배치 16건)
        └─ BERT (nlptown/bert-base-multilingual-uncased-sentiment)
           1~2점 → negative / 3점 → neutral / 4~5점 → positive
           백엔드 불가 시 → 단어 포함 여부 fallback
    ↓ 감성 분류 완료 리뷰
```

### 키워드 추출 (`src/lib/reviewAnalysis.ts`)

ML 추출이 아닌 **사전 정의 목록 매칭** 방식입니다.

- 긍정 키워드 15개: `촉촉`, `피부결`, `진정`, `흡수`, `보습` 등 (`src/lib/reviewConstants.ts`)
- 부정 키워드 14개: `자극`, `건조`, `끈적임`, `트러블`, `따가움` 등

긍정 리뷰 묶음 / 부정 리뷰 묶음 각각에서 키워드별 등장 횟수를 세고,  
총 매칭 수 대비 비율(%)을 계산해 TOP 5를 반환합니다.

### AI 인사이트 생성 (`src/lib/generateInsights.ts`)

각 페이지의 집계 데이터를 JSON으로 묶어 OpenAI `gpt-4.1-mini`에 전달합니다.  
페이지별 시스템 프롬프트로 MD 의사결정에 바로 쓸 수 있는 문장 2~5개를 JSON Schema로 강제 출력합니다.

### 네이버 DataLab 요청 안정화

DataLab API 연속 호출 시 `RemoteDisconnected` 오류 방지를 위해:
- 전역 Lock으로 요청 직렬화
- 요청 간 기본 1초 간격 (`NAVER_DATALAB_REQUEST_GAP_SECONDS`)
- 결과 10분 캐시 (새로고침 시 재폭주 방지)
- `.env`에서 조정 가능:

```env
NAVER_DATALAB_REQUEST_GAP_SECONDS=1.5
NAVER_DATALAB_BACKOFF_SECONDS=1.5
NAVER_DATALAB_MAX_RETRIES=5
```

---

## 디렉터리 구조

```
.
├── backend/
│   └── fastapi_app.py       # 감성 분석 API, 네이버 DataLab 프록시
├── src/
│   ├── app/
│   │   ├── page.tsx
│   │   └── api/dashboard/
│   │       ├── page1-insights/   # 시장 요약 GPT 인사이트
│   │       ├── page2-insights/   # 트렌드 GPT 인사이트
│   │       ├── page3-insights/   # 리뷰 GPT 인사이트
│   │       └── page5-agent/      # AI Agent
│   ├── components/
│   │   ├── dashboard/Dashboard.tsx
│   │   └── review-analysis/      # 03 리뷰 분석 컴포넌트 모음
│   └── lib/
│       ├── reviewAnalysis.ts     # 리뷰 수집·감성 분류·키워드 추출·스코어링
│       ├── reviewConstants.ts    # 긍정/부정 키워드 사전
│       ├── sentiment.ts          # FastAPI /sentiment 호출 + fallback
│       ├── generateInsights.ts   # OpenAI 인사이트 생성 공통 함수
│       └── demand-supply-matrix.ts
└── README.md
```
