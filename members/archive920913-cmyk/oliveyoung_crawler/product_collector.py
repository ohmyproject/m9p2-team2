from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .browser import create_driver, safe_quit_driver, wait_for_oliveyoung_access
from .category import select_category
from .common import make_output_path, now_iso, parse_sorts, parse_volume_package
from .config import ProductCrawlConfig
from .product_parser import (
    build_detail_dict,
    parse_product_cards,
    with_page,
    with_sort,
)


# ============================================================
# product_collector.py
# ------------------------------------------------------------
# 역할:
# - 실제 상품 수집 실행
# - 카테고리 진입
# - 목록 페이지 수집
# - 상품 상세 페이지 수집
# - 상품 CSV 저장
#
# 기존 collect_products.py에서 한 파일에 있던 내용을
# 브라우저 / 카테고리 / 파서 / 수집 실행으로 나눈 구조입니다.
# ============================================================


def get_detail(
    driver,
    url: str,
    *,
    detail_delay_seconds: float = 1.0,
    access_check_timeout_seconds: int = 180,
) -> dict[str, str]:
    """
    상품 상세 페이지에 들어가서 상세정보를 수집합니다.

    수집 대상:
    - 평점
    - 전체 리뷰수
    - 상세설명
    - 대표이미지
    - 상품정보 제공고시
    - 전성분
    - 용량
    """

    for attempt in range(3):
        try:
            driver.get(url)

            wait_for_oliveyoung_access(
                driver,
                timeout_seconds=access_check_timeout_seconds,
                context="상품 상세",
            )

            # 상세 페이지 body가 뜰 때까지 대기
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
            )

            time.sleep(detail_delay_seconds)

            # 상품정보 제공고시 아코디언 버튼이 있으면 펼칩니다.
            # 기존 코드에서 상품정보 제공고시 버튼을 눌러 전성분/용량을 확보하는 흐름을 유지합니다.
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "button.Accordion_accordion-btn__IYjKm")
                    )
                )

                buttons = driver.find_elements(
                    By.CSS_SELECTOR,
                    "button.Accordion_accordion-btn__IYjKm",
                )

                notice_button = None

                for button in buttons:
                    if "상품정보 제공고시" in button.text:
                        notice_button = button
                        break

                if notice_button:
                    driver.execute_script(
                        "arguments[0].scrollIntoView(true);",
                        notice_button,
                    )
                    time.sleep(0.5)

                    driver.execute_script("arguments[0].click();", notice_button)

                    time.sleep(detail_delay_seconds)

            except Exception as error:
                print(f"  [상세] 상품정보 제공고시 버튼 확인 실패: {str(error)[:80]}")

            soup = BeautifulSoup(driver.page_source, "html.parser")
            detail = build_detail_dict(soup)

            ingredient_text = detail.get("전성분", "")

            print(
                f"  [상세 성공] 평점:{detail.get('제품평점', '')} "
                f"리뷰:{detail.get('전체리뷰수', '')} "
                f"용량:{detail.get('용량', '')} "
                f"성분:{len(ingredient_text)}자"
            )

            return detail

        except Exception as error:
            print(f"  [상세 시도 {attempt + 1}/3 실패] {str(error)[:120]}")
            time.sleep(2)

    return {
        "제품평점": "",
        "전체리뷰수": "",
        "상세설명": "",
        "대표이미지": "",
        "용량": "",
        "제품주요사양": "",
        "사용기한": "",
        "사용방법": "",
        "제조판매업자": "",
        "제조국": "",
        "전성분": "3회 실패",
        "기능성화장품심사": "",
        "사용시주의사항": "",
        "품질보증기준": "",
        "소비자상담전화번호": "",
        "상세정보_JSON": "{}",
    }


