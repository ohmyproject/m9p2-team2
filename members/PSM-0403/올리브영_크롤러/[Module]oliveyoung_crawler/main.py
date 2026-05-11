from pathlib import Path

# ============================================================
# 실행 모드 선택
# ============================================================
#
# "crawl"         → 올리브영 상품/리뷰 수집
# "retry_review"  → 리뷰 수집 실패/부족 상품 재수집
# "retry_volume"  → volume_ml 누락 상품 재수집
# "retry_info"    → main_ingredients 누락 상품 재수집
#
MODE = "crawl"

# ============================================================
# 공통 설정
# ============================================================

CHROME_VERSION = 147
HEADLESS       = False

# ============================================================
# [crawl] 상품/리뷰 수집 설정
# ============================================================

# 수집 페이지 수
TOTAL_PAGES         = 1

# 최대 상품 수 (None이면 제한 없음)
MAX_PRODUCTS        = 5

# 올리브영 카테고리
MAJOR_CATEGORY      = "스킨케어"
MIDDLE_CATEGORY     = "에센스/세럼/앰플"

# 정렬 기준
# best  → 판매순   hot  → 인기순   new  → 신상품순
# low   → 낮은가격순   sale → 할인율순
# 여러 개 동시 수집: "best,hot"
SORTS               = "best,new"

# 상품 1개당 리뷰 수집 개수
REVIEWS_PER_PRODUCT = 3

# 리뷰 수집 건너뛰기
SKIP_REVIEWS        = False

# DB 적재 건너뛰기 (DB 없이 CSV만 받을 때 True)
SKIP_IMPORT         = True

# ============================================================
# [retry_review] 리뷰 재수집 설정
# ============================================================

# 재수집할 리뷰 CSV 경로
# None          → Data/ 폴더에서 가장 최근 review CSV 자동 선택
# 파일 1개      → Path("Data/oliveyoung_판매순(review)_260503.csv")
# 파일 여러 개  → [Path("Data/...csv"), Path("Data/...csv")]
RETRY_REVIEW_CSV    = None

# 상품당 목표 리뷰 수
RETRY_REVIEW_TARGET = 10

# ============================================================
# [retry_volume] 용량 재수집 설정
# ============================================================

# 재수집할 info CSV 경로 (None이면 자동 선택)
RETRY_VOLUME_CSV    = None

# ============================================================
# [retry_info] 주성분 재수집 설정
# ============================================================

# 재수집할 CSV 경로 (info / review 모두 가능, None이면 자동 선택)
RETRY_INFO_CSV      = None

# True  → 주성분 유무 상관없이 모든 상품 재크롤링
# False → main_ingredients가 비어 있는 상품만 재크롤링
RETRY_INFO_RECRAWL_ALL = True

# ============================================================


if __name__ == "__main__":
    if MODE == "crawl":
        from oliveyoung_crawler.run_pipeline import run_pipeline

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

    elif MODE == "retry_review":
        from oliveyoung_crawler.review_retry import run_retry

        run_retry(
            review_csv=RETRY_REVIEW_CSV,
            target=RETRY_REVIEW_TARGET,
            chrome_version=CHROME_VERSION,
            headless=HEADLESS,
        )

    elif MODE == "retry_volume":
        from oliveyoung_crawler.volume_retry import run_retry

        run_retry(
            target_csv=RETRY_VOLUME_CSV,
            chrome_version=CHROME_VERSION,
            headless=HEADLESS,
        )

    elif MODE == "retry_info":
        from oliveyoung_crawler.info_retry import run_retry

        run_retry(
            target_csv=RETRY_INFO_CSV,
            recrawl_all=RETRY_INFO_RECRAWL_ALL,
            chrome_version=CHROME_VERSION,
            headless=HEADLESS,
        )

    else:
        print(f"[오류] 알 수 없는 MODE: {MODE!r}")
        print("사용 가능한 MODE: crawl / retry_review / retry_volume / retry_info")
