# 네이버 검색 → 올리브영 공식몰 클릭 → 새 탭 전환입니다.

# crawler/naver_entry.py

import time

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from crawler.config import NAVER_URL, SEARCH_KEYWORD, WAIT_TIME


def enter_oliveyoung_from_naver(driver):
    """
    네이버에서 올리브영을 검색하고,
    공식몰이 새 탭에서 열리면 그 탭으로 전환합니다.
    """

    wait = WebDriverWait(driver, WAIT_TIME)

    print("[검색] 네이버 접속")
    driver.get(NAVER_URL)

    search_box = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='query']"))
    )

    print("[검색] 올리브영 검색")
    search_box.clear()
    search_box.send_keys(SEARCH_KEYWORD)
    search_box.send_keys(Keys.ENTER)

    time.sleep(2)

    before_tabs = driver.window_handles
    link = find_official_link(driver)

    if not link:
        raise Exception("올리브영 공식몰 링크를 찾지 못했습니다.")

    print("[접속] 올리브영 공식몰 클릭")
    link.click()

    wait.until(lambda d: len(d.window_handles) > len(before_tabs))

    new_tab = [tab for tab in driver.window_handles if tab not in before_tabs][0]
    driver.switch_to.window(new_tab)

    print("[접속] 새 탭 전환 완료")
    print("[현재 URL]", driver.current_url)

    time.sleep(3)


def find_official_link(driver):
    """
    네이버 검색 결과에서 oliveyoung.co.kr 링크를 찾습니다.
    """

    links = driver.find_elements(By.TAG_NAME, "a")

    for link in links:
        href = link.get_attribute("href") or ""

        if "oliveyoung.co.kr" in href:
            return link

    return None