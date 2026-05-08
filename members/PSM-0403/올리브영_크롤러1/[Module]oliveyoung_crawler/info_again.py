"""
주성분(main_ingredients)을 재크롤링합니다.

info CSV와 review CSV 모두 처리합니다.
- info CSV  : 상품 1개 = 1행  → 해당 행만 업데이트
- review CSV: 상품 1개 = N행  → URL이 같은 모든 행에 동시에 업데이트

사용법:
  python info_again.py

동작 방식:
  RECRAWL_ALL = True  → 주성분 유무 상관없이 모든 상품 재크롤링
  RECRAWL_ALL = False → main_ingredients가 비어 있는 상품만 재크롤링
  1. TARGET_CSV 에서 대상 행을 찾습니다.
  2. URL 기준으로 중복 제거 후 상품별로 한 번만 상세 페이지를 방문합니다.
  3. GPT Vision OCR로 주요 성분 1~3개를 추출합니다.
  4. 같은 URL을 가진 모든 행에 주성분을 채우고 CSV를 덮어씁니다.
"""

import sys
from pathlib import Path

# ============================================================
# 설정
# ============================================================

# 재수집할 CSV 경로 (info / review 모두 가능)
# None          → Data/ 폴더에서 가장 최근 CSV 자동 선택
# 파일 1개      → Path("Data/oliveyoung_판매순(info)_260505.csv")
# 파일 여러 개  → [Path("Data/...csv"), Path("Data/...csv")]
TARGET_CSV = [Path("Data/oliveyoung_신상품순(info)_260502.csv"),
              Path("Data/oliveyoung_판매순(info)_260502.csv")
]
              
              
            

# True  → 주성분 유무 상관없이 모든 상품 재크롤링
# False → main_ingredients가 비어 있는 상품만 재크롤링
RECRAWL_ALL = True

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


def resolve_csv_paths(data_dir: Path) -> list[Path]:
    if TARGET_CSV is None:
        latest = find_latest_csv(data_dir)
        return [latest] if latest else []
    if isinstance(TARGET_CSV, list):
        return [Path(p) for p in TARGET_CSV]
    return [Path(TARGET_CSV)]


def find_retry_urls(df: pd.DataFrame) -> list[dict]:
    """
    RECRAWL_ALL=True  → 전체 상품(URL 기준 중복 제거)을 반환합니다.
    RECRAWL_ALL=False → main_ingredients가 비어 있는 상품만 반환합니다.
    review CSV는 같은 상품이 여러 행이므로 URL로 묶습니다.
    """
    if RECRAWL_ALL:
        target_df = df
    else:
        missing_mask = df["main_ingredients"].isna() | (
            df["main_ingredients"].astype(str).str.strip() == ""
        )
        target_df = df[missing_mask]

    seen_urls: set[str] = set()
    products: list[dict] = []

    for _, row in target_df.iterrows():
        url = str(row.get("url", "")).strip()
        if not url or url == "nan" or url in seen_urls:
            continue
        seen_urls.add(url)
        products.append({
            "url": url,
            "product_name": str(row.get("product_name", "")),
            "ingredients": str(row.get("ingredients", "")),
        })

    return products


def main() -> None:
    data_dir = Path(__file__).parent / "Data"
    csv_paths = resolve_csv_paths(data_dir)

    if not csv_paths:
        print("[오류] CSV 파일을 찾을 수 없습니다.")
        return

    for csv_path in csv_paths:
        if not csv_path.exists():
            print(f"[건너뜀] 파일 없음: {csv_path}")
            continue
        process_csv(csv_path)


def process_csv(csv_path: Path) -> None:
    print(f"\n{'=' * 60}")
    print(f"[대상 CSV] {csv_path}")

    for enc in ("utf-8-sig", "cp949", "euc-kr"):
        try:
            df = pd.read_csv(csv_path, encoding=enc)
            print(f"[인코딩] {enc}")
            break
        except UnicodeDecodeError:
            continue
    else:
        print("[오류] CSV 인코딩을 자동으로 판별할 수 없습니다.")
        return
    print(f"[전체 행] {len(df)}개")

    if "main_ingredients" not in df.columns:
        print("[건너뜀] main_ingredients 컬럼이 없습니다.")
        return

    retry_products = find_retry_urls(df)

    mode_label = "전체 재크롤링" if RECRAWL_ALL else "누락 상품만 재크롤링"
    if not retry_products:
        print(f"[완료] 재수집할 상품이 없습니다. ({mode_label})")
        return

    print(f"\n[재수집 대상] {len(retry_products)}개 상품  ({mode_label})")
    for p in retry_products:
        print(f"  - {p['product_name']}")

    driver = create_driver(chrome_version=CHROME_VERSION, headless=HEADLESS)

    try:
        for i, product in enumerate(retry_products, 1):
            product_name = product["product_name"]
            product_url = product["url"]
            ingredients_text = product["ingredients"]

            print(f"\n[{i}/{len(retry_products)}] {product_name}")

            detail = get_detail(driver, product_url)
            image_urls = parse_detail_image_urls(detail.get("상세이미지_URLS", "[]"))

            main_ingredients = extract_main_ingredients_with_gpt_ocr(
                product_name=product_name,
                image_urls=image_urls,
                ingredients_text=ingredients_text,
            )

            # URL이 같은 모든 행(리뷰 CSV의 경우 여러 행)에 동시에 채움
            url_mask = df["url"].astype(str).str.strip() == product_url
            df.loc[url_mask, "main_ingredients"] = main_ingredients
            filled_count = url_mask.sum()
            print(f"  [주성분] {main_ingredients!r}  ({filled_count}행 업데이트)")

            # 상품 하나 끝날 때마다 중간 저장
            df.to_csv(csv_path, index=False, encoding="utf-8-sig")
            print(f"  [중간 저장] {csv_path.name}")

    finally:
        safe_quit_driver(driver)

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"\n[저장 완료] {csv_path} ({len(df)}행)")


if __name__ == "__main__":
    main()
