"""리뷰 태그 크롤링"""
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


def get_tags(driver) -> list:
    """
    리뷰 전체보기 → 태그 버튼 수집 (+N 더보기 포함)
    반환: tag 문자열 리스트
    """
    wait = WebDriverWait(driver, 15)
    tags = []

    # 리뷰 탭 클릭
    try:
        for btn in driver.find_elements(By.CSS_SELECTOR, "button[data-shp-area='tab.select']"):
            if btn.text.strip().startswith("리뷰"):
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(2)
                break
    except Exception:
        pass

    # 리뷰 전체보기 클릭
    try:
        driver.execute_script("window.scrollBy(0, 600);")
        time.sleep(1.5)

        wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "button[data-shp-area='sprvrpre.more']")))
        more_btn = driver.find_element(
            By.CSS_SELECTOR, "button[data-shp-area='sprvrpre.more']")
        driver.execute_script("arguments[0].click();", more_btn)
        time.sleep(3)

        # 태그 버튼 로딩 대기
        for _ in range(20):
            cnt = driver.execute_script(
                "return document.querySelectorAll(\"button[data-shp-area*='.tag']\").length;")
            if cnt > 0:
                break
            time.sleep(0.5)

        # +N 더보기 버튼 클릭
        has_more = driver.execute_script("""
            const btn = document.querySelector("button[data-shp-contents-type^='+']");
            if (btn) { btn.click(); return true; }
            return false;
        """)
        if has_more:
            time.sleep(2.5)

        # 태그 수집 (중복 제거, +N 제외)
        tags = driver.execute_script("""
            const seen = new Set();
            return Array.from(
                document.querySelectorAll("button[data-shp-area*='.tag']")
            )
            .map(b => b.getAttribute('data-shp-contents-type'))
            .filter(t => {
                if (!t || !t.trim() || /^\\+\\d+$/.test(t.trim())) return false;
                if (seen.has(t)) return false;
                seen.add(t);
                return true;
            });
        """) or []

    except TimeoutException:
        pass
    except Exception:
        pass

    return tags
