# 설정값, 정렬명, CSV 컬럼 순서를 관리합니다.

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "Data")

os.makedirs(DATA_DIR, exist_ok=True)

NAVER_URL = "https://www.naver.com"
SEARCH_KEYWORD = "올리브영"

WAIT_TIME = 15
BOT_CHECK_SLEEP = 5

SORT_MAP = {
    "인기순": "인기순",
    "신상품순": "신상품순",
    "판매순": "판매순",
    "판매량순": "판매순",
    "낮은가격순": "낮은 가격순",
    "낮은 가격순": "낮은 가격순",
    "할인율순": "할인율순",
}

PRODUCT_COLUMNS = [
    "date", "platform", "sort_type", "rank",
    "product_name", "brand", "volume_ml",
    "regular_price", "discount", "sales_price",
    "rating", "review_count",
    "main_ingredients", "ingredients", "ing_source", "url",
]

REVIEW_COLUMNS = [
    "date", "platform", "sort_type", "rank",
    "main_ingredients", "product_name", "review_count",
    "review_rating", "skin_type", "review_text", "url",
]