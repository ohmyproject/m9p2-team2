# daiso_sales_info.py

import re
import time
import html as html_lib
from datetime import datetime

import requests
import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from PIL import Image
from io import BytesIO
import pytesseract


pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


CATEGORY_URL = "https://www.daisomall.co.kr/ds/exhCtgr/C208/CTGR_01050/CTGR_01051/CTGR_01065?srt=SALE_QTY_DESC"
DETAIL_DESC_API = "https://fapi.daisomall.co.kr/pd/pdr/pdDtl/selPdDtlDesc"

TARGET_COUNT = 24

RUN_DATE = datetime.now().strftime("%y%m%d")
PLATFORM = "daiso"
RANKING_TYPE = "판매순"

OUTPUT_CSV = f"daiso_판매순(info)_{RUN_DATE}.csv"
OUTPUT_XLSX = f"daiso_판매순(info)_{RUN_DATE}.xlsx"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.daisomall.co.kr/",
    "Origin": "https://www.daisomall.co.kr",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
}


def clean_text(text):
    if not text:
        return ""
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_img_url(src):
    if not src:
        return ""
    if src.startswith("//"):
        return "https:" + src
    if src.startswith("/"):
        return "https://cdn.daisomall.co.kr" + src
    return src


def clean_ingredients_advanced(text):
    if not text:
        return ""
    text = re.sub(r"[^\w가-힣,\-\(\)\s/%\.\*\[\]]", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\b[A-Z0-9\|]{5,}\b", "", text)
    return clean_text(text)


def extract_volume_ml(product_name):
    if not product_name:
        return ""

    match = re.search(r"(\d+(?:\.\d+)?)\s*(ml|mL|ML|㎖)", product_name)

    if match:
        value = match.group(1)
        if value.endswith(".0"):
            value = value.replace(".0", "")
        return value

    return ""


def get_text_safe(page, selector):
    try:
        locator = page.locator(selector).first
        if locator.count() == 0:
            return ""
        return clean_text(locator.inner_text(timeout=5000))
    except Exception:
        return ""


def get_sales_products(page, target_count=24):
    page.goto(CATEGORY_URL, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(4000)

    products = []
    seen = set()

    for _ in range(35):
        links = page.locator("a[href*='SCR_PDR_0001?pdNo=']").evaluate_all(
            "els => els.map(a => a.href)"
        )

        for href in links:
            if not href:
                continue

            if href.startswith("/"):
                url = "https://www.daisomall.co.kr" + href
            else:
                url = href

            match = re.search(r"pdNo=([^&]+)", url)
            if not match:
                continue

            pd_no = match.group(1)

            if pd_no in seen:
                continue

            seen.add(pd_no)

            products.append({
                "rank": len(products) + 1,
                "pdNo": pd_no,
                "url": f"https://www.daisomall.co.kr/pd/pdr/SCR_PDR_0001?pdNo={pd_no}&recmYn=N"
            })

            if len(products) >= target_count:
                return products

        page.mouse.wheel(0, 3000)
        page.wait_for_timeout(1200)

    return products[:target_count]


def get_product_info_from_detail_page(page, url):
    page.goto(url, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(2500)

    product_name = get_text_safe(page, "h1.product-title")

    brand = ""
    if product_name:
        parts = product_name.split()
        brand = parts[0] if parts else ""

    regular_price = get_text_safe(page, "div.price-value span.value")
    sales_price = regular_price
    discount = ""

    rating = get_text_safe(page, "span.rate-txt")
    review_count = get_text_safe(page, "span.rate-txt-sm")
    review_count = review_count.replace("(", "").replace(")", "").strip()

    volume_ml = extract_volume_ml(product_name)

    return {
        "product_name": product_name,
        "brand": brand,
        "regular_price": regular_price,
        "discount": discount,
        "sales_price": sales_price,
        "rating": rating,
        "review_count": review_count,
        "volume_ml": volume_ml,
    }


def get_desc_images_from_api(pd_no):
    response = requests.post(
        DETAIL_DESC_API,
        headers=HEADERS,
        json={"pdNo": pd_no},
        timeout=30
    )

    response.raise_for_status()
    data = response.json()

    escaped_html = (
        data
        .get("data", {})
        .get("pdDtlDesc", {})
        .get("pdDtlDc", "")
    )

    if not escaped_html:
        raise ValueError(f"pdDtlDc empty: {pd_no}")

    real_html = html_lib.unescape(escaped_html)
    soup = BeautifulSoup(real_html, "html.parser")

    imgs = []
    for img in soup.find_all("img"):
        src = normalize_img_url(img.get("src"))
        if src and src not in imgs:
            imgs.append(src)

    return imgs


def pick_ingredient_image(imgs):
    if not imgs:
        return ""
    return imgs[-1]


def extract_text_from_image(url):
    if not url:
        return ""

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()

        image = Image.open(BytesIO(response.content)).convert("RGB")

        width, height = image.size
        max_height = 4000
        texts = []

        for y in range(0, height, max_height):
            crop = image.crop((0, y, width, min(y + max_height, height)))

            cw, ch = crop.size
            if cw < 1200:
                crop = crop.resize((cw * 2, ch * 2))

            crop = crop.convert("L")

            text = pytesseract.image_to_string(
                crop,
                lang="kor+eng",
                config="--psm 6"
            )

            texts.append(text)

        return clean_text("\n".join(texts))

    except Exception as e:
        return f"OCR_FAIL: {e}"


def extract_ingredients_only(text):
    if not text:
        return ""

    if text.startswith("OCR_FAIL"):
        return text

    match = re.search(r"전성분[:：]?\s*(.+)", text)

    if not match:
        match = re.search(r"모든\s*성분\s*(.+)", text)

    if not match:
        match = re.search(r"(정제수\s*,.+)", text)

    if not match:
        return ""

    ingredients = match.group(1)

    ingredients = re.split(
        r"사용할\s*때|사용할때|사용시|사용 시|주의사항|품질\s*보증|품질보증|소비자\s*상담|고객상담|제조국|화장품법|식품의약품안전처|용법/용량|용법용량",
        ingredients
    )[0]

    return clean_text(ingredients)


def get_ingredients(pd_no):
    imgs = get_desc_images_from_api(pd_no)
    ingredient_img = pick_ingredient_image(imgs)

    ocr_text = extract_text_from_image(ingredient_img)
    ingredients_raw = extract_ingredients_only(ocr_text)
    ingredients_clean = clean_ingredients_advanced(ingredients_raw)

    if ingredients_clean:
        ing_source = "OCR"
    else:
        ing_source = "OCR_EMPTY"

    if ocr_text.startswith("OCR_FAIL"):
        ing_source = "OCR_FAIL"

    return ingredients_clean, ing_source


def save_results(results):
    df = pd.DataFrame(
        results,
        columns=[
            "date",
            "platform",
            "ranking_type",
            "rank",
            "volume_ml",
            "product_name",
            "brand",
            "regular_price",
            "discount",
            "sales_price",
            "rating",
            "review_count",
            "url",
            "ingredients",
            "ing_source",
            "crawled_at",
        ]
    )

    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    df.to_excel(OUTPUT_XLSX, index=False)

    print(f"저장 완료: {OUTPUT_CSV}")
    print(f"저장 완료: {OUTPUT_XLSX}")


def main():
    crawled_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )

        page = browser.new_page(
            viewport={"width": 1400, "height": 1000},
            user_agent=HEADERS["User-Agent"]
        )

        products = get_sales_products(page, TARGET_COUNT)

        print(f"수집된 상품 수: {len(products)}")

        for item in products:
            rank = item["rank"]
            pd_no = item["pdNo"]
            url = item["url"]

            print(f"\n[{rank}/{TARGET_COUNT}] {pd_no}")

            product_info = {
                "product_name": "",
                "brand": "",
                "regular_price": "",
                "discount": "",
                "sales_price": "",
                "rating": "",
                "review_count": "",
                "volume_ml": "",
            }

            ingredients = ""
            ing_source = ""

            try:
                product_info = get_product_info_from_detail_page(page, url)
                print(f"제품명: {product_info['product_name']}")
                print(f"용량: {product_info['volume_ml']}")
                print(f"가격: {product_info['regular_price']}")
                print(f"평점: {product_info['rating']}")
                print(f"리뷰수: {product_info['review_count']}")
            except Exception as e:
                print(f"상세 정보 추출 실패: {e}")

            try:
                ingredients, ing_source = get_ingredients(pd_no)
                print(f"전성분 일부: {ingredients[:80]}")
            except Exception as e:
                print(f"전성분 추출 실패: {e}")
                ing_source = "OCR_FAIL"

            results.append({
                "date": RUN_DATE,
                "platform": PLATFORM,
                "ranking_type": RANKING_TYPE,
                "rank": rank,
                "volume_ml": product_info.get("volume_ml", ""),
                "product_name": product_info.get("product_name", ""),
                "brand": product_info.get("brand", ""),
                "regular_price": product_info.get("regular_price", ""),
                "discount": product_info.get("discount", ""),
                "sales_price": product_info.get("sales_price", ""),
                "rating": product_info.get("rating", ""),
                "review_count": product_info.get("review_count", ""),
                "url": url,
                "ingredients": ingredients,
                "ing_source": ing_source,
                "crawled_at": crawled_at,
            })

            if len(results) % 10 == 0:
                print(f"\n{len(results)}개 수집 완료 - 부분 저장")
                save_results(results)

            time.sleep(0.5)

        browser.close()

    print("\n최종 저장")
    save_results(results)


if __name__ == "__main__":
    main()