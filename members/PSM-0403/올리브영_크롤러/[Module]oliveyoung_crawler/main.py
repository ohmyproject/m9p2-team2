from oliveyoung_crawler.run_pipeline import run_pipeline


# ============================================================
# 설정: 여기만 바꾸면 됩니다
# ============================================================

# 수집 페이지 수
TOTAL_PAGES         = 1

# 최대 상품 수 (None이면 제한 없음)
MAX_PRODUCTS        = 24

# 올리브영 카테고리
MAJOR_CATEGORY      = "스킨케어"
MIDDLE_CATEGORY     = "에센스/세럼/앰플"

# 정렬 기준
# best  → 판매순   hot  → 인기순   new  → 신상품순
# low   → 낮은가격순   sale → 할인율순
# 여러 개 동시 수집: "best,hot"
SORTS               = "best,new"

# 상품 1개당 리뷰 수집 개수
REVIEWS_PER_PRODUCT = 10

# 크롬 버전 (None이면 자동 감지)
CHROME_VERSION      = 147

# True면 브라우저 창 없이 실행
HEADLESS            = False

# 리뷰 수집 건너뛰기
SKIP_REVIEWS        = False

# DB 적재 건너뛰기 (DB 없이 CSV만 받을 때 True)
SKIP_IMPORT         = True

# ============================================================


if __name__ == "__main__":
    run_pipeline(
        total_pages=TOTAL_PAGES,
        max_products=MAX_PRODUCTS,
        major_category=MAJOR_CATEGORY,
        middle_category=MIDDLE_CATEGORY,
        sorts=SORTS,
        reviews_per_product=REVIEWS_PER_PRODUCT,
        chrome_version=CHROME_VERSION,
        headless=HEADLESS,
        skip_reviews=SKIP_REVIEWS,
        skip_import=SKIP_IMPORT,
    )
