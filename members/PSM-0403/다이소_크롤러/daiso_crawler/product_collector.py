from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
from playwright.sync_api import Page

from .browser import create_browser, create_page, safe_close, start_playwright
from .category import collect_product_links_from_config
from .common import make_output_path
from .config import SORT_MAP, DaisoCrawlConfig
from .ocr import extract_main_ingredients_gpt, get_ingredients, setup_tesseract
from .product_parser import fetch_desc_images, parse_detail_page, parse_main_ingredients


# ============================================================
# product_collector.py
# ------------------------------------------------------------
# 역할:
# - 카테고리 → 상품 링크 수집 → 상세 페이지 수집 → OCR 전성분 추출
# - 정렬별 CSV 저장
# ============================================================


CHECKPOINT_EVERY = 5  # 상품 N개마다 체크포인트 저장


def _checkpoint_path(save_path: Path) -> Path:
    return save_path.parent / f"_ckpt_{save_path.name}"


PRODUCT_INFO_COLUMNS = [
    "date",
    "platform",
    "sort_type",
    "rank",
    "product_name",
    "brand",
    "volume_ml",
    "regular_price",
    "discount",
    "sales_price",
    "rating",
    "review_count",
    "main_ingredients",
    "ingredients",
    "ing_source",
    "url",
]


def _save_csv(results: list[dict], path: Path) -> None:
    df = pd.DataFrame(results, columns=PRODUCT_INFO_COLUMNS)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def collect_sort_products(
    page: Page,
    *,
    sort_key: str,
    config: DaisoCrawlConfig,
) -> Path | None:
    """
    특정 정렬 기준 하나에 대해 상품 목록과 상세 정보를 수집합니다.

    흐름:
    1. 카테고리 페이지에서 상품 링크(pdNo) 수집
    2. 각 상품 상세 페이지에서 이름/가격/평점/용량 수집
    3. API로 상세 설명 이미지 가져오기 → OCR로 전성분 추출
    4. 상품마다 중간 저장
    """
    from datetime import date as _date

    _, _, sort_name = SORT_MAP[sort_key]

    print("=" * 60)
    print(f"▶ [{sort_name}] 상품 수집 시작")
    print("=" * 60)

    links = collect_product_links_from_config(page, config, sort_key=sort_key)

    if not links:
        print(f"[{sort_name}] 수집된 상품이 없습니다.")
        return None

    today = _date.today().strftime("%Y-%m-%d")
    save_path = make_output_path(config.output_dir, "info", sort_key)
    ckpt_path = _checkpoint_path(save_path)

    results: list[dict] = []
    done_urls: set[str] = set()

    if ckpt_path.exists():
        print(f"  [체크포인트 발견] {ckpt_path.name} — 이어서 수집합니다.")
        df_ckpt = pd.read_csv(ckpt_path, encoding="utf-8-sig")
        results = df_ckpt.to_dict("records")
        done_urls = {str(r["url"]) for r in results}

    for item in links:
        rank = int(item["rank"])
        pd_no = str(item["pdNo"])
        url = str(item["url"])

        if url in done_urls:
            print(f"\n[{rank}/{len(links)}] 건너뜀 (이미 수집): {pd_no}")
            continue

        print(f"\n[{rank}/{len(links)}] pdNo={pd_no}")

        product_info: dict[str, str] = {
            "product_name": "",
            "brand": "",
            "regular_price": "",
            "discount": "",
            "sales_price": "",
            "rating": "",
            "review_count": "",
            "volume_ml": "",
        }

        main_ingredients = ""
        ingredients = ""
        ing_source = ""

        try:
            product_info = parse_detail_page(
                page,
                url,
                detail_delay_ms=config.detail_delay_ms,
            )
            print(f"  제품명: {product_info['product_name']}")
            print(f"  용량:   {product_info['volume_ml']}")
            print(f"  가격:   {product_info['regular_price']}")
            print(f"  평점:   {product_info['rating']}")
            print(f"  리뷰수: {product_info['review_count']}")

            # 주요성분 HTML 우선 추출
            main_ingredients = parse_main_ingredients(page)
            if main_ingredients:
                print(f"  핵심성분(HTML): {main_ingredients}")

        except Exception as e:
            print(f"  [상세 정보 실패] {str(e)[:80]}")

        try:
            desc_images = fetch_desc_images(pd_no)

            # HTML에서 못 가져왔으면 GPT 폴백
            if not main_ingredients and config.openai_api_key:
                main_ingredients = extract_main_ingredients_gpt(
                    desc_images, config.openai_api_key
                )
                print(f"  핵심성분(GPT): {main_ingredients}")

            ingredients, ing_source = get_ingredients(desc_images)
            print(f"  전성분 일부: {ingredients[:80]}")

        except Exception as e:
            print(f"  [전성분 실패] {str(e)[:80]}")
            ing_source = "OCR_FAIL"

        results.append({
            "date": today,
            "platform": "daiso",
            "sort_type": sort_name,
            "rank": rank,
            "product_name": product_info.get("product_name", ""),
            "brand": product_info.get("brand", ""),
            "volume_ml": product_info.get("volume_ml", ""),
            "regular_price": product_info.get("regular_price", ""),
            "discount": product_info.get("discount", ""),
            "sales_price": product_info.get("sales_price", ""),
            "rating": product_info.get("rating", ""),
            "review_count": product_info.get("review_count", ""),
            "main_ingredients": main_ingredients,
            "ingredients": ingredients,
            "ing_source": ing_source,
            "url": url,
        })

        if len(results) % CHECKPOINT_EVERY == 0:
            _save_csv(results, ckpt_path)
            print(f"  [체크포인트] {len(results)}개 저장 → {ckpt_path.name}")

        time.sleep(0.5)

    _save_csv(results, save_path)
    if ckpt_path.exists():
        ckpt_path.unlink()
    print(f"\n[{sort_name}] 수집 완료: {save_path}")

    return save_path


def run(config: DaisoCrawlConfig) -> list[Path]:
    """
    상품 수집 전체 실행 함수입니다.

    흐름:
    1. Tesseract 경로 설정
    2. 브라우저 시작
    3. 정렬별 상품 수집
    4. 브라우저 종료
    """
    setup_tesseract(config.tesseract_cmd)

    playwright = start_playwright()
    browser = create_browser(playwright, headless=config.headless)
    page = create_page(browser)

    saved_paths: list[Path] = []

    try:
        for sort_key in [s.strip() for s in config.sort.split(",") if s.strip()]:
            if sort_key not in SORT_MAP:
                print(f"[경고] 지원하지 않는 정렬 키: {sort_key}")
                continue

            path = collect_sort_products(page, sort_key=sort_key, config=config)

            if path:
                saved_paths.append(path)

    finally:
        safe_close(browser, playwright)

    print("\n모든 정렬에서 상품 수집 완료!")

    return saved_paths
