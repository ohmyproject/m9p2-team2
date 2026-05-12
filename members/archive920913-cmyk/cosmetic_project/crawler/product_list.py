import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from crawler.config import WAIT_TIME
from crawler.utils import clean_text, clean_int, extract_volume_ml, calc_discount


def wait_product_list(driver):
    wait = WebDriverWait(driver, WAIT_TIME)
    wait.until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".prd_info"))
    )


def get_product_count(driver):
    return len(driver.find_elements(By.CSS_SELECTOR, ".prd_info"))


def get_product_summary_by_index(driver, index):
    cards = driver.find_elements(By.CSS_SELECTOR, ".prd_info")

    if index >= len(cards):
        raise Exception(f"상품 index 초과: {index}")

    card = cards[index]

    brand = get_text(card, ".tx_brand")
    product_name = get_text(card, ".tx_name")
    regular_price = clean_int(get_text(card, ".tx_org .tx_num"))
    sales_price = clean_int(get_text(card, ".tx_cur .tx_num"))
    url = get_href(card, "a.prd_thumb")

    if regular_price == 0:
        regular_price = sales_price

    return {
        "brand": brand,
        "product_name": product_name,
        "volume_ml": extract_volume_ml(product_name),
        "regular_price": regular_price,
        "discount": calc_discount(regular_price, sales_price),
        "sales_price": sales_price,
        "url": url,
    }


def click_product_by_index(driver, index):
    links = driver.find_elements(By.CSS_SELECTOR, ".prd_info a.prd_thumb")

    if index >= len(links):
        raise Exception(f"상품 링크 index 초과: {index}")

    target = links[index]

    driver.execute_script(
        "arguments[0].scrollIntoView({block:'center'});",
        target,
    )
    time.sleep(0.5)
    driver.execute_script("arguments[0].click();", target)
    time.sleep(2)


def go_back_to_list(driver, list_url):
    for _ in range(3):
        try:
            driver.back()
            wait_product_list(driver)
            return
        except Exception:
            time.sleep(1)

    driver.get(list_url)
    wait_product_list(driver)


def get_text(parent, selector):
    try:
        return clean_text(parent.find_element(By.CSS_SELECTOR, selector).text)
    except Exception:
        return ""


def get_href(parent, selector):
    try:
        return parent.find_element(By.CSS_SELECTOR, selector).get_attribute("href") or ""
    except Exception:
        return ""