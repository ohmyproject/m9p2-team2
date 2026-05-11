# 상세페이지에서는 리뷰수, 평점, 전성분을 보완 수집합니다.

import re
import time

from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait

from crawler.utils import clean_text, extract_volume


def collect_product_detail(driver, sort_type="", rank="", list_info=None):
    list_info = list_info or {}

    WebDriverWait(driver, 15).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )

    time.sleep(1)
    open_product_notice(driver)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    notice = extract_notice_table(soup)

    product_name = list_info.get("product_name", "")
    brand = list_info.get("brand", "")

    review_count_raw = text_from_soup(soup, [
        ".ReviewArea_btn-review__gZoOZ",
        ".ReviewArea_btn-review__gZoOZ span",
        ".review_total",
        ".goods_reputation",
        "a[href*='review']",
        "button[aria-controls*='review']",
    ])

    rating_raw = text_from_soup(soup, [
        ".ReviewArea_rating-star__al_PT",
        ".review_point .point",
        ".point",
        ".star_area .num",
    ])

    review_count = extract_review_count(review_count_raw)
    rating = extract_rating(rating_raw)

    ingredients = notice.get("ingredients", "")
    volume_ml = list_info.get("volume_ml", "") or extract_volume(product_name)

    if not volume_ml:
        volume_ml = extract_volume(notice.get("volume_ml", ""))

    print(f"[상품정보] {brand} / {product_name} / 리뷰 {review_count}")
    print(f"[전성분 길이] {len(ingredients)}")

    return {
        "sort_type": sort_type,
        "rank": rank,
        "product_name": product_name,
        "brand": brand,
        "volume_ml": volume_ml,
        "regular_price": list_info.get("regular_price", ""),
        "discount": list_info.get("discount", ""),
        "sales_price": list_info.get("sales_price", ""),
        "rating": rating,
        "review_count": review_count,
        "main_ingredients": "",
        "ingredients": ingredients,
        "ing_source": "oliveyoung_notice" if ingredients else "",
        "url": driver.current_url or list_info.get("url", ""),
    }


def text_from_soup(soup, selectors):
    for selector in selectors:
        tag = soup.select_one(selector)

        if tag:
            value = clean_text(tag.get_text(" ", strip=True))

            if value:
                return value

    return ""


def open_product_notice(driver):
    buttons = driver.find_elements("tag name", "button")

    for button in buttons:
        text = clean_text(button.text)

        if "상품정보 제공고시" not in text:
            continue

        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", button)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", button)
            time.sleep(1.5)
            print("[전성분] 상품정보 제공고시 펼침")
            return True
        except Exception:
            return False

    print("[전성분] 상품정보 제공고시 버튼 못 찾음")
    return False


def extract_notice_table(soup):
    result = {}

    for row in soup.find_all("tr"):
        th = row.find("th")
        td = row.find("td")

        if not th or not td:
            continue

        label = clean_text(th.get_text(" ", strip=True))
        value = clean_text(td.get_text(" ", strip=True))

        if "내용물의 용량 또는 중량" in label:
            result["volume_ml"] = value

        if (
            "화장품법에 따라 기재해야 하는 모든 성분" in label
            or "전성분" in label
            or "모든 성분" in label
        ):
            result["ingredients"] = value

    return result


def extract_review_count(text):
    if not text:
        return ""

    match = re.search(r"리뷰\s*([0-9,]+)", text)

    if match:
        return match.group(1)

    match = re.search(r"\(([0-9,]+)\)", text)

    if match:
        return match.group(1)

    numbers = re.findall(r"[0-9,]+", text)

    if numbers:
        return numbers[-1]

    return ""


def extract_rating(text):
    if not text:
        return ""

    match = re.search(r"([0-9]\.[0-9])", text)

    if match:
        return match.group(1)

    return ""