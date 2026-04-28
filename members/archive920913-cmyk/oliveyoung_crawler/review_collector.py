from __future__ import annotations

import csv
import re
import time
from pathlib import Path
from typing import Any

import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from .browser import create_driver, safe_quit_driver, wait_for_oliveyoung_access
from .common import clean_text, make_output_path
from .config import ReviewCrawlConfig


# ============================================================
# review_collector.py
# ------------------------------------------------------------
# 역할:
# - 상품 CSV를 읽음
# - 각 상품 상세 페이지로 이동
# - 리뷰 탭 클릭
# - 리뷰 데이터 추출
# - 리뷰 CSV 저장
#
# 기존 collect_reviews.py의 역할을 유지하되,
# 교육용으로 함수 단위와 주석을 더 명확하게 나눈 버전입니다.
# ============================================================


CLICK_REVIEW_TAB_JS = """
const candidates = [
    ...document.querySelectorAll('button.GoodsDetailTabs_tab-item__tgAnU'),
    ...document.querySelectorAll('button[role="tab"]')
];
const tab = candidates.find(button => (button.innerText || '').includes('리뷰'));
if (!tab) return false;
tab.scrollIntoView({block: 'center'});
tab.click();
return true;
"""

REVIEW_HOST_READY_JS = """
const host = document.querySelector('oy-review-review-in-product');
if (!host) return false;
const list = host.shadowRoot?.querySelector('oy-review-review-list');
return !!list;
"""

REVIEW_ITEM_COUNT_JS = """
const s1 = document.querySelector('oy-review-review-in-product')?.shadowRoot;
const s2 = s1?.querySelector('oy-review-review-list')?.shadowRoot;
return s2 ? s2.querySelectorAll('oy-review-review-item').length : 0;
"""

SCROLL_REVIEW_AREA_JS = """
const host = document.querySelector('oy-review-review-in-product');
if (host) {
    host.scrollIntoView({block: 'start'});
}
window.scrollBy(0, arguments[0] || 1200);
return window.scrollY;
"""


EXTRACT_REVIEWS_JS = """
const s1 = document.querySelector('oy-review-review-in-product')?.shadowRoot;
const s2 = s1?.querySelector('oy-review-review-list')?.shadowRoot;
if (!s2) return [];
const items = s2.querySelectorAll('oy-review-review-item');
const results = [];
items.forEach(item => {
    try {
        const s3 = item.shadowRoot;
        if (!s3) return;
        const starIcons = s3.querySelectorAll('oy-review-star-icon');
        let stars = 0;
        starIcons.forEach(icon => {
            const sh = icon.shadowRoot;
            if (sh) {
                const path = sh.querySelector('path');
                if (path && path.getAttribute('fill') === '#FF5753') stars++;
            }
        });
        const date = s3.querySelector('span.date')?.innerText?.trim() || '';
        const tags = Array.from(s3.querySelectorAll('.tag') || [])
            .map(t => t.innerText.trim())
            .filter(Boolean)
            .join('/');
        const userEl = s3.querySelector('oy-review-review-user');
        const su = userEl?.shadowRoot;
        const nickname = su?.querySelector('.name')?.innerText?.trim() || '';
        const skinTypes = Array.from(su?.querySelectorAll('.skin-type') || [])
            .map(s => s.innerText.trim()).join('/');
        const contEl = s3.querySelector('oy-review-review-content');
        const sc = contEl?.shadowRoot;
        const content = sc?.querySelector('p')?.innerText?.trim() || '';
        if (!nickname) return;
        results.push({nickname, skinTypes, stars, date, content, tags});
    } catch(e) {}
});
return results;
"""


def read_product_rows(path: Path) -> list[dict[str, str]]:
    """
    상품 CSV를 읽어서 딕셔너리 리스트로 반환합니다.
    """
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def save_review_rows(rows: list[dict[str, str]], path: Path) -> None:
    """
    리뷰 행 목록을 CSV로 저장합니다.

    행마다 컬럼이 조금 다를 수 있으므로,
    전체 row를 돌면서 fieldnames를 동적으로 만듭니다.
    """
    fieldnames: list[str] = []

    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def suffix_from_product_csv(path: Path, fallback: str = "hot") -> str:
    """
    상품 CSV 파일명에서 정렬 suffix를 추출합니다.

    예:
    2026-04-28_Data(oliveyoung)_hot.csv -> hot
    """
    stem = path.stem

    if "_" not in stem:
        return fallback

    return stem.split("_")[-1] or fallback


def normalize_review_row(
    product: dict[str, str],
    raw_review: dict[str, Any],
) -> dict[str, str]:
    """
    JS로 추출한 리뷰 데이터를 기존 리뷰 CSV 컬럼 구조에 맞게 변환합니다.
    """

    tags = clean_text(raw_review.get("tags"))
    content = clean_text(raw_review.get("content"))

    long_term = "Y" if ("한달" in tags or "한달" in content or "1개월" in content) else ""
    repurchase = "Y" if ("재구매" in tags or "재구매" in content) else ""

    row = dict(product)

    row.update(
        {
            "리뷰_닉네임": clean_text(raw_review.get("nickname")),
            "리뷰_피부타입": clean_text(raw_review.get("skinTypes")),   # JS: skinTypes
            "리뷰_별점": raw_review.get("stars", ""),                   # JS: stars (int)
            "리뷰_작성일": clean_text(raw_review.get("date")),
            "리뷰_태그": tags,
            "리뷰_장기사용여부": long_term,
            "리뷰_재구매여부": repurchase,
            "리뷰_내용": content,
            "리뷰_수집상태": "success",
            "리뷰_수집오류": "",
        }
    )

    return row


