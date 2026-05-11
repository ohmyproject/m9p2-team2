# 화장품 성분 트렌드 대시보드

화장품 성분/기능 키워드의 검색 관심도, 가격 분포, 수요-공급 구조를 한 화면에서 확인하는 Next.js 기반 대시보드입니다.

현재 프로젝트는 기존 HTML/CSS/JS + FastAPI 프로토타입을 Next.js App Router 구조로 이전한 상태입니다.  
프론트엔드는 Next.js가 담당하고, 데이터는 Supabase와 FastAPI/Naver DataLab API를 함께 사용합니다.

---

## 기술 스택

- **Frontend**: Next.js 14, React 18, TypeScript
- **Backend/API**
  - Next.js Route Handler
  - FastAPI 배포 서버
  - Naver DataLab API
  - OpenAI API
- **Database**: Supabase
- **Data Source**
  - Supabase `product_snapshots`
  - Supabase `product_main_ingredients`
  - Naver DataLab 검색 관심도
  - 올리브영/다이소 크롤링 상품 데이터

---

## 주요 기능

### 1. 시장 요약

대시보드 1페이지에서 성분 시장의 핵심 지표를 요약합니다.

- 분석 제품 수
- 분석 성분 수
- 검색 관심도 증감률
- 급상승 성분 수
- 공급 부족 성분 수

---

### 2. 기능 급상승 순위 TOP 5

기능별 키워드 그룹을 기준으로 Naver DataLab 검색 관심도를 조회합니다.

예시 기능 그룹:

- 쿨링진정
- 수분보습
- 안티에이징
- 브라이트닝
- 기미잡티
- 주름탄력
- 모공
- 각질결
- 트러블진정
- 장벽
- 피지유분

계산 방식:

- 최근 7일 검색 관심도 평균
- 이전 7일 검색 관심도 평균
- 전주 대비 증감률 계산
- 전주 대비 증가율 기준 TOP 5 표시

---

### 3. 성분 인기 순위 TOP 5

성분별 키워드 그룹을 기준으로 Naver DataLab 검색 관심도를 조회합니다.

예시 성분 그룹:

- 레티놀/레티날
- PDRN
- 나이아신아마이드
- 히알루론산
- 병풀/시카
- 세라마이드
- 판테놀
- 비타민C
- 글루타티온
- 트라넥사믹애씨드
- 바쿠치올
- 어성초
- 티트리
- AHA/BHA/PHA 등

계산 방식:

- 최근 7일 검색 관심도 평균 기준으로 TOP 5 표시
- 오른쪽에는 전주 대비 증감률 표시

주의:  
Naver DataLab 값은 절대 검색량이 아니라 상대 지수입니다. 비교 대상 키워드 그룹이 바뀌면 순위도 달라질 수 있습니다.

---

### 4. 주요 성분 10ml당 가격 분포

Supabase의 가격 데이터를 사용해 성분별 가격 분포를 시각화합니다.

사용 테이블:

- `product_snapshots`
- `product_main_ingredients`

사용 컬럼 예시:

- `goods_no`
- `regular_price`
- `sales_price`
- `discount`
- 상품명 컬럼
- 용량 컬럼
- 성분명 컬럼

전처리 규칙:

- `sales_price`가 없는 데이터는 가격 차트에서 제외
- `regular_price`와 `discount`가 모두 `NULL`이면:
  - `regular_price = sales_price`
  - `discount = 0%`
- `ml`과 `g`는 동일한 용량 단위로 취급
- `regular_price`, `sales_price` 모두 10ml당 가격으로 변환

차트 기능:

- 판매가/정가 토글
- 성분별 가격 분포 표시
- 가격 포인트 hover 시 제품 정보 표시
  - 제품명
  - 성분명
  - 10ml당 가격
  - 원래 판매가 또는 정가
  - 용량
  - `goods_no`

---

### 5. 수요-공급 매트릭스

성분별 수요와 공급을 0~100 지수로 환산해 4개 영역으로 분류합니다.

#### 수요 데이터

수요는 Naver DataLab 성분 검색 관심도를 사용합니다.

| 지표 | 설명 |
| --- | --- |
| `demand_score` | 최근 7일 DataLab 지수 평균을 0~100으로 정규화 |
| `prev_demand_score` | 이전 7일 DataLab 지수 평균 |
| `demand_wow` | 전주 대비 검색 증가율 |
| `demand_mom` | 전월 대비 검색 증가율 |

#### 공급 데이터

공급은 Supabase의 제품/성분 원천 데이터를 사용합니다.

| 지표 | 설명 |
| --- | --- |
| `supply_count` | 성분별 현재 제품 수 |
| `prev_supply_count` | 전주 성분별 제품 수 |
| `supply_score` | 현재 제품 수를 0~100으로 정규화 |
| `prev_supply_score` | 전주 제품 수를 0~100으로 정규화 |
| `supply_wow` | 전주 대비 제품 수 증가율 |
| `supply_growth_count` | 전주 대비 제품 수 증가량 |

