NAVER_URL = "https://www.naver.com"
SEARCH_KEYWORD = "올리브영"
WAIT_TIME = 15

DATA_DIR = "Data"
PLATFORM = "oliveyoung"

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
    "date",
    "platform",
    "sort_type",
    "rank",
    "product_name",
    "brand",
    "volume_ml",
    "regular_price",
    "discount",
    "sales_price",
    "rating",
    "review_count",
    "main_ingredients",
    "ingredients",
    "ing_source",
    "url",
]

REVIEW_COLUMNS = [
    "date",
    "platform",
    "sort_type",
    "rank",
    "main_ingredients",
    "product_name",
    "review_count",
    "review_rating",
    "skin_type",
    "review_text",
    "url",
]