def failed_review_row(product: dict[str, str], error_code: str) -> dict[str, str]:
    """
    리뷰 수집 실패 시에도 상품 행을 버리지 않고 failed 상태로 저장합니다.

    기존 CSV에서도 리뷰 0건 또는 수집 실패 상품을 failed로 기록하는 구조가 있었습니다.
    """
    row = dict(product)

    row.update(
        {
            "리뷰_닉네임": "",
            "리뷰_피부타입": "",
            "리뷰_별점": "",
            "리뷰_작성일": "",
            "리뷰_태그": "",
            "리뷰_장기사용여부": "",
            "리뷰_재구매여부": "",
            "리뷰_내용": "리뷰 0건으로 크롤링 불가",
            "리뷰_수집상태": "failed",
            "리뷰_수집오류": error_code,
        }
    )

    return row


def collect_reviews_for_product(
    driver,
    product: dict[str, str],
    *,
    limit: int,
    access_check_timeout_seconds: int,
) -> list[dict[str, str]]:
    """
    상품 1개에 대해 리뷰를 수집합니다.
    """

    product_name = clean_text(product.get("상품명"))
    product_url = clean_text(product.get("상품링크"))

    if not product_url:
        return [failed_review_row(product, "missing_product_url")]

    print(f"[리뷰] {product_name}")

    try:
        driver.get(product_url)

        wait_for_oliveyoung_access(
            driver,
            timeout_seconds=access_check_timeout_seconds,
            context="리뷰 상품 상세",
        )

        WebDriverWait(driver, 15).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        time.sleep(2)

        clicked = driver.execute_script(CLICK_REVIEW_TAB_JS)

        if not clicked:
            print("  [리뷰 실패] 리뷰 탭 클릭 실패")
            return [failed_review_row(product, "review_tab_not_clicked")]

        time.sleep(2)

        # 리뷰 Web Component가 실제로 마운트될 때까지 대기 (최대 6회 폴링)
        for _ in range(6):
            if (
                bool(driver.execute_script(REVIEW_HOST_READY_JS))
                or int(driver.execute_script(REVIEW_ITEM_COUNT_JS) or 0) > 0
            ):
                break
            driver.execute_script(SCROLL_REVIEW_AREA_JS, 1200)
            time.sleep(1)

        raw_reviews = driver.execute_script(EXTRACT_REVIEWS_JS) or []

        # 첫 추출 실패 시 추가 스크롤 후 재시도 (lazy loading 대응)
        if not raw_reviews:
            for _ in range(5):
                driver.execute_script(SCROLL_REVIEW_AREA_JS, 1400)
                time.sleep(1.5)
                raw_reviews = driver.execute_script(EXTRACT_REVIEWS_JS) or []
                if raw_reviews:
                    break

        if not raw_reviews:
            print("  [리뷰 실패] 리뷰 컴포넌트 또는 리뷰 아이템 미확인")
            return [failed_review_row(product, "review_component_or_items_not_loaded")]

        result: list[dict[str, str]] = []

        for raw_review in raw_reviews[:limit]:
            result.append(normalize_review_row(product, raw_review))

        print(f"  [리뷰 성공] {len(result)}건")

        return result

    except Exception as error:
        print(f"  [리뷰 예외] {str(error)[:120]}")
        return [failed_review_row(product, f"exception:{str(error)[:80]}")]


def run(config: ReviewCrawlConfig) -> Path | None:
    """
    리뷰 수집 전체 실행 함수입니다.

    흐름:
    1. 상품 CSV 읽기
    2. 브라우저 생성
    3. 상품별 리뷰 수집
    4. 리뷰 CSV 저장
    5. 브라우저 종료
    """

    product_rows = read_product_rows(config.product_csv)

    if not product_rows:
        print("[리뷰] 상품 CSV에 데이터가 없습니다.")
        return None

    suffix = suffix_from_product_csv(config.product_csv, fallback=config.sorts)

    save_path = make_output_path(config.output_dir, "Review", suffix)

    all_review_rows: list[dict[str, str]] = []

    driver = create_driver(
        chrome_version=config.chrome_version,
        headless=config.headless,
    )

    try:
        for index, product in enumerate(product_rows, start=1):
            print(f"[리뷰 진행] {index}/{len(product_rows)}")

            rows = collect_reviews_for_product(
                driver,
                product,
                limit=config.reviews_per_product,
                access_check_timeout_seconds=config.access_check_timeout_seconds,
            )

            all_review_rows.extend(rows)

    finally:
        safe_quit_driver(driver)

    save_review_rows(all_review_rows, save_path)

    print(f"[리뷰 CSV 저장 완료] {save_path}")

    return save_path