#### 수요-공급 격차

| 지표 | 설명 |
| --- | --- |
| `gap` | `demand_score - supply_score` |
| `prev_gap` | `prev_demand_score - prev_supply_score` |
| `gap_delta` | `gap - prev_gap` |

해석:

- `gap > 0`: 수요가 공급보다 큼
- `gap_delta > 0`: 전주보다 수요-공급 격차가 커짐

#### 매트릭스 영역

| 영역 | 조건 | 의미 |
| --- | --- | --- |
| 성장 | 수요 높음 + 공급 높음 | 이미 시장이 형성된 성분 |
| 기회 | 수요 높음 + 공급 낮음 | 수요 대비 공급이 부족한 성분 |
| 공급 과잉 | 수요 낮음 + 공급 높음 | 공급 대비 관심도가 낮은 성분 |
| 관찰 | 수요 낮음 + 공급 낮음 | 추이 관찰이 필요한 성분 |

#### 표시 대상 버블 선정 기준

전체 성분 중 아래 조건에 해당하는 성분을 우선 표시합니다.

1. 수요 또는 공급 변화율이 큰 성분
2. 기회 점수가 높은 성분
3. 공급 과잉 리스크가 높은 성분
4. 각 사분면을 대표하는 상위 N개 성분
5. 최근 급상승/급락 등 알림 조건에 걸린 성분

#### 시각화 규칙

- X축: 공급 지수
- Y축: 수요 지수
- 진한 버블: 현재 위치
- 옅은 잔상: 전주 위치에서 현재 위치까지 이동한 흔적
- 현재 위치에 가까울수록 잔상이 더 크고 진함
- 성분명은 버블 위에 표시
- 버블 크기는 성분별 공급 제품 수를 기본으로, 현재 수요 지수를 일부 반영한 상대적 규모

---

### 6. 핵심 인사이트 요약

페이지 내 데이터를 기반으로 OpenAI API를 사용해 핵심 인사이트를 요약합니다.

요약 대상:

- 기능 급상승 순위
- 성분 인기 순위
- 가격 분포 주요 특징/이상치
- 수요-공급 매트릭스 결과

보안 원칙:

- OpenAI API Key는 브라우저에 노출하지 않습니다.
- 클라이언트에서 OpenAI API를 직접 호출하지 않습니다.
- 서버 사이드 Route Handler 또는 FastAPI에서만 `OPENAI_API_KEY`를 사용합니다.

---

## 프로젝트 구조

```text
.
├── backend/
│   ├── fastapi_app.py
│   └── requirements.txt
├── legacy/
│   ├── index.html
│   ├── assets/
│   └── fastapi_app.py
├── public/
├── src/
│   ├── app/
│   │   ├── api/
│   │   │   └── dashboard/
│   │   ├── globals.css
│   │   ├── layout.tsx
│   │   └── page.tsx
│   ├── components/
│   │   └── dashboard/
│   │       └── Dashboard.tsx
│   ├── lib/
│   │   ├── demand-supply-matrix.ts
│   │   ├── mock-data.ts
│   │   ├── naver-datalab-groups.ts
│   │   ├── price-distribution.ts
│   │   └── types.ts
│   └── utils/
│       └── supabase/
│           ├── client.ts
│           ├── middleware.ts
│           └── server.ts
├── .env
├── .env.local
├── .env.example
├── next.config.js
├── package.json
├── package-lock.json
└── tsconfig.json
```

---

## 환경변수

실제 키는 Git에 올리지 않습니다.

### `.env`

서버에서만 사용하는 비밀키입니다.

```env
NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=
OPENAI_API_KEY=

PORT=8000
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### `.env.local`

Next.js에서 사용하는 공개 가능한 값입니다.

```env
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=

