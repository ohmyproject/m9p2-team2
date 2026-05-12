from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from crawler.config import WAIT_TIME


def move_to_category(driver, category_name):
    wait = WebDriverWait(driver, WAIT_TIME)

    print("[1] 카테고리 버튼 클릭")
    category_btn = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), '카테고리')]"))
    )
    category_btn.click()

    print(f"[2] 세부 카테고리 클릭: {category_name}")
    target = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, f"//*[contains(normalize-space(text()), '{category_name}')]")
        )
    )
    target.click()

    check_human_page(driver)


def check_human_page(driver):
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text
    except Exception:
        body_text = ""

    current_url = driver.current_url

    is_human_check = (
        "사람인지 확인" in body_text
        or "Cloudflare" in body_text
        or "cdn-cgi/challenge" in current_url
    )

    if not is_human_check:
        print("[확인] 사람 확인 화면 없음")
        return

    print("=" * 70)
    print("[사람 확인 필요]")
    print("브라우저에서 직접 체크하세요.")
    print("상품 목록이 보이면 터미널에서 Enter를 누르세요.")
    print("=" * 70)

    input("체크 완료 후 Enter: ")