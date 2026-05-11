# 카테고리 클릭 → 에센스/세럼/앰플 클릭 → 사람 확인 감지입니다.

# crawler/category.py

import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from crawler.config import WAIT_TIME, BOT_CHECK_SLEEP


def move_to_essence_category(driver):
    """
    카테고리 메뉴를 열고
    스킨케어 아래의 에센스/세럼/앰플을 클릭합니다.
    """

    wait = WebDriverWait(driver, WAIT_TIME)

    print("[이동] 카테고리 클릭")
    category_btn = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), '카테고리')]"))
    )
    category_btn.click()

    time.sleep(1)

    print("[이동] 에센스/세럼/앰플 클릭")
    essence = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//*[contains(normalize-space(text()), '에센스/세럼/앰플')]")
        )
    )
    essence.click()

    print("[대기] 페이지 이동 후 대기")
    time.sleep(BOT_CHECK_SLEEP)

    wait_if_human_check_page(driver)


def wait_if_human_check_page(driver):
    """
    사람 확인 화면이 나오면 사용자가 직접 체크하게 기다립니다.
    자동 클릭하지 않습니다.
    """

    text = ""

    try:
        text = driver.find_element(By.TAG_NAME, "body").text
    except Exception:
        pass

    has_challenge = (
        "사람인지 확인" in text
        or "Cloudflare" in text
        or "cdn-cgi/challenge" in driver.current_url
    )

    if not has_challenge:
        print("[확인] 사람 확인 화면 없음")
        return

    print("=" * 70)
    print("[확인 필요] 브라우저에서 직접 사람 확인 체크를 해주세요.")
    print("[안내] 상품 목록이 보이면 터미널에서 Enter를 누르세요.")
    print("=" * 70)

    input("직접 체크 완료 후 Enter: ")
    time.sleep(3)