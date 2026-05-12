import re
import time

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By

from crawler.utils import clean_text, clean_int, extract_volume_ml


def collect_product_detail(driver):
    wait_page_ready(driver)
    open_product_info_notice(driver)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    rating = extract_rating(soup)
    review_count = extract_review_count(soup)
    ingredients = extract_ingredients(soup)
    volume_ml = extract_volume_from_notice(soup)

    return {
        "rating": rating,
        "review_count": review_count,
        "main_ingredients": "",
        "ingredients": ingredients,
        "ing_source": "oliveyoung",
        "volume_ml": volume_ml,
    }


def wait_page_ready(driver):
    for _ in range(20):
        state = driver.execute_script("return document.readyState")
        if state == "complete":
            return
        time.sleep(0.5)


def open_product_info_notice(driver):
    buttons = driver.find_elements(By.TAG_NAME, "button")

    for btn in buttons:
        try:
            text = clean_text(btn.text)

            if "상품정보 제공고시" in text:
                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});",
                    btn,
                )
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(1)
                return

        except Exception:
            continue


def extract_rating(soup):
    text = soup.get_text(" ", strip=True)

    patterns = [
        r"평점\s*([0-9.]+)",
        r"별점\s*([0-9.]+)",
        r"([0-9.]+)\s*점",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            try:
                return float(match.group(1))
            except Exception:
                return 0

    return 0


def extract_review_count(soup):
    text = soup.get_text(" ", strip=True)

    patterns = [
        r"리뷰\s*([0-9,]+)",
        r"상품평\s*([0-9,]+)",
        r"([0-9,]+)\s*건",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            return clean_int(match.group(1))

    return 0


def extract_ingredients(soup):
    rows = soup.find_all("tr")

    labels = [
        "화장품법에 따라 기재해야 하는 모든 성분",
        "전성분",
        "모든 성분",
    ]

    for row in rows:
        th = row.find("th")
        td = row.find("td")

        if not th or not td:
            continue

        label = clean_text(th.get_text(" ", strip=True))
        value = clean_text(td.get_text(" ", strip=True))

        if any(key in label for key in labels):
            return value

    return ""


def extract_volume_from_notice(soup):
    rows = soup.find_all("tr")

    for row in rows:
        th = row.find("th")
        td = row.find("td")

        if not th or not td:
            continue

        label = clean_text(th.get_text(" ", strip=True))
        value = clean_text(td.get_text(" ", strip=True))

        if "용량" in label or "중량" in label:
            return extract_volume_ml(value)

    return ""