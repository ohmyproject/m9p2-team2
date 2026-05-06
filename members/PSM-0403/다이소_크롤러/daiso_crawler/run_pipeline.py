from __future__ import annotations

from pathlib import Path

from .config import (
    DEFAULT_CATEGORY_URL,
    DEFAULT_TESSERACT_CMD,
    DaisoCrawlConfig,
    DaisoReviewCrawlConfig,
)
from .product_collector import run as run_product_collector
from .review_collector import run as run_review_collector


# ============================================================
# run_pipeline.py
# ------------------------------------------------------------
# 역할:
# - main.py에서 호출하는 진입점 함수 제공
# - 상품 수집 → 리뷰 수집 순서 관리
#
# 실제 수집 로직은 각 collector에 있습니다.
# 이 파일은 config를 조립하고 순서를 정하는 역할만 합니다.
# ============================================================


def run_pipeline(
    *,
    # 공통 설정
    sort: str = "new",
    target_count: int = 24,
    category_url: str = DEFAULT_CATEGORY_URL,
    headless: bool = False,
    output_dir: Path | None = None,
    # 상품 수집 설정
    tesseract_cmd: str = DEFAULT_TESSERACT_CMD,
    openai_api_key: str = "",
    skip_products: bool = False,
    # 리뷰 수집 설정
    reviews_per_product: int = 10,
    skip_reviews: bool = False,
) -> None:
    """
    다이소몰 상품 정보 + 리뷰 수집 파이프라인입니다.

    Parameters
    ----------
    sort:
        정렬 기준 ('best', 'new', 'low', 'high', 'rate')
        여러 개 동시 수집: 'best,new'

    target_count:
        수집할 상품 수

    category_url:
        카테고리 기본 URL (정렬 파라미터 제외)
        기본값: 스킨케어 > 기초스킨

    headless:
        True면 브라우저 창 없이 실행

    output_dir:
        CSV 저장 폴더 (None이면 프로젝트 루트/Data)

    tesseract_cmd:
        Tesseract 실행 파일 경로 (상품 수집에서 OCR 사용 시 필요)

    skip_products:
        True면 상품 정보 수집 건너뜀

    reviews_per_product:
        상품 1개당 수집할 리뷰 수

    skip_reviews:
        True면 리뷰 수집 건너뜀
    """

    print("=" * 70)
    print("다이소몰 크롤러 시작")
    print(f"정렬: {sort} | 목표 상품: {target_count}개")
    print("=" * 70)

    product_config_kwargs: dict = {
        "sort": sort,
        "target_count": target_count,
        "category_url": category_url,
        "headless": headless,
        "tesseract_cmd": tesseract_cmd,
        "openai_api_key": openai_api_key,
    }

    review_config_kwargs: dict = {
        "sort": sort,
        "target_product_count": target_count,
        "reviews_per_product": reviews_per_product,
        "category_url": category_url,
        "headless": headless,
    }

    if output_dir is not None:
        product_config_kwargs["output_dir"] = output_dir
        review_config_kwargs["output_dir"] = output_dir

    # 1. 상품 수집
    if skip_products:
        print("\n[건너뜀] skip_products=True: 상품 정보 수집을 건너뜁니다.")
    else:
        print("\n" + "=" * 70)
        print("1단계: 상품 정보 수집")
        print("=" * 70)

        product_config = DaisoCrawlConfig(**product_config_kwargs)
        product_paths = run_product_collector(product_config)

        print("\n저장된 상품 CSV:")
        for path in product_paths:
            print(f"  - {path}")

    # 2. 리뷰 수집
    if skip_reviews:
        print("\n[건너뜀] skip_reviews=True: 리뷰 수집을 건너뜁니다.")
    else:
        print("\n" + "=" * 70)
        print("2단계: 리뷰 수집")
        print("=" * 70)

        review_config = DaisoReviewCrawlConfig(**review_config_kwargs)
        review_paths = run_review_collector(review_config)

        print("\n저장된 리뷰 CSV:")
        for path in review_paths:
            print(f"  - {path}")

    print("\n전체 파이프라인 완료")
