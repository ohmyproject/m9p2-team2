from __future__ import annotations

import re
import time
from pathlib import Path

import pandas as pd
from playwright.sync_api import Locator, Page

from .browser import create_browser, create_page, safe_close, start_playwright
from .category import collect_product_links_from_config
from .common import clean_text, make_output_path
from .config import SORT_MAP, DaisoReviewCrawlConfig
from .product_parser import parse_main_ingredients


# ============================================================
# review_collector.py
# ------------------------------------------------------------
# 역할:
# - 카테고리 페이지에서 상품 링크 수집
# - 각 상품 상세 페이지에서 리뷰 탭 클릭
# - 리뷰 카드에서 평점 / 피부타입 / 리뷰 텍스트 추출
# - 리뷰 CSV 저장
# ============================================================


def _checkpoint_path(save_path: Path) -> Path:
    return save_path.parent / f"_ckpt_{save_path.name}"


REVIEW_OUTPUT_COLUMNS = [
    "date",
    "platform",
    "sort_type",
    "main_ingredients",
    "product_name",
    "review_count",
    "review_rating",
    "skin_type",
    "review_text",
    "url",
]


# ============================================================
# 텍스트 추출 헬퍼
# ============================================================

def _get_text_safe(locator: Locator) -> str:
    """로케이터에서 텍스트를 안전하게 추출합니다."""
    try:
        if locator.count() == 0:
            return ""
        return clean_text(locator.first.inner_text(timeout=5000))
    except Exception:
        return ""


# ============================================================
# 상품명 추출
# ============================================================

def extract_product_name(page: Page) -> str:
    """
    h1.product-title에서 상품명을 추출합니다.

    첫 어절(브랜드)을 제거하고 나머지를 반환합니다.
    예: '본셉 비타씨 에센스 100ml' → '비타씨 에센스 100ml'
    """
    full_name = _get_text_safe(page.locator("h1.product-title"))

    if not full_name:
        return ""

    parts = full_name.split()

    if len(parts) >= 2:
        return " ".join(parts[1:])

    return full_name


# ============================================================
# 리뷰 탭 클릭
# ============================================================

def click_review_tab(page: Page) -> bool:
    """
    상품 상세 페이지에서 리뷰 탭을 클릭합니다.

    Returns
    -------
    True: 클릭 성공, False: 클릭 실패
    """
    try:
        button = page.locator("button:has-text('리뷰')").first
        button.wait_for(state="visible", timeout=15000)
        button.click()
        page.wait_for_timeout(3000)
        return True

    except Exception as e:
        print(f"  [리뷰 탭 클릭 실패] {str(e)[:80]}")
        return False


# ============================================================
# 리뷰 수 추출
# ============================================================

def extract_review_count(page: Page) -> str:
    """
    총 리뷰 수를 추출합니다.

    다이소몰은 리뷰 탭 클릭 직후 타이밍 이슈가 있어
    여러 선택자를 순서대로 시도합니다.
    """
    page.wait_for_timeout(2000)

    selectors = [
        "span.star-detail--cnt",
        "button:has-text('리뷰') em.count",
        "em.count",
    ]

    for selector in selectors:
        try:
            locator = page.locator(selector).first

            if locator.count() == 0:
                continue

            locator.wait_for(state="visible", timeout=10000)
            text = clean_text(locator.inner_text(timeout=5000))

            if text:
                return text.replace("(", "").replace(")", "").replace(",", "").strip()

        except Exception:
            continue

    return ""


# ============================================================
# 리뷰 카드 로딩
# ============================================================

def load_review_cards(page: Page, target_count: int = 10):
    """
    리뷰 카드가 충분히 로드될 때까지 스크롤합니다.

    최대 12번 스크롤을 시도합니다.
    """
    for _ in range(12):
        cards = page.locator("li.review-detail")

        try:
            if cards.count() >= target_count:
                return cards
        except Exception:
            pass

        page.mouse.wheel(0, 2500)
        page.wait_for_timeout(1000)

    return page.locator("li.review-detail")


# ============================================================
# 리뷰 카드 필드 추출
# ============================================================

def extract_review_rating(card: Locator) -> str:
    """
    리뷰 카드에서 별점을 추출합니다.

    예: '별점 5점' → '5'
    """
    try:
        text = _get_text_safe(card.locator("span.hiddenText"))
        match = re.search(r"별점\s*([0-9.]+)\s*점", text)

        if match:
            return match.group(1)

        return text.replace("별점", "").replace("점", "").strip()

    except Exception:
        return ""


def extract_skin_type(card: Locator) -> str:
    """
    리뷰 카드의 ul.info-list.review에서 피부타입 항목만 추출합니다.

    피부타입 항목이 없는 리뷰는 빈 문자열을 반환합니다.
    """
    try:
        info_items = card.locator("ul.info-list.review li")
        count = info_items.count()

        for i in range(count):
            li = info_items.nth(i)
            item_name = _get_text_safe(li.locator("div.item"))
            item_value = _get_text_safe(li.locator("div.val"))

            if item_name == "피부타입":
                return item_value

        return ""

    except Exception:
        return ""


def extract_review_text(card: Locator) -> str:
    """
    리뷰 카드에서 본문 텍스트를 추출합니다.

    '재구매', '체험단', '한달사용' 배지 텍스트는 제거합니다.
    """
    try:
        cont = card.locator("div.review-desc div.cont").first

        if cont.count() == 0:
            return ""

        text = clean_text(cont.inner_text(timeout=5000))
        text = re.sub(r"^(재구매|체험단|한달사용)\s+", "", text)

        return text

    except Exception:
        return ""


