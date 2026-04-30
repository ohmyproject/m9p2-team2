# daiso_판매순(review)_20260430.py
# 다이소몰 세럼/앰플 판매량순 상위 24개 상품 리뷰 수집
# 상품별 리뷰 10개씩, 총 최대 240행
# 상품 10개마다 부분 저장

import re
import time
from datetime import datetime

import pandas as pd
from playwright.sync_api import sync_playwright


CATEGORY_URL = "https://www.daisomall.co.kr/ds/exhCtgr/C208/CTGR_01050/CTGR_01051/CTGR_01065?srt=SALE_QTY_DESC"

TARGET_PRODUCT_COUNT = 24
REVIEWS_PER_PRODUCT = 10

TODAY = datetime.now().strftime("%Y%m%d")

OUTPUT_CSV = f"daiso_판매순(review)_{TODAY}.csv"
OUTPUT_XLSX = f"daiso_판매순(review)_{TODAY}.xlsx"

PARTIAL_CSV = f"daiso_판매순(review)_{TODAY}_partial.csv"
PARTIAL_XLSX = f"daiso_판매순(review)_{TODAY}_partial.xlsx"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
    )
}


def clean_text(text):
    if not text:
        return ""

    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_text_safe(locator):
    try:
        if locator.count() == 0:
            return ""
        return clean_text(locator.first.inner_text(timeout=5000))
    except Exception:
        return ""


def get_sales_top_products(page, target_count=24):
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

            url = href if href.startswith("http") else "https://www.daisomall.co.kr" + href

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


def extract_product_name(page):
    full_name = get_text_safe(page.locator("h1.product-title"))

    if not full_name:
        return ""

    parts = full_name.split()

    # 첫 어절 브랜드 제거
    if len(parts) >= 2:
        return " ".join(parts[1:])

    return full_name


def click_review_tab(page):
    try:
        review_button = page.locator("button:has-text('리뷰')").first
        review_button.wait_for(state="visible", timeout=15000)
        review_button.click()
        page.wait_for_timeout(3000)
        return True
    except Exception as e:
        print(f"리뷰 버튼 클릭 실패: {e}")
        return False


def extract_review_count(page):
    selectors = [
        "span.star-detail--cnt",
        "button:has-text('리뷰') em.count",
        "em.count",
    ]

    for selector in selectors:
        txt = get_text_safe(page.locator(selector))
        if txt:
            return txt.replace("(", "").replace(")", "").replace(",", "").strip()

    return ""


def get_review_cards(page):
    return page.locator("li.review-detail")


def load_reviews_enough(page, target_count=10):
    for _ in range(12):
        cards = get_review_cards(page)

        try:
            if cards.count() >= target_count:
                return cards
        except Exception:
            pass

        page.mouse.wheel(0, 2500)
        page.wait_for_timeout(1000)

    return get_review_cards(page)


def extract_review_rating(review_card):
    try:
        txt = get_text_safe(review_card.locator("span.hiddenText"))

        # 예: 별점 5점 → 5
        match = re.search(r"별점\s*([0-9.]+)\s*점", txt)
        if match:
            return match.group(1)

        return txt.replace("별점", "").replace("점", "").strip()

    except Exception:
        return ""


def extract_skin_type(review_card):
    """
    ul.info-list.review 안에서 item 텍스트가 '피부타입'인 li의 val만 추출.
    피부타입 항목이 없는 리뷰는 빈칸.
    """
    try:
        info_items = review_card.locator("ul.info-list.review li")
        count = info_items.count()

        for i in range(count):
            li = info_items.nth(i)

            item_name = get_text_safe(li.locator("div.item"))
            item_value = get_text_safe(li.locator("div.val"))

            if item_name == "피부타입":
                return item_value

        return ""

    except Exception:
        return ""


def extract_review_text(review_card):
    try:
        cont = review_card.locator("div.review-desc div.cont").first

        if cont.count() == 0:
            return ""

        txt = clean_text(cont.inner_text(timeout=5000))

        # 리뷰 배지 제거
        txt = re.sub(r"^(재구매|체험단|한달사용)\s+", "", txt)

        return txt

    except Exception:
        return ""


def crawl_reviews_for_product(page, product):
    url = product["url"]

    page.goto(url, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(3000)

    product_name = extract_product_name(page)

    clicked = click_review_tab(page)
    if not clicked:
        return []

    review_count = extract_review_count(page)

    cards = load_reviews_enough(page, REVIEWS_PER_PRODUCT)
    card_count = min(cards.count(), REVIEWS_PER_PRODUCT)

    print(f"제품명: {product_name}")
    print(f"총 리뷰수: {review_count}")
    print(f"리뷰 카드 수: {card_count}")

    rows = []

    for i in range(card_count):
        card = cards.nth(i)

        rows.append({
            "product_name": product_name,
            "review_count": review_count,
            "review_rating": extract_review_rating(card),
            "skin_type": extract_skin_type(card),
            "review_text": extract_review_text(card),
            "url": url,
        })

    return rows


def save_results(rows, csv_path, xlsx_path):
    df = pd.DataFrame(
        rows,
        columns=[
            "product_name",
            "review_count",
            "review_rating",
            "skin_type",
            "review_text",
            "url",
        ]
    )

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    df.to_excel(xlsx_path, index=False)


def main():
    all_rows = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )

        page = browser.new_page(
            viewport={"width": 1400, "height": 1000},
            user_agent=HEADERS["User-Agent"]
        )

        products = get_sales_top_products(page, TARGET_PRODUCT_COUNT)

        print(f"수집된 상품 수: {len(products)}")

        for idx, product in enumerate(products, start=1):
            print(f"\n[{idx}/{len(products)}] 상품 리뷰 수집 중: {product['pdNo']}")

            try:
                rows = crawl_reviews_for_product(page, product)
                all_rows.extend(rows)
                print(f"수집 리뷰 수: {len(rows)}")

            except Exception as e:
                print(f"상품 리뷰 수집 실패: {product['pdNo']} / {e}")

            # 상품 10개마다 부분 저장
            if idx % 10 == 0:
                save_results(all_rows, PARTIAL_CSV, PARTIAL_XLSX)
                print(f"부분 저장 완료: 상품 {idx}개 처리 / 누적 리뷰 {len(all_rows)}개")

            time.sleep(1)

        browser.close()

    save_results(all_rows, OUTPUT_CSV, OUTPUT_XLSX)

    print(f"\n최종 CSV 저장 완료: {OUTPUT_CSV}")
    print(f"최종 Excel 저장 완료: {OUTPUT_XLSX}")
    print(f"총 리뷰 행 수: {len(all_rows)}")


if __name__ == "__main__":
    main()