"""
추천순 / 신상품순 에센스 크롤러 메인
실행: python main_.py
"""
import time, random
import pandas as pd
from datetime import datetime

from driver      import create_driver
from cookie      import load_cookies
from products    import collect_products
from reviews     import get_rating, get_reviews
from tags        import get_tags
from ingredients import get_ingredients, setup_interceptor

# ── 설정 ────────────────────────────────────────────────────────────
COLLECT_LIMIT  = 3    # 수집할 상품 수
REVIEW_LIMIT   = 10    # 상품당 리뷰 수
COOKIE_FILE    = "naver_cookies.pkl"
# 수집할 정렬 목록: None = 추천순(기본), "신상품순" 추가 가능
SORT_ORDERS    = [None, "신상품순"]
CRAWL_REVIEWS      = True   # 리뷰 크롤링 여부
CRAWL_TAGS         = False  # 태그 크롤링 여부
CRAWL_INGREDIENTS  = True   # 전성분 크롤링 여부 (시간 오래 걸림)

INFO_COLS = [
    "product_name", "brand",
    "regular_price", "discount", "sales_price",
    "rating", "review_count",
    "url", "ingredients",
    "ing_source", "tags", "tag_count", "crawled_at",
]
REVIEW_COLS = ["product_name", "review_count", "review_text", "url"]


def crawl_one_sort(driver, sort_order):
    label = sort_order if sort_order else "추천순"

    # ── Step 1: 상품 목록 수집 ────────────────────────────────────────
    print(f"\n[Step 1] 상품 목록 수집 ({label}, {COLLECT_LIMIT}개)")
    products = collect_products(driver, limit=COLLECT_LIMIT, sort_order=sort_order)

    # ── Step 2: 상품 상세 크롤링 ──────────────────────────────────────
    print(f"\n[Step 2] 상품 상세 크롤링 시작 (총 {len(products)}개)")

    for idx, p in enumerate(products, 1):
        name = p["product_name"][:35]
        print(f"\n  [{idx}/{len(products)}] {name}")
        driver.get(p["url"])
        time.sleep(random.uniform(4, 7))

        p["rating"] = get_rating(driver)

        if CRAWL_REVIEWS:
            review_count, review_texts = get_reviews(driver, REVIEW_LIMIT)
            p["review_count"] = review_count
            p["review_text"]   = " || ".join(review_texts)
        else:
            p["review_count"] = ""
            p["review_text"]  = ""

        if CRAWL_TAGS:
            tags          = get_tags(driver)
            p["tags"]      = " / ".join(tags)
            p["tag_count"] = len(tags)
        else:
            p["tags"]      = ""
            p["tag_count"] = 0

        if CRAWL_INGREDIENTS:
            ing, src         = get_ingredients(driver, p["url"])
            p["ingredients"] = ing
            p["ing_source"]  = src
        else:
            p["ingredients"] = ""
            p["ing_source"]  = ""

        p["crawled_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print(f"    평점: {p['rating'] or '?'} | "
              f"리뷰수: {p['review_count'] or '?'} | "
              f"태그: {p.get('tag_count', 0)}개")

    # ── 저장 ────────────────────────────────────────────────────────
    date_str   = datetime.now().strftime("%y%m%d")
    df_all     = pd.DataFrame(products)

    info_csv   = f"naver_{label}(info)_{date_str}.csv"
    review_csv = f"naver_{label}(review)_{date_str}.csv"

    df_all[INFO_COLS].to_csv(info_csv,   index=False, encoding="utf-8-sig")
    df_all[REVIEW_COLS].to_csv(review_csv, index=False, encoding="utf-8-sig")

    print(f"\n✅ 저장 완료 → {info_csv} / {review_csv} ({len(df_all)}개)")
    print(df_all[["product_name", "brand", "regular_price", "discount", "sales_price", "rating"]].to_string())


def main():
    driver, _ = create_driver()
    setup_interceptor(driver)
    load_cookies(driver, COOKIE_FILE)

    for sort_order in SORT_ORDERS:
        crawl_one_sort(driver, sort_order)

    driver.quit()


if __name__ == "__main__":
    main()
