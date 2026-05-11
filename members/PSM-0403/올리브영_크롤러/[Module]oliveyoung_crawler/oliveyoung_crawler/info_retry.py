from __future__ import annotations

from pathlib import Path

import pandas as pd

from .browser import create_driver, safe_quit_driver
from .product_collector import (
    extract_main_ingredients_with_gpt_ocr,
    get_detail,
    parse_detail_image_urls,
)


def _find_latest_csv(data_dir: Path) -> Path | None:
    candidates = sorted(
        data_dir.glob("*.csv"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _resolve_csv_paths(target_csv, data_dir: Path) -> list[Path]:
    if target_csv is None:
        latest = _find_latest_csv(data_dir)
        return [latest] if latest else []
    if isinstance(target_csv, list):
        return [Path(p) for p in target_csv]
    return [Path(target_csv)]


def _find_retry_urls(df: pd.DataFrame, *, recrawl_all: bool) -> list[dict]:
    if recrawl_all:
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


def _process_csv(
    csv_path: Path,
    *,
    recrawl_all: bool,
    chrome_version: int,
    headless: bool,
) -> None:
    print(f"\n{'=' * 60}")
    print(f"[대상 CSV] {csv_path}")

    df = None
    for enc in ("utf-8-sig", "cp949", "euc-kr"):
        try:
            df = pd.read_csv(csv_path, encoding=enc)
            print(f"[인코딩] {enc}")
            break
        except UnicodeDecodeError:
            continue

    if df is None:
        print("[오류] CSV 인코딩을 자동으로 판별할 수 없습니다.")
        return

    print(f"[전체 행] {len(df)}개")

    if "main_ingredients" not in df.columns:
        print("[건너뜀] main_ingredients 컬럼이 없습니다.")
        return

    retry_products = _find_retry_urls(df, recrawl_all=recrawl_all)

    mode_label = "전체 재크롤링" if recrawl_all else "누락 상품만 재크롤링"
    if not retry_products:
        print(f"[완료] 재수집할 상품이 없습니다. ({mode_label})")
        return

    print(f"\n[재수집 대상] {len(retry_products)}개 상품  ({mode_label})")
    for p in retry_products:
        print(f"  - {p['product_name']}")

    driver = create_driver(chrome_version=chrome_version, headless=headless)

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

            url_mask = df["url"].astype(str).str.strip() == product_url
            df.loc[url_mask, "main_ingredients"] = main_ingredients
            filled_count = url_mask.sum()
            print(f"  [주성분] {main_ingredients!r}  ({filled_count}행 업데이트)")

            df.to_csv(csv_path, index=False, encoding="utf-8-sig")
            print(f"  [중간 저장] {csv_path.name}")

    finally:
        safe_quit_driver(driver)

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"\n[저장 완료] {csv_path} ({len(df)}행)")


def run_retry(
    *,
    target_csv=None,
    recrawl_all: bool = True,
    chrome_version: int = 147,
    headless: bool = False,
    data_dir: Path | None = None,
) -> None:
    """
    main_ingredients(주성분)을 재크롤링합니다.

    Args:
        target_csv: 재수집할 CSV 경로 (info / review 모두 가능).
                    None → Data/ 폴더에서 가장 최근 CSV 자동 선택.
                    Path 1개 또는 list[Path] 가능.
        recrawl_all: True → 주성분 유무 상관없이 모든 상품 재크롤링.
                     False → main_ingredients가 비어 있는 상품만 재크롤링.
        chrome_version: 크롬 버전.
        headless: True면 브라우저 창 없이 실행.
        data_dir: Data 폴더 경로. None이면 이 파일 기준 자동 결정.
    """
    if data_dir is None:
        data_dir = Path(__file__).parent.parent / "Data"

    csv_paths = _resolve_csv_paths(target_csv, data_dir)

    if not csv_paths:
        print("[오류] CSV 파일을 찾을 수 없습니다.")
        return

    for csv_path in csv_paths:
        if not csv_path.exists():
            print(f"[건너뜀] 파일 없음: {csv_path}")
            continue
        _process_csv(
            csv_path,
            recrawl_all=recrawl_all,
            chrome_version=chrome_version,
            headless=headless,
        )
