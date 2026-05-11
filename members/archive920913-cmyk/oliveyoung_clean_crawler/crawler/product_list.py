# 목록에서는 상품 진입에 필요한 기본 정보만 수집합니다.

import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from crawler.config import WAIT_TIME
from crawler.utils import extract_volume


def wait_product_list(driver):
    WebDriverWait(driver, WAIT_TIME).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".prd_info"))
    )
    time.sleep(1)


def get_product_count(driver):
    wait_product_list(driver)
    return len(driver.find_elements(By.CSS_SELECTOR, ".prd_info"))


def get_product_summary_by_index(driver, index):
    wait_product_list(driver)

    cards = driver.find_elements(By.CSS_SELECTOR, ".prd_info")

    if index >= len(cards):
        raise Exception(f"{index + 1}번째 상품 없음")

    card = cards[index]

    def text(selector):
        try:
            element = card.find_element(By.CSS_SELECTOR, selector)
            value = driver.execute_script("return arguments[0].textContent;", element)
            return value.strip() if value else ""
        except Exception:
            return ""

    product_name = text(".tx_name")
    regular_price = text(".tx_org .tx_num")
    sales_price = text(".tx_cur .tx_num")

    url = card.find_element(By.CSS_SELECTOR, "a.prd_thumb").get_attribute("href")

    return {
        "brand": text(".tx_brand"),
        "product_name": product_name,
        "volume_ml": extract_volume(product_name),
        "regular_price": regular_price,
        "discount": calc_discount(regular_price, sales_price),
        "sales_price": sales_price,
        "url": url,
    }


def click_product_by_index(driver, index):
    wait_product_list(driver)

    links = driver.find_elements(By.CSS_SELECTOR, ".prd_info a.prd_thumb")

    if index >= len(links):
        raise Exception(f"{index + 1}번째 상품 링크 없음")

    target = links[index]

    print(f"[상품] {index + 1}위 상품 클릭")

    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", target)
    time.sleep(0.5)
    driver.execute_script("arguments[0].click();", target)
    time.sleep(2)


def go_back_to_list(driver, list_url=None):
    """
    상세페이지/리뷰탭에서 목록으로 돌아갑니다.

    1차: driver.back()
    2차: driver.back()
    3차: driver.back()
    실패 시: 저장해둔 목록 URL로 복구
    """

    print("[복귀] 목록으로 돌아가는 중")

    for i in range(3):
        try:
            driver.back()
            time.sleep(2)
            wait_product_list(driver)
            print("[복귀] 목록 복귀 완료")
            return
        except Exception:
            print(f"[복귀] back 실패 {i + 1}회")

    if list_url:
        print("[복귀] 목록 URL로 복구")
        driver.get(list_url)
        time.sleep(3)
        wait_product_list(driver)
        print("[복귀] 목록 복구 완료")
        return

    raise Exception("목록으로 복귀 실패")


def calc_discount(regular_price, sales_price):
    try:
        rp = int(regular_price.replace(",", ""))
        sp = int(sales_price.replace(",", ""))

        if rp > sp:
            return f"{round((rp - sp) / rp * 100)}%"
    except Exception:
        pass

    return ""