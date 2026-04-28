"""상품 목록 수집 (정렬 선택 가능, 정가·판매가·할인율 포함)"""
import json, re, time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

CATEGORY_URL = "https://search.shopping.naver.com/ns/category/10002147"


def _parse_dtl(dtl_str: str, key: str) -> str:
    try:
        for item in json.loads(dtl_str):
            if item.get("key") == key:
                return item.get("value", "")
    except Exception:
        pass
    return ""


def _get_price_info(card) -> dict:
    """카드 요소에서 정가·판매가·할인율 추출"""
    sales_price   = ""
    regular_price = ""
    discount      = ""

    # 판매가: span[class*='priceTag_price__']
    try:
        el = card.find_element(By.CSS_SELECTOR, "[class*='priceTag_price__']")
        t  = re.sub(r"[^\d]", "", el.text)
        if t:
            sales_price = t
    except NoSuchElementException:
        pass

    # 정가: span[class*='original_price'] → "할인 전 판매가91,000원"
    try:
        el = card.find_element(By.CSS_SELECTOR, "[class*='original_price']")
        t  = re.sub(r"[^\d]", "", el.text)
        if t:
            regular_price = t
    except NoSuchElementException:
        pass

    # 할인율: 두 가격으로 직접 계산
    if regular_price and sales_price:
        try:
            v = round((int(regular_price) - int(sales_price)) / int(regular_price) * 100)
            if v > 0:
                discount = f"{v}%"
        except Exception:
            pass

    return {"sales_price": sales_price, "regular_price": regular_price, "discount": discount}


def collect_products(driver, limit: int = 24, sort_order: str | None = None) -> list:
    """
    상품 목록 수집
    sort_order: '신상품순' | None (기본값 None = 추천순)
    """
    wait = WebDriverWait(driver, 20)

    driver.get(CATEGORY_URL)
    time.sleep(5)
    wait.until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, "[class*='product_list'] li")))

    # 정렬 버튼 클릭 (sort_order 지정 시)
    if sort_order:
        try:
            sort_btn = driver.find_element(
                By.CSS_SELECTOR, f"button[data-shp-contents-id='{sort_order}']")
            driver.execute_script("arguments[0].click();", sort_btn)
            time.sleep(4)
            wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "[class*='product_list'] li")))
            print(f"  {sort_order} 정렬 적용")
        except Exception as e:
            print(f"  {sort_order} 버튼 오류: {e}")
    else:
        print("  추천순 (기본 정렬)")

    products = []
    for item in driver.find_elements(By.CSS_SELECTOR, "[class*='product_list'] li"):
        if len(products) >= limit:
            break
        try:
            a   = item.find_element(By.CSS_SELECTOR, "a[data-shp-contents-dtl]")
            dtl = a.get_attribute("data-shp-contents-dtl")

            name  = _parse_dtl(dtl, "prod_nm")
            price = _parse_dtl(dtl, "price")
            url   = a.get_attribute("href").split("?")[0]

            try:
                brand = item.find_element(
                    By.CSS_SELECTOR, "[class*='mall_name']"
                ).text.replace(" 스토어", "").strip()
            except NoSuchElementException:
                brand = ""

            price_info    = _get_price_info(item)
            sales_price   = price_info["sales_price"] or price
            regular_price = price_info["regular_price"]
            discount      = price_info["discount"]

            if name:
                products.append({
                    "product_name": name,
                    "brand":        brand,
                    "sales_price":  sales_price,
                    "regular_price": regular_price,
                    "discount":     discount,
                    "url":          url,
                })
        except Exception:
            continue

    print(f"  {len(products)}개 수집 완료")
    for i, p in enumerate(products, 1):
        disc_str = f" ({p['discount']})" if p['discount'] else ""
        print(f"  {i:>2}. {p['product_name'][:28]:<28} | {p['brand']:<12} | "
              f"{int(p['sales_price'] or 0):,}원{disc_str}")

    return products
