from __future__ import annotations

import html as html_lib

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import Page

from .common import clean_text, extract_volume_ml, normalize_img_url
from .config import DETAIL_DESC_API, REQUEST_HEADERS


# ============================================================
# product_parser.py
# ------------------------------------------------------------
# 역할:
# - Playwright 페이지에서 상품 기본 정보 추출
# - 상세 설명 API 호출로 이미지 URL 목록 반환
#
# 왜 따로 분리하는가?
# - 실제 데이터 수집(orchestration)과 HTML/API 파싱을 분리하면
#   파싱 로직을 독립적으로 수정·테스트할 수 있습니다.
# ============================================================


def get_text_safe(page: Page, selector: str) -> str:
    """
    CSS 선택자로 요소를 찾아 텍스트를 반환합니다.

    요소가 없거나 타임아웃이 발생하면 빈 문자열을 반환합니다.
    """
    try:
        locator = page.locator(selector).first

        if locator.count() == 0:
            return ""

        return clean_text(locator.inner_text(timeout=5000))

    except Exception:
        return ""


def parse_detail_page(
    page: Page,
    url: str,
    *,
    detail_delay_ms: int = 2500,
) -> dict[str, str]:
    """
    상품 상세 페이지에서 기본 정보를 추출합니다.

    수집 항목:
    - product_name : 상품명 (브랜드 포함 전체)
    - brand        : 상품명 첫 어절 (브랜드)
    - regular_price: 정가
    - discount     : 할인율 (다이소는 대부분 없음)
    - sales_price  : 판매가
    - rating       : 평점
    - review_count : 리뷰 수
    - volume_ml    : 상품명에서 추출한 용량
    """
    page.goto(url, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(detail_delay_ms)

    product_name = get_text_safe(page, "h1.product-title")

    brand = ""
    if product_name:
        parts = product_name.split()
        brand = parts[0] if parts else ""

    regular_price = get_text_safe(page, "div.price-value span.value")
    sales_price = regular_price
    discount = ""

    rating = get_text_safe(page, "span.rate-txt")

    review_count = get_text_safe(page, "span.rate-txt-sm")
    review_count = review_count.replace("(", "").replace(")", "").strip()

    volume_ml = extract_volume_ml(product_name)

    return {
        "product_name": product_name,
        "brand": brand,
        "regular_price": regular_price,
        "discount": discount,
        "sales_price": sales_price,
        "rating": rating,
        "review_count": review_count,
        "volume_ml": volume_ml,
    }


def parse_main_ingredients(page: Page) -> str:
    """
    상품 상세 페이지의 '주요성분' 섹션에서 chip 텍스트를 추출합니다.

    HTML 구조:
        <div class="title-text">주요성분</div>
        ...
        <span class="chip-button__inner">레티놀</span>

    Returns
    -------
    "레티놀, 나이아신아마이드" 형태의 문자열, 없으면 빈 문자열
    """
    try:
        # "주요성분" 타이틀의 바로 위 부모만 올라가서 그 안의 칩만 가져옴
        title = page.locator("div.title-text").filter(has_text="주요성분").first
        if title.count() == 0:
            return ""
        section = title.locator("xpath=..")
        chips = section.locator("span.chip-button__inner")
        count = chips.count()
        if count == 0:
            return ""
        names = [
            clean_text(chips.nth(i).inner_text(timeout=3000))
            for i in range(count)
        ]
        return ", ".join(n for n in names if n)
    except Exception:
        return ""


def fetch_desc_images(pd_no: str) -> list[str]:
    """
    다이소몰 API를 호출해 상품 상세 설명 이미지 URL 목록을 반환합니다.

    API 응답의 pdDtlDc 필드는 HTML-escaped 문자열입니다.
    unescape 후 BeautifulSoup으로 img src를 추출합니다.

    Raises
    ------
    ValueError
        API 응답에 pdDtlDc 데이터가 없는 경우
    requests.HTTPError
        API 호출 실패
    """
    response = requests.post(
        DETAIL_DESC_API,
        headers=REQUEST_HEADERS,
        json={"pdNo": pd_no},
        timeout=30,
    )

    response.raise_for_status()
    data = response.json()

    escaped_html = (
        data
        .get("data", {})
        .get("pdDtlDesc", {})
        .get("pdDtlDc", "")
    )

    if not escaped_html:
        raise ValueError(f"pdDtlDc empty: {pd_no}")

    real_html = html_lib.unescape(escaped_html)
    soup = BeautifulSoup(real_html, "html.parser")

    imgs: list[str] = []

    for img in soup.find_all("img"):
        src = normalize_img_url(img.get("src", ""))

        if src and src not in imgs:
            imgs.append(src)

    return imgs
