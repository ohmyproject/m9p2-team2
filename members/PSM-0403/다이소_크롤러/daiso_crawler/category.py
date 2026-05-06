from __future__ import annotations

import re

from playwright.sync_api import Page

from .config import SORT_MAP, DaisoCrawlConfig, DaisoReviewCrawlConfig


# ============================================================
# category.py
# ------------------------------------------------------------
# 역할:
# - 다이소몰 카테고리 페이지 이동
# - 정렬 버튼 클릭
# - 상품 링크(pdNo) 스크롤 수집
#
# 왜 따로 분리하는가?
# - 상품 수집(product_collector)과 리뷰 수집(review_collector) 모두
#   같은 방식으로 상품 링크를 수집하기 때문입니다.
# ============================================================


def _click_sort_button(page: Page, button_text: str, page_delay_ms: int) -> None:
    """
    카테고리 페이지에서 정렬 버튼을 클릭합니다.

    판매량순(기본)은 URL에 이미 반영되어 있어 클릭이 필요 없을 수 있지만,
    일관성을 위해 항상 클릭을 시도합니다.
    """
    try:
        button = page.locator(f"span.name:has-text('{button_text}')").first
        button.wait_for(state="visible", timeout=15000)
        button.click()

        page.wait_for_timeout(page_delay_ms)

        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass

        print(f"[정렬] {button_text} 클릭 완료")

    except Exception as e:
        print(f"[정렬 버튼 클릭 실패] {button_text}: {str(e)[:80]}")


def collect_product_links(
    page: Page,
    *,
    sort_key: str,
    category_url: str,
    target_count: int,
    page_delay_ms: int,
    scroll_delay_ms: int,
) -> list[dict[str, str | int]]:
    """
    다이소몰 카테고리 페이지를 스크롤하며 상품 링크를 수집합니다.

    Parameters
    ----------
    page:
        Playwright Page 객체

    sort_key:
        SORT_MAP의 키 ('best', 'new', 'low', 'high', 'rate')

    category_url:
        카테고리 기본 URL (정렬 파라미터 제외)

    target_count:
        수집 목표 상품 수

    page_delay_ms / scroll_delay_ms:
        페이지 로드 및 스크롤 후 대기 시간 (ms)

    Returns
    -------
    list of dict:
        [{'rank': 1, 'pdNo': '...', 'url': '...'}, ...]
    """
    url_param, button_text, sort_name = SORT_MAP[sort_key]
    full_url = f"{category_url}?srt={url_param}"

    print("=" * 60)
    print(f"카테고리 이동: {sort_name}")
    print(f"URL: {full_url}")
    print("=" * 60)

    page.goto(full_url, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(page_delay_ms)

    # 판매량순이 아닌 경우 정렬 버튼 클릭
    # (판매량순은 URL 파라미터만으로도 적용되지만 일관성을 위해 항상 클릭)
    _click_sort_button(page, button_text, page_delay_ms)

    products: list[dict[str, str | int]] = []
    seen: set[str] = set()

    for _ in range(35):
        links: list[str] = page.locator(
            "a[href*='SCR_PDR_0001?pdNo=']"
        ).evaluate_all("els => els.map(a => a.href)")

        for href in links:
            if not href:
                continue

            full_href = (
                "https://www.daisomall.co.kr" + href
                if href.startswith("/")
                else href
            )

            match = re.search(r"pdNo=([^&]+)", full_href)

            if not match:
                continue

            pd_no = match.group(1)

            if pd_no in seen:
                continue

            seen.add(pd_no)

            products.append({
                "rank": len(products) + 1,
                "pdNo": pd_no,
                "url": f"https://www.daisomall.co.kr/pd/pdr/SCR_PDR_0001?pdNo={pd_no}&recmYn=N",
            })

            if len(products) >= target_count:
                print(f"[수집 완료] {len(products)}개")
                return products

        page.mouse.wheel(0, 3000)
        page.wait_for_timeout(scroll_delay_ms)

    print(f"[수집 완료] {len(products)}개 (스크롤 한계 도달)")
    return products[:target_count]


def collect_product_links_from_config(
    page: Page,
    config: DaisoCrawlConfig | DaisoReviewCrawlConfig,
    *,
    sort_key: str,
) -> list[dict[str, str | int]]:
    """
    config 객체에서 필요한 값을 꺼내 collect_product_links를 호출합니다.

    DaisoCrawlConfig와 DaisoReviewCrawlConfig 모두 사용할 수 있습니다.
    """
    target = getattr(config, "target_count", getattr(config, "target_product_count", 24))

    return collect_product_links(
        page,
        sort_key=sort_key,
        category_url=config.category_url,
        target_count=target,
        page_delay_ms=config.page_delay_ms,
        scroll_delay_ms=config.scroll_delay_ms,
    )
