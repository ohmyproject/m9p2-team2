## 설치 및 실행 명령어

이 프로젝트는 두 가지 실행 흐름으로 나뉩니다.

```txt
1. 데이터 생성 / 적재 실행 파일
2. Render API 서버 실행
```

---

# 1. 패키지 설치

프로젝트 최초 실행 시 한 번 설치합니다.

```bash
pip install -r requirements.txt
```

`requirements.txt` 내용은 아래와 같습니다.

```txt
pandas
selenium
beautifulsoup4
openai
python-dotenv
sqlalchemy
psycopg2-binary
fastapi
uvicorn
```

---
## 빠른 실행 요약

데이터 파이프라인 실행:

```bash
python main.py
python retry_main.py
python ingredient_main.py
python preprocess_main.py
python supabase_main.py

## Render 배포 설정:
Build Command: pip install -r requirements.txt
Start Command: uvicorn api.supabase_api:app --host 0.0.0.0 --port $PORT

---

# 2. 데이터 파이프라인 실행 순서

아래 명령어는 데이터를 수집하고 Supabase에 넣기 위한 실행 순서입니다.

## 2-1. 1차 크롤링 실행

```bash
python main.py
```

역할:

```txt
올리브영 접속
카테고리 입력
정렬 입력
제품 개수 입력
리뷰 개수 입력
상품 CSV 저장
리뷰 CSV 저장
```

---

## 2-2. 누락 데이터 검증 및 재수집 실행

```bash
python retry_main.py
```

역할:

```txt
Data 폴더의 CSV 검증
누락된 상품 정보 재수집
부족한 리뷰 재수집
_retry.csv 생성
```

---

## 2-3. OpenAI 주요성분 정제 실행

```bash
python ingredient_main.py
```

역할:

```txt
main_ingredients 빈 값 확인
ingredients가 있는 상품만 OpenAI로 주요성분 추출
같은 전성분은 중복 호출하지 않음
_ingredients.csv 생성
```

---

## 2-4. 최종 전처리 실행

```bash
python preprocess_main.py
```

역할:

```txt
가격 정리
할인율 재계산
용량 정리
성분 정리
중복 제거
_cleaned.csv 생성
```

---

## 2-5. Supabase 적재 실행

```bash
python supabase_main.py
```

역할:

```txt
_cleaned.csv 파일을 Supabase에 적재
products 테이블 생성
reviews 테이블 생성
상품 중복 시 업데이트
리뷰 중복 시 무시
```

---

# 3. 전체 데이터 파이프라인 명령어 요약

아래 순서대로 실행합니다.

```bash
python main.py
python retry_main.py
python ingredient_main.py
python preprocess_main.py
python supabase_main.py
```

---

# 4. Render API 서버 실행 명령

Render에서는 아래 명령어로 FastAPI 서버를 실행합니다.

## Render Build Command

```bash
pip install -r requirements.txt
```

## Render Start Command

```bash
uvicorn api.supabase_api:app --host 0.0.0.0 --port $PORT
```

Render 설정 화면에는 이렇게 입력합니다.

```txt
Build Command:
pip install -r requirements.txt

Start Command:
uvicorn api.supabase_api:app --host 0.0.0.0 --port $PORT
```

---

# 5. Render 환경변수

Render Dashboard에서 아래 환경변수를 등록합니다.

```txt
SUPABASE_DB_URL=본인_SUPABASE_DB_URL
OPENAI_API_KEY=본인_OPENAI_API_KEY
```

필수 환경변수:

```txt
SUPABASE_DB_URL
```

선택 환경변수:

```txt
OPENAI_API_KEY
```

단, OpenAI 주요성분 정제를 서버에서 직접 실행하지 않고 데이터 파이프라인에서만 실행한다면 Render API 서버에는 `OPENAI_API_KEY`가 필수는 아닙니다.

---

# 6. Render 배포 후 접속 주소

Render 배포가 완료되면 아래 주소로 접속합니다.

```txt
https://본인-service-name.onrender.com
```

API 문서 주소:

```txt
https://본인-service-name.onrender.com/docs
```

---

# 7. 프론트엔드에서 사용할 API 주소

프론트엔드 팀원은 아래 주소들을 사용합니다.

## 상품 목록

```txt
GET https://본인-service-name.onrender.com/products
```

## 상품 검색

```txt
GET https://본인-service-name.onrender.com/products?keyword=토리든
```

## 성분 검색

```txt
GET https://본인-service-name.onrender.com/products?ingredient=나이아신아마이드
```

## 정렬별 조회

```txt
GET https://본인-service-name.onrender.com/products?sort_type=판매순
```

## 상품 상세

```txt
GET https://본인-service-name.onrender.com/products/1
```

## 리뷰 목록

```txt
GET https://본인-service-name.onrender.com/reviews
```

## 리뷰 검색

```txt
GET https://본인-service-name.onrender.com/reviews?keyword=촉촉
```

## 전체 요약

```txt
GET https://본인-service-name.onrender.com/summary
```

## 통합 검색

```txt
GET https://본인-service-name.onrender.com/search?q=병풀
```

---

# 8. 실행 파일 정리

| 파일명 | 실행 명령어 | 역할 |
|---|---|---|
| `main.py` | `python main.py` | 1차 크롤링 |
| `retry_main.py` | `python retry_main.py` | 누락 상품/리뷰 재수집 |
| `ingredient_main.py` | `python ingredient_main.py` | OpenAI 주요성분 정제 |
| `preprocess_main.py` | `python preprocess_main.py` | 최종 CSV 전처리 |
| `supabase_main.py` | `python supabase_main.py` | Supabase 적재 |
| `api_main.py` | 사용 안 함 | Render에서는 직접 실행하지 않음 |
| `api/supabase_api.py` | `uvicorn api.supabase_api:app --host 0.0.0.0 --port $PORT` | Render API 서버 |

---

# 9. 최종 실행 흐름

```txt
데이터 생성 담당자:
python main.py
↓
python retry_main.py
↓
python ingredient_main.py
↓
python preprocess_main.py
↓
python supabase_main.py

Render:
uvicorn api.supabase_api:app --host 0.0.0.0 --port $PORT

프론트엔드:
Render API 주소 호출
```