def collect_sort_products(
    driver,
    base_url: str,
    *,
    sort_code: str,
    sort_name: str,
    suffix: str,
    config: ProductCrawlConfig,
) -> Path | None:
    """
    특정 정렬 기준 하나에 대해 상품 목록과 상세정보를 수집합니다.

    예:
    - 인기순 hot
    - 신상품순 new
    """

    print("=" * 60)
    print(f"▶ [{sort_name}] 상품 수집 시작")
    print("=" * 60)

    all_data: list[dict[str, str | int]] = []
    seen_product_keys: set[str] = set()

    # 1페이지 URL에 정렬 코드 적용
    sorted_base_url = with_sort(base_url.format(page=1), sort_code)

    for page in range(1, config.total_pages + 1):
        if config.max_products is not None and len(all_data) >= config.max_products:
            break

        print(f"[목록] {page}페이지 수집 중...")

        page_url = with_page(sorted_base_url, page)

        driver.get(page_url)

        time.sleep(config.page_delay_seconds)

        wait_for_oliveyoung_access(
            driver,
            timeout_seconds=config.access_check_timeout_seconds,
            context=f"{sort_name} {page}페이지",
        )

        # 첫 페이지에서는 정렬 버튼 클릭도 한 번 시도합니다.
        # URL prdSort만으로 충분한 경우도 있지만, 기존 흐름에 맞춰 버튼 클릭을 유지합니다.
        if page == 1:
            try:
                sort_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, f'//a[@data-prdsoting="{sort_code}"]')
                    )
                )
                driver.execute_script("arguments[0].click();", sort_button)
                time.sleep(config.page_delay_seconds)
            except Exception as error:
                print(f"  [정렬 버튼 클릭 생략] {str(error)[:80]}")

        rows = parse_product_cards(
            driver.page_source,
            page=page,
            sort_code=sort_code,
            sort_name=sort_name,
            suffix=suffix,
            major_category=config.major_category,
            middle_category=config.middle_category,
            start_rank=len(all_data) + 1,
            seen_product_keys=seen_product_keys,
        )

        print(f"  목록 상품 수: {len(rows)}")

        for row in rows:
            if config.max_products is not None and len(all_data) >= config.max_products:
                break

            all_data.append(row)

    if not all_data:
        print(f"[{sort_name}] 수집된 상품이 없습니다.")
        return None

    # 상품 목록 데이터프레임 생성
    df = pd.DataFrame(all_data)

    # 수집일시 추가
    df["수집일시"] = now_iso()

    # 상세정보 수집
    detail_rows: list[dict[str, str]] = []

    print("=" * 60)
    print(f"▶ [{sort_name}] 상품 상세정보 수집 시작")
    print("=" * 60)

    for index, row in df.iterrows():
        product_name = row.get("상품명", "")
        product_url = row.get("상품링크", "")

        print(f"[상세] {index + 1}/{len(df)} {product_name}")

        detail = get_detail(
            driver,
            product_url,
            detail_delay_seconds=config.detail_delay_seconds,
            access_check_timeout_seconds=config.access_check_timeout_seconds,
        )

        detail_rows.append(detail)

    detail_df = pd.DataFrame(detail_rows)

    for column in detail_df.columns:
        df[column] = detail_df[column]

    # 용량 컬럼 후처리
    if "용량" in df.columns:
        volume_rows = [
            parse_volume_package(row.get("용량", ""), row.get("상품명", ""))
            for _, row in df.iterrows()
        ]

        volume_df = pd.DataFrame(volume_rows)

        df["용량_원문"] = volume_df["package_volume_text"]
        df["단품용량"] = volume_df["unit_volume_text"]
        df["단품용량값"] = volume_df["unit_volume_value"]
        df["단품용량단위"] = volume_df["unit_volume_unit"]
        df["구성수량"] = volume_df["package_quantity"]
        df["총용량값"] = volume_df["total_volume_value"]
        df["총용량"] = volume_df["total_volume_text"]

    # 상세 대표이미지가 있으면 목록 이미지보다 우선 사용
    if "대표이미지" in df.columns:
        has_detail_image = df["대표이미지"].fillna("").astype(str).str.len() > 0
        df["이미지"] = df["대표이미지"].where(has_detail_image, df["이미지"])

    save_path = make_output_path(config.output_dir, "Data", suffix)

    df.to_csv(save_path, index=False, encoding="utf-8-sig")

    print(f"[상품 CSV 저장 완료] {save_path}")

    return save_path


def run(config: ProductCrawlConfig) -> list[Path]:
    """
    상품 수집 전체 실행 함수입니다.

    흐름:
    1. 브라우저 생성
    2. 카테고리 진입
    3. 정렬별 상품 수집
    4. CSV 저장
    5. 브라우저 종료
    """

    driver = create_driver(
        chrome_version=config.chrome_version,
        headless=config.headless,
    )

    saved_paths: list[Path] = []

    try:
        base_url = select_category(driver, config)

        for sort_code, sort_name, suffix in parse_sorts(config.sorts):
            path = collect_sort_products(
                driver,
                base_url,
                sort_code=sort_code,
                sort_name=sort_name,
                suffix=suffix,
                config=config,
            )

            if path:
                saved_paths.append(path)

            # 다음 정렬 수집 전 카테고리 첫 페이지로 복귀
            driver.get(base_url.format(page=1))
            time.sleep(config.page_delay_seconds)

            wait_for_oliveyoung_access(
                driver,
                timeout_seconds=config.access_check_timeout_seconds,
                context="카테고리 복귀",
            )

    finally:
        safe_quit_driver(driver)

    print("모든 정렬순서 상품 수집 완료!")

    return saved_paths