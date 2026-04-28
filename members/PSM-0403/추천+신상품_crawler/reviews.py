"""평점 + 총 리뷰 수 + 리뷰 본문 크롤링"""
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

REVIEW_LIMIT = 10


def get_rating(driver) -> str:
    """현재 페이지에서 평점 추출"""
    return driver.execute_script("""
        for (const tag of ['span','em','strong']) {
            for (const el of document.querySelectorAll(tag)) {
                const t = el.textContent.trim();
                if (/^[1-5]\\.[0-9]{1,2}$/.test(t)) return t;
            }
        }
        return '';
    """)


def get_reviews(driver, review_limit: int = REVIEW_LIMIT) -> tuple:
    """
    리뷰 탭 클릭 → 전체보기 → 리뷰 본문 수집
    반환: (review_count: str, review_texts: list)
    """
    wait = WebDriverWait(driver, 20)
    review_count  = ""
    review_texts  = []

    # 리뷰 탭 클릭 + 리뷰수 수집
    try:
        for btn in driver.find_elements(By.CSS_SELECTOR, "button[data-shp-area='tab.select']"):
            if btn.text.strip().startswith("리뷰"):
                review_count = btn.text.strip().replace("리뷰", "").replace(",", "").strip()
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(2)
                break
    except Exception:
        pass

    # 리뷰 전체보기 버튼 클릭
    try:
        driver.execute_script("window.scrollBy(0, 600);")
        time.sleep(1.5)

        wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "button[data-shp-area='sprvrpre.more']")))
        more_btn = driver.find_element(
            By.CSS_SELECTOR, "button[data-shp-area='sprvrpre.more']")
        driver.execute_script("arguments[0].click();", more_btn)
        time.sleep(3)

        # 리뷰 텍스트 수집 (스크롤 반복)
        for _ in range(8):
            els = driver.find_elements(By.CSS_SELECTOR, "[id^='review_content_']")
            review_texts = [el.text.strip() for el in els if el.text.strip()]
            if len(review_texts) >= review_limit:
                break
            driver.execute_script("window.scrollBy(0, 800);")
            time.sleep(1.5)

    except TimeoutException:
        pass
    except Exception:
        pass

    return review_count, review_texts[:review_limit]
