from __future__ import annotations

from playwright.sync_api import Browser, Page, Playwright, sync_playwright


# ============================================================
# browser.py
# ------------------------------------------------------------
# 역할:
# - Playwright 브라우저 시작 / 페이지 생성 / 종료
#
# 왜 따로 분리하는가?
# - 상품 수집(product_collector.py)과 리뷰 수집(review_collector.py)이
#   모두 같은 브라우저 설정을 사용하기 때문입니다.
# - 브라우저 설정을 한 곳에서 관리하면 수정이 쉬워집니다.
# ============================================================


def start_playwright() -> Playwright:
    """
    Playwright를 시작하고 인스턴스를 반환합니다.

    사용 후 반드시 safe_close()로 종료해야 합니다.
    """
    return sync_playwright().start()


def create_browser(playwright: Playwright, *, headless: bool = False) -> Browser:
    """
    Chromium 브라우저를 실행합니다.

    Parameters
    ----------
    playwright:
        start_playwright()로 얻은 Playwright 인스턴스

    headless:
        True면 브라우저 창 없이 실행 (디버깅 시 False 권장)
    """
    return playwright.chromium.launch(
        headless=headless,
        args=["--disable-blink-features=AutomationControlled"],
    )


def create_page(browser: Browser) -> Page:
    """
    브라우저 페이지를 생성하고 기본 설정을 적용합니다.

    뷰포트와 User-Agent를 고정해 일반 사용자처럼 보이게 합니다.
    """
    return browser.new_page(
        viewport={"width": 1400, "height": 1000},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
        ),
    )


def safe_close(browser: Browser | None, playwright: Playwright | None) -> None:
    """
    브라우저와 Playwright를 안전하게 종료합니다.

    크롤링 도중 오류가 발생해도 finally 블록에서 호출하면
    브라우저 프로세스가 남지 않습니다.
    """
    try:
        if browser:
            browser.close()
    except Exception:
        pass

    try:
        if playwright:
            playwright.stop()
    except Exception:
        pass
