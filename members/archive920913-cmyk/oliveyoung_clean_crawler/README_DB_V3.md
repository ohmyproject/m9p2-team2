# OliveYoung DB v3 - cleaned CSV 우선 반영 버전

## 핵심 변경점

이번 수정본에는 같은 날짜/정렬 기준으로 원본 CSV와 `_cleaned.csv`가 같이 있습니다.

예:

```text
oliveyoung_...(info)_260501.csv
oliveyoung_...(info)_260501_cleaned.csv
```

DB 적재는 반드시 `_cleaned.csv`만 사용하는 것을 권장합니다.
그래야 `product_name_clean`, `main_ingredients_kor`가 반영되고 원본/cleaned 중복 적재를 막을 수 있습니다.

## 테이블 구조

```text
products
product_snapshots
product_rankings
product_main_ingredients
product_full_ingredients
product_reviews
```

- `products`: 상품 기본정보. goodsNo 기준으로 상품당 1행.
- `product_snapshots`: 날짜별 가격/할인율/평점/리뷰수.
- `product_rankings`: 날짜별/정렬별 랭킹.
- `product_main_ingredients`: 주성분. `main_ingredients_kor` 우선 사용.
- `product_full_ingredients`: 전성분.
- `product_reviews`: 나중에 리뷰 CSV 적재용.

## 실행 순서

```powershell
pip install pandas fastapi uvicorn
```

처음 DB를 새로 만들 때:

```powershell
python import_products_to_db.py --data-dir Data --db-path db/oliveyoung.sqlite --reset
```

다음부터 누적 적재할 때:

```powershell
python import_products_to_db.py --data-dir Data --db-path db/oliveyoung.sqlite
```

DB 확인:

```powershell
python check_db.py --db-path db/oliveyoung.sqlite
```

API 실행:

```powershell
uvicorn api:app --reload --host 127.0.0.1 --port 8000
```

API 문서:

```text
http://127.0.0.1:8000/docs
```

## 중복 방지 방식

- `products`: `goods_no` 기준으로 이미 있으면 업데이트.
- `product_snapshots`: `goods_no + collected_date + platform` 기준으로 이미 있으면 업데이트.
- `product_rankings`: `goods_no + collected_date + platform + sort_type` 기준으로 이미 있으면 업데이트.
- `product_main_ingredients`: 같은 상품의 같은 주성분은 중복 저장하지 않음.
- `product_full_ingredients`: 같은 상품의 같은 순서/성분은 중복 저장하지 않음.

## 이번 데이터 기준 예상 결과

수정본 기준으로 `_cleaned.csv` 10개만 사용합니다.

```text
상품 CSV: 10개
처리 행: 240행
고유 상품: 60개
랭킹 기록: 240행
```

`snapshots`는 같은 날짜에 같은 상품이 판매순/신상품순 양쪽에 있으면 한 번만 들어가므로 240보다 작을 수 있습니다.


# 실행 코드 
python import_products_to_db.py --data-dir Data --db-path db/oliveyoung.sqlite

# DB확인
python check_db.py --db-path db/oliveyoung.sqlite

# API 실행
uvicorn api:app --reload --host 127.0.0.1 --port 8000

# 브라우저 확인
http://127.0.0.1:8000/docs