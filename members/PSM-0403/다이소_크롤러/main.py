import os

from dotenv import load_dotenv

from daiso_crawler.run_pipeline import run_pipeline

load_dotenv()

# ============================================================
# 설정: 여기만 바꾸면 됩니다
# ============================================================

# 정렬 기준
# best  → 판매량순   new  → 신상품순
# low   → 낮은가격순  high → 높은가격순  rate → 평점순
# 여러 개 동시 수집: "best,new"
SORT                = "best,new"

# 수집 목표 상품 수
TARGET_COUNT        = 3

# True면 브라우저 창 없이 실행
HEADLESS            = False

# Tesseract 경로 (전성분 OCR에 사용)
TESSERACT_CMD       = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# OpenAI API 키 (.env 파일에서 자동 로드 (GPT Vision 핵심 성분 추출용)
OPENAI_API_KEY      = os.getenv("OPENAI_API_KEY", "")

# 상품 1개당 수집할 리뷰 수
REVIEWS_PER_PRODUCT = 10

# 상품 정보 수집 건너뛰기
SKIP_PRODUCTS       = False

# 리뷰 수집 건너뛰기
SKIP_REVIEWS        = False

# ============================================================


if __name__ == "__main__":
    run_pipeline(
        sort=SORT,
        target_count=TARGET_COUNT,
        headless=HEADLESS,
        tesseract_cmd=TESSERACT_CMD,
        openai_api_key=OPENAI_API_KEY,
        reviews_per_product=REVIEWS_PER_PRODUCT,
        skip_products=SKIP_PRODUCTS,
        skip_reviews=SKIP_REVIEWS,
    )
