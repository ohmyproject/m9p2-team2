"""
기존 CSV의 주성분(main_ingredients)과 새로 재크롤링한 주성분을 비교하는 CSV를 만듭니다.

기존 CSV는 수정하지 않습니다.
출력: Data/compare_ingredients_YYYYMMDD_HHMMSS.csv
  - product_name
  - url
  - old_main_ingredients  (기존 CSV 값)
  - new_main_ingredients  (지금 재크롤링한 값)

사용법:
  python compare_ingredients.py
"""

import sys
from datetime import datetime
from pathlib import Path

# ============================================================
# 설정
# ============================================================

# 비교할 CSV 경로
# None       → Data/ 폴더에서 가장 최근 CSV 자동 선택
# 직접 지정  → Path("Data/oliveyoung_판매순(info)_260505.csv")
TARGET_CSV = Path("Data/oliveyoung_신상품순(info)_260501.csv")

# 비교할 상품 수 제한 (None → 전체)
LIMIT = 5
              

# 크롬 설정
CHROME_VERSION = 147
HEADLESS = False

# ============================================================

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd

from oliveyoung_crawler.browser import create_driver, safe_quit_driver
from oliveyoung_crawler.product_collector import (
    extract_main_ingredients_with_gpt_ocr,
    get_detail,
    parse_detail_image_urls,
)


def find_latest_csv(data_dir: Path) -> Path | None:
    candidates = sorted(
        data_dir.glob("*.csv"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def main() -> None:
    data_dir = Path(__file__).parent / "Data"

    csv_path = Path(TARGET_CSV) if TARGET_CSV else find_latest_csv(data_dir)

    if not csv_path or not csv_path.exists():
        print("[오류] CSV 파일을 찾을 수 없습니다.")
        return

    print(f"[대상 CSV] {csv_path}")

    for enc in ("utf-8-sig", "cp949", "euc-kr"):
        try:
            df = pd.read_csv(csv_path, encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        print("[오류] CSV 인코딩을 읽을 수 없습니다.")
        return

    required = {"product_name", "url", "main_ingredients"}
    if not required.issubset(df.columns):
        missing = required - set(df.columns)
        print(f"[오류] 필수 컬럼 없음: {missing}")
        return

    # URL 기준으로 중복 제거
    seen_urls: set[str] = set()
    products: list[dict] = []

    for _, row in df.iterrows():
        url = str(row.get("url", "")).strip()
        if not url or url == "nan" or url in seen_urls:
            continue
        seen_urls.add(url)
        products.append({
            "product_name": str(row.get("product_name", "")),
            "url": url,
            "old_main_ingredients": str(row.get("main_ingredients", "") or ""),
            "ingredients": str(row.get("ingredients", "") or ""),
        })

    if LIMIT:
        products = products[:LIMIT]

    print(f"[대상 상품] {len(products)}개")

    results: list[dict] = []
    driver = create_driver(chrome_version=CHROME_VERSION, headless=HEADLESS)

    try:
        for i, product in enumerate(products, 1):
            product_name = product["product_name"]
            product_url = product["url"]
            old_val = product["old_main_ingredients"]
            ingredients_text = product["ingredients"]

            print(f"\n[{i}/{len(products)}] {product_name}")
            print(f"  [기존] {old_val!r}")

            detail = get_detail(driver, product_url)
            image_urls = parse_detail_image_urls(detail.get("상세이미지_URLS", "[]"))
            print(f"  [이미지] {len(image_urls)}개")
            for j, url in enumerate(image_urls, 1):
                print(f"    {j}. {url}")

            try:
                new_val = extract_main_ingredients_with_gpt_ocr(
                    product_name=product_name,
                    image_urls=image_urls,
                    ingredients_text=ingredients_text,
                )
            except Exception as e:
                print(f"  [GPT 오류] {e}")
                new_val = ""

            print(f"  [신규] {new_val!r}")

            results.append({
                "product_name": product_name,
                "url": product_url,
                "old_main_ingredients": old_val,
                "new_main_ingredients": new_val,
            })

    finally:
        safe_quit_driver(driver)

    out_df = pd.DataFrame(results, columns=["product_name", "url", "old_main_ingredients", "new_main_ingredients"])

    timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
    out_path = data_dir / f"compare_ingredients_{timestamp}.csv"
    out_df.to_csv(out_path, index=False, encoding="utf-8-sig")

    print(f"\n[저장 완료] {out_path} ({len(out_df)}행)")


if __name__ == "__main__":
    main()
