from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date as _date
from pathlib import Path

from .browser import create_driver, safe_quit_driver
from .review_collector import collect_reviews_for_product, save_review_rows


def _find_latest_review_csv(data_dir: Path) -> Path | None:
    candidates = sorted(
        data_dir.glob("*review*.csv"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _is_failed_row(row: dict[str, str]) -> bool:
    return "리뷰 수집 실패" in row.get("review_text", "")


def _find_retry_products(
    rows: list[dict[str, str]],
    target: int,
) -> list[dict[str, str]]:
    url_to_rows: defaultdict[str, list] = defaultdict(list)
    for row in rows:
        url_to_rows[row["url"]].append(row)

    retry: list[dict[str, str]] = []
    for url, product_rows in url_to_rows.items():
        valid = [r for r in product_rows if not _is_failed_row(r)]
        if len(valid) < target:
            ref = product_rows[0]
            retry.append({
                "url":              url,
                "product_name":     ref.get("product_name", ""),
                "review_count":     ref.get("review_count", ""),
                "sort_type":        ref.get("sort_type", ""),
                "main_ingredients": ref.get("main_ingredients", ""),
                "already":          len(valid),
            })

    return retry


def _resolve_csv_paths(
    review_csv,
    data_dir: Path,
) -> list[Path]:
    if review_csv is None:
        latest = _find_latest_review_csv(data_dir)
        return [latest] if latest else []
    if isinstance(review_csv, list):
        return [Path(p) for p in review_csv]
    return [Path(review_csv)]


def _process_csv(
    csv_path: Path,
    *,
    target: int,
    chrome_version: int,
    headless: bool,
) -> None:
    print(f"\n{'=' * 60}")
    print(f"[대상 CSV] {csv_path}")

    rows = _read_csv(csv_path)
    print(f"[전체 행] {len(rows)}개")

    retry_products = _find_retry_products(rows, target)

    if not retry_products:
        print("[완료] 재수집이 필요한 상품이 없습니다.")
        return

    print(f"\n[재수집 대상] {len(retry_products)}개 상품")
    for p in retry_products:
        print(f"  - {p['product_name']} | 현재 {p['already']}개 / 목표 {target}개")

    today = _date.today().strftime("%Y-%m-%d")
    driver = create_driver(chrome_version=chrome_version, headless=headless)
    new_rows: dict[str, list[dict[str, str]]] = {}

    try:
        for i, product in enumerate(retry_products, 1):
            print(f"\n[{i}/{len(retry_products)}] {product['product_name']}")

            collected = collect_reviews_for_product(
                driver,
                product,
                limit=target,
                access_check_timeout_seconds=300,
                today=today,
            )
            new_rows[product["url"]] = collected

            retry_urls_done = set(new_rows.keys())
            kept = [r for r in rows if r["url"] not in retry_urls_done]
            merged = kept + [row for rows_list in new_rows.values() for row in rows_list]
            save_review_rows(merged, csv_path)
            print(f"  [중간 저장] {csv_path.name}")

    finally:
        safe_quit_driver(driver)

    retry_urls_all = {p["url"] for p in retry_products}
    kept_final = [r for r in rows if r["url"] not in retry_urls_all]
    final = kept_final + [row for rows_list in new_rows.values() for row in rows_list]
    save_review_rows(final, csv_path)
    print(f"\n[저장 완료] {csv_path} ({len(final)}행)")


def run_retry(
    *,
    review_csv=None,
    target: int = 10,
    chrome_version: int = 147,
    headless: bool = False,
    data_dir: Path | None = None,
) -> None:
    """
    리뷰 수집에 실패했거나 목표치보다 적게 수집된 상품들을 재수집합니다.

    Args:
        review_csv: 재수집할 리뷰 CSV 경로.
                    None → Data/ 폴더에서 가장 최근 review CSV 자동 선택.
                    Path 1개 또는 list[Path] 가능.
        target: 상품당 목표 리뷰 수.
        chrome_version: 크롬 버전.
        headless: True면 브라우저 창 없이 실행.
        data_dir: Data 폴더 경로. None이면 이 파일 기준 자동 결정.
    """
    if data_dir is None:
        data_dir = Path(__file__).parent.parent / "Data"

    csv_paths = _resolve_csv_paths(review_csv, data_dir)

    if not csv_paths:
        print("[오류] 리뷰 CSV 파일을 찾을 수 없습니다.")
        return

    for csv_path in csv_paths:
        if not csv_path.exists():
            print(f"[건너뜀] 파일 없음: {csv_path}")
            continue
        _process_csv(
            csv_path,
            target=target,
            chrome_version=chrome_version,
            headless=headless,
        )
