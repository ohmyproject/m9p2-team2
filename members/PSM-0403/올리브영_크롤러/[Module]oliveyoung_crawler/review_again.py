"""
리뷰 수집에 실패했거나 목표치보다 적게 수집된 상품들을 재수집합니다.

사용법:
  python review_again.py

동작 방식:
  1. REVIEW_CSV 에서 상품별 리뷰 현황을 분석합니다.
  2. 실패 행("리뷰 수집 실패")만 있거나 TARGET보다 적은 상품을 추립니다.
  3. 해당 상품들만 재수집합니다.
  4. 기존 CSV에서 실패 행을 제거하고 새 리뷰를 합쳐 덮어씁니다.
"""

import csv
import sys
from collections import defaultdict
from datetime import date as _date
from pathlib import Path

# ============================================================
# 설정
# ============================================================

# 재수집할 리뷰 CSV 경로
# None          → Data/ 폴더에서 가장 최근 review CSV 자동 선택
# 파일 1개      → Path("Data/oliveyoung_판매순(review)_260503.csv")
# 파일 여러 개  → [Path("Data/...csv"), Path("Data/...csv")]
REVIEW_CSV = [
    Path("Data/oliveyoung_신상품순(review)_260501.csv")
]

# 상품당 목표 리뷰 수
TARGET         = 10

# 크롬 설정
CHROME_VERSION = 147
HEADLESS       = False

# ============================================================

sys.path.insert(0, str(Path(__file__).parent))

from oliveyoung_crawler.browser import create_driver, safe_quit_driver
from oliveyoung_crawler.review_collector import (
    collect_reviews_for_product,
    save_review_rows,
)


def find_latest_review_csv(data_dir: Path) -> Path | None:
    candidates = sorted(
        data_dir.glob("*review*.csv"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def is_failed_row(row: dict[str, str]) -> bool:
    return "리뷰 수집 실패" in row.get("review_text", "")


def find_retry_products(
    rows: list[dict[str, str]],
    target: int,
) -> list[dict[str, str]]:
    """재수집이 필요한 상품 목록을 반환합니다."""
    url_to_rows: defaultdict[str, list] = defaultdict(list)
    for row in rows:
        url_to_rows[row["url"]].append(row)

    retry: list[dict[str, str]] = []
    for url, product_rows in url_to_rows.items():
        valid = [r for r in product_rows if not is_failed_row(r)]
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


def resolve_csv_paths(data_dir: Path) -> list[Path]:
    """REVIEW_CSV 설정에서 처리할 파일 목록을 반환합니다."""
    if REVIEW_CSV is None:
        latest = find_latest_review_csv(data_dir)
        return [latest] if latest else []
    if isinstance(REVIEW_CSV, list):
        return [Path(p) for p in REVIEW_CSV]
    return [Path(REVIEW_CSV)]


def main() -> None:
    data_dir = Path(__file__).parent / "Data"

    csv_paths = resolve_csv_paths(data_dir)
    if not csv_paths:
        print("[오류] 리뷰 CSV 파일을 찾을 수 없습니다.")
        return

    for csv_path in csv_paths:
        if not csv_path.exists():
            print(f"[건너뜀] 파일 없음: {csv_path}")
            continue
        process_csv(csv_path)


def process_csv(csv_path: Path) -> None:
    print(f"\n{'=' * 60}")
    print(f"[대상 CSV] {csv_path}")

    rows = read_csv(csv_path)
    print(f"[전체 행] {len(rows)}개")

    retry_products = find_retry_products(rows, TARGET)

    if not retry_products:
        print("[완료] 재수집이 필요한 상품이 없습니다.")
        return

    print(f"\n[재수집 대상] {len(retry_products)}개 상품")
    for p in retry_products:
        print(f"  - {p['product_name']} | 현재 {p['already']}개 / 목표 {TARGET}개")

    today = _date.today().strftime("%Y-%m-%d")
    driver = create_driver(chrome_version=CHROME_VERSION, headless=HEADLESS)
    new_rows: dict[str, list[dict[str, str]]] = {}

    try:
        for i, product in enumerate(retry_products, 1):
            print(f"\n[{i}/{len(retry_products)}] {product['product_name']}")

            collected = collect_reviews_for_product(
                driver,
                product,
                limit=TARGET,
                access_check_timeout_seconds=300,
                today=today,
            )
            new_rows[product["url"]] = collected

            # 상품 하나 끝날 때마다 중간 저장
            retry_urls_done = set(new_rows.keys())
            kept = [r for r in rows if r["url"] not in retry_urls_done]
            merged = kept + [row for rows_list in new_rows.values() for row in rows_list]
            save_review_rows(merged, csv_path)
            print(f"  [중간 저장] {csv_path.name}")

    finally:
        safe_quit_driver(driver)

    # 최종 저장: 기존 성공 행 + 새로 수집한 행
    retry_urls_all = {p["url"] for p in retry_products}
    kept_final = [r for r in rows if r["url"] not in retry_urls_all]
    final = kept_final + [row for rows_list in new_rows.values() for row in rows_list]
    save_review_rows(final, csv_path)
    print(f"\n[저장 완료] {csv_path} ({len(final)}행)")


if __name__ == "__main__":
    main()