# ============================================================
# 상품 1개 리뷰 수집
# ============================================================

def collect_reviews_for_product(
    page: Page,
    product: dict,
    *,
    reviews_per_product: int,
    detail_delay_ms: int,
    today: str,
    sort_name: str,
) -> list[dict[str, str]]:
    """
    상품 1개에 대해 리뷰를 수집합니다.

    Parameters
    ----------
    product:
        {'rank': ..., 'pdNo': ..., 'url': ...}

    Returns
    -------
    리뷰 행 목록 (REVIEW_OUTPUT_COLUMNS 스키마)
    """
    url = str(product["url"])

    page.goto(url, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(detail_delay_ms)

    product_name = extract_product_name(page)
    main_ingredients = parse_main_ingredients(page)

    clicked = click_review_tab(page)

    if not clicked:
        return []

    # 리뷰 카드 렌더링 대기
    try:
        page.wait_for_selector("li.review-detail", timeout=15000)
    except Exception:
        pass

    review_count = extract_review_count(page)

    cards = load_review_cards(page, reviews_per_product)
    card_count = min(cards.count(), reviews_per_product)

    print(f"  제품명: {product_name}")
    print(f"  총 리뷰수: {review_count} / 수집: {card_count}개")

    rows = []

    for i in range(card_count):
        card = cards.nth(i)

        rows.append({
            "date": today,
            "platform": "daiso",
            "sort_type": sort_name,
            "main_ingredients": main_ingredients,
            "product_name": product_name,
            "review_count": review_count,
            "review_rating": extract_review_rating(card),
            "skin_type": extract_skin_type(card),
            "review_text": extract_review_text(card),
            "url": url,
        })

    return rows


# ============================================================
# 정렬 1개 전체 리뷰 수집
# ============================================================

def collect_sort_reviews(
    page: Page,
    *,
    sort_key: str,
    config: DaisoReviewCrawlConfig,
) -> Path | None:
    """
    특정 정렬 기준 하나에 대해 전체 상품 리뷰를 수집합니다.
    """
    from datetime import date as _date

    _, _, sort_name = SORT_MAP[sort_key]

    print("=" * 60)
    print(f"▶ [{sort_name}] 리뷰 수집 시작")
    print("=" * 60)

    links = collect_product_links_from_config(page, config, sort_key=sort_key)

    if not links:
        print(f"[{sort_name}] 수집된 상품이 없습니다.")
        return None

    today = _date.today().strftime("%Y-%m-%d")
    save_path = make_output_path(config.output_dir, "review", sort_key)
    ckpt_path = _checkpoint_path(save_path)

    all_rows: list[dict[str, str]] = []
    done_urls: set[str] = set()

    if ckpt_path.exists():
        print(f"  [체크포인트 발견] {ckpt_path.name} — 이어서 수집합니다.")
        df_ckpt = pd.read_csv(ckpt_path, encoding="utf-8-sig")
        all_rows = df_ckpt.to_dict("records")
        done_urls = {str(r["url"]) for r in all_rows}

    for idx, product in enumerate(links, start=1):
        print(f"\n[{idx}/{len(links)}] pdNo={product['pdNo']}")

        url = str(product["url"])

        if url in done_urls:
            print(f"  건너뜀 (이미 수집): pdNo={product['pdNo']}")
            continue

        try:
            rows = collect_reviews_for_product(
                page,
                product,
                reviews_per_product=config.reviews_per_product,
                detail_delay_ms=config.detail_delay_ms,
                today=today,
                sort_name=sort_name,
            )

            all_rows.extend(rows)
            print(f"  수집 리뷰: {len(rows)}개")

        except Exception as e:
            print(f"  [리뷰 수집 실패] {str(e)[:80]}")

        _save_review_csv(all_rows, ckpt_path)
        print(f"  [체크포인트] {idx}/{len(links)} → {ckpt_path.name}")

        time.sleep(1)

    _save_review_csv(all_rows, save_path)
    if ckpt_path.exists():
        ckpt_path.unlink()
    print(f"\n[{sort_name}] 리뷰 수집 완료: {save_path}")
    print(f"  총 누적 리뷰: {len(all_rows)}개")

    return save_path


def _save_review_csv(rows: list[dict], path: Path) -> None:
    df = pd.DataFrame(rows, columns=REVIEW_OUTPUT_COLUMNS)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


# ============================================================
# 전체 실행
# ============================================================

def run(config: DaisoReviewCrawlConfig) -> list[Path]:
    """
    리뷰 수집 전체 실행 함수입니다.

    흐름:
    1. 브라우저 시작
    2. 정렬별 리뷰 수집
    3. 브라우저 종료
    """
    playwright = start_playwright()
    browser = create_browser(playwright, headless=config.headless)
    page = create_page(browser)

    saved_paths: list[Path] = []

    try:
        for sort_key in [s.strip() for s in config.sort.split(",") if s.strip()]:
            if sort_key not in SORT_MAP:
                print(f"[경고] 지원하지 않는 정렬 키: {sort_key}")
                continue

            path = collect_sort_reviews(page, sort_key=sort_key, config=config)

            if path:
                saved_paths.append(path)

    finally:
        safe_close(browser, playwright)

    print("\n모든 정렬에서 리뷰 수집 완료!")

    return saved_paths
