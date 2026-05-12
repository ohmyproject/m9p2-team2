import time

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from crawler.config import NAVER_URL, SEARCH_KEYWORD, WAIT_TIME


def enter_oliveyoung_from_naver(driver):
    wait = WebDriverWait(driver, WAIT_TIME)

    print("[1] 네이버 접속")
    driver.get(NAVER_URL)

    search_box = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='query']"))
    )

    print("[2] 올리브영 검색")
    search_box.clear()
    search_box.send_keys(SEARCH_KEYWORD)
    search_box.send_keys(Keys.ENTER)

    time.sleep(2)

    href = find_oliveyoung_href(driver)

    if not href:
        raise Exception("올리브영 공식몰 링크를 찾지 못했습니다.")

    print("[3] 현재 탭에서 올리브영 이동")
    driver.get(href)

    wait.until(lambda d: "oliveyoung.co.kr" in d.current_url)

    time.sleep(3)

    print("[완료] 올리브영 접속")
    print("[현재 URL]", driver.current_url)


def find_oliveyoung_href(driver):
    """
    stale element 방지용.
    WebElement를 반환하지 않고 href 문자열만 반환한다.
    """

    for attempt in range(5):
        try:
            links = driver.find_elements(By.TAG_NAME, "a")

            for link in links:
                try:
                    href = link.get_attribute("href") or ""

                    if "oliveyoung.co.kr" in href:
                        return href

                except Exception:
                    continue

        except Exception:
            pass

        time.sleep(1)

    return None