NEXT_PUBLIC_DATALAB_API_BASE_URL=https://cosmetic-api-clae.onrender.com
```

주의:

- `NAVER_CLIENT_SECRET`, `OPENAI_API_KEY`에는 `NEXT_PUBLIC_`을 붙이면 안 됩니다.
- `NEXT_PUBLIC_`이 붙은 값은 브라우저에 노출될 수 있습니다.
- Supabase service role key는 클라이언트에 절대 노출하지 않습니다.

---

## 실행 방법

### 1. 패키지 설치

```bash
npm install
```

### 2. Next.js 실행

```bash
npm run dev
```

브라우저에서 확인:

```text
http://localhost:3000
```

만약 3000번 포트가 사용 중이면 Next.js가 3001, 3002 등 다른 포트를 사용할 수 있습니다.  
터미널에 표시되는 `Local:` 주소를 확인하세요.

### 3. 빌드 확인

```bash
npm run build
```

---

## FastAPI 사용

현재 배포된 FastAPI Base URL:

```text
https://cosmetic-api-clae.onrender.com
```

API Docs:

```text
https://cosmetic-api-clae.onrender.com/docs
```

현재 사용 가능한 API:

```text
GET /health
GET /products
GET /products?q=리들샷
GET /products?brand=VT
GET /products/{goods_no}
GET /rankings
GET /rankings?collected_date=2026-05-05&sort_type=판매순&limit=24
GET /ingredients/search?q=나이아신아마이드
GET /ingredients/search?q=판테놀&kind=full
GET /dashboard/summary
```

로컬 FastAPI를 실행해야 하는 경우:

```bash
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.fastapi_app:app --host 127.0.0.1 --port 8000
```

로컬 API를 사용할 경우 `.env.local`을 아래처럼 변경합니다.

```env
NEXT_PUBLIC_DATALAB_API_BASE_URL=http://localhost:8000
```

변경 후 Next.js dev 서버를 재시작해야 반영됩니다.

---

## Naver DataLab 안정화 참고

Naver DataLab API는 짧은 시간에 많은 요청을 보내면 연결이 끊기거나 응답이 실패할 수 있습니다.

안정화 전략:

- 서버 사이드에서만 Naver API 호출
- 요청 직렬화 또는 batch 처리
- 반복 요청 캐시
- 실패 시 에러 메시지 요약
- DataLab credentials는 서버 환경변수에서만 사용

관련 조정 환경변수 예시:

```env
NAVER_DATALAB_REQUEST_GAP_SECONDS=1.5
NAVER_DATALAB_BACKOFF_SECONDS=1.5
NAVER_DATALAB_MAX_RETRIES=5
```

---

## 개발 시 주의사항

### Git에 올리면 안 되는 파일

`.gitignore`에 아래 항목이 포함되어 있어야 합니다.

```gitignore
node_modules
.next
.cache
.pytest_cache
__pycache__
.venv
.env
.env.local
.crawler_home
```

### 수정 범위 주의

기능별 주요 파일:

| 기능 | 주요 파일 |
| --- | --- |
| 대시보드 화면 | `src/components/dashboard/Dashboard.tsx` |
| 가격 분포 | `src/lib/price-distribution.ts` |
| 수요-공급 매트릭스 | `src/lib/demand-supply-matrix.ts` |
| DataLab 키워드 그룹 | `src/lib/naver-datalab-groups.ts` |
| 공통 타입 | `src/lib/types.ts` |
| 전역 스타일 | `src/app/globals.css` |
| Supabase 클라이언트 | `src/utils/supabase/*` |

---

## 기존 프로토타입

기존 HTML/CSS/JS + FastAPI 프로토타입은 `legacy/` 폴더에 보관되어 있습니다.

```text
legacy/
├── index.html
├── assets/
└── fastapi_app.py
```

기존 프로토타입을 임시로 확인하려면:

```bash
cd legacy
python3 -m http.server 8080
```

브라우저에서 확인:

```text
http://localhost:8080
```

---

## 현재 리뷰 데이터 상태

현재 리뷰 본문 데이터는 아직 없습니다.

- `product_reviews`: 0건
- `review_count`: 상품 페이지에서 수집한 전체 리뷰 수

리뷰 본문 기반 감성/키워드 분석은 리뷰 수집 이후 연결이 필요합니다.

---

## 트러블슈팅

### 1. `localhost:3000`이 안 열리는 경우

터미널에서 `npm run dev` 실행 결과의 `Local:` 주소를 확인하세요.

예:

```text
Local: http://localhost:3002
```

이 경우 브라우저에서 `http://localhost:3002`로 접속합니다.

### 2. FastAPI 요청 오류가 나는 경우

`.env.local`의 Base URL을 확인합니다.

```env
NEXT_PUBLIC_DATALAB_API_BASE_URL=https://cosmetic-api-clae.onrender.com
```

배포 API가 살아있는지 확인:

```text
https://cosmetic-api-clae.onrender.com/health
```

### 3. Supabase 조회가 안 되는 경우

확인할 것:

- `.env.local`의 Supabase URL/key
- Supabase RLS 정책
- 테이블명/컬럼명
- 브라우저 console의 에러 메시지

### 4. Naver DataLab 순위가 이전과 다르게 보이는 경우

Naver DataLab은 상대 지수이므로 비교 대상 키워드 그룹이 바뀌면 순위도 바뀔 수 있습니다.  
예를 들어 성분 후보군을 5개에서 20개 이상으로 확장하면 기존 1위였던 성분이 다른 성분과 함께 재정렬될 수 있습니다.

---

## 빌드 체크리스트

작업 후 아래 명령어로 확인합니다.

```bash
npm run build
npm run dev
```

확인할 것:

- 1페이지 시장 요약 표시
- 기능 급상승 TOP 5 표시
- 성분 인기 TOP 5 표시
- 가격 violin chart tooltip 표시
- 수요-공급 매트릭스 hover tooltip 표시
- OpenAI 인사이트 요약 표시 또는 실패 안내 표시
