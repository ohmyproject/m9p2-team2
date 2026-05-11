"""
수정본 CSV를 SQLite DB에 적재하는 스크립트입니다.

이번 v3의 핵심:
1. Data 폴더에 원본 CSV와 _cleaned.csv가 같이 있으면 _cleaned.csv만 사용합니다.
2. goodsNo 컬럼을 우선 사용하고, 없으면 url에서 goodsNo를 추출합니다.
3. product_name_clean 컬럼이 있으면 화면 표시용 상품명으로 사용합니다.
4. rank는 product_rankings에 따로 저장합니다.
5. 이미 들어간 데이터는 UNIQUE + ON CONFLICT / INSERT OR IGNORE로 중복 저장하지 않습니다.

사용 예시:
python import_products_to_db.py --data-dir Data --db-path db/oliveyoung.sqlite --reset
python import_products_to_db.py --data-dir Data --db-path db/oliveyoung.sqlite
"""

from __future__ import annotations

import argparse
import math
import re
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from schema import connect_db, create_tables, reset_tables


GOODS_NO_RE = re.compile(r"goodsNo=([^&]+)")


def is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    text = str(value).strip()
    return text == "" or text.lower() in {"nan", "none", "null"}


def clean_text(value: Any) -> str | None:
    if is_empty(value):
        return None
    return str(value).strip()


def to_int(value: Any) -> int | None:
    if is_empty(value):
        return None
    text = str(value).replace(",", "").replace("원", "").strip()
    try:
        return int(float(text))
    except ValueError:
        return None


def to_float(value: Any) -> float | None:
    if is_empty(value):
        return None
    text = str(value).replace(",", "").strip()
    try:
        return float(text)
    except ValueError:
        return None


def extract_goods_no(row: pd.Series) -> str | None:
    goods_no = clean_text(row.get("goodsNo")) or clean_text(row.get("goods_no"))
    if goods_no:
        return goods_no
    url = clean_text(row.get("url"))
    if not url:
        return None
    match = GOODS_NO_RE.search(url)
    return match.group(1) if match else None


def split_by_comma_outside_parentheses(value: Any) -> list[str]:
    """
    쉼표 기준으로 분리하되 괄호 안의 쉼표는 자르지 않습니다.

    예:
    히알루론산(소듐하이알루로네이트, 하이알루로닉애씨드), 판테놀
    -> [히알루론산(...), 판테놀]
    """
    if is_empty(value):
        return []

    text = str(value).strip()
    result: list[str] = []
    buf: list[str] = []
    depth = 0

    for ch in text:
        if ch in "(（":
            depth += 1
            buf.append(ch)
        elif ch in ")）":
            depth = max(depth - 1, 0)
            buf.append(ch)
        elif ch == "," and depth == 0:
            part = "".join(buf).strip()
            if part:
                result.append(part)
            buf = []
        else:
            buf.append(ch)

    last = "".join(buf).strip()
    if last:
        result.append(last)

    deduped: list[str] = []
    seen: set[str] = set()
    for part in result:
        if part.lower() in {"nan", "none", "null"}:
            continue
        if part not in seen:
            deduped.append(part)
            seen.add(part)
    return deduped


def choose_product_csv_files(data_dir: Path) -> list[Path]:
    """
    상품 CSV만 고릅니다.

    이번 수정본에는 같은 날짜/정렬에 대해 아래 두 파일이 같이 있습니다.
    - oliveyoung_...(info)_260501.csv
    - oliveyoung_...(info)_260501_cleaned.csv

    DB에는 cleaned 파일만 넣어야 합니다.
    그래야 product_name_clean, main_ingredients_kor를 반영하고
    원본/cleaned 중복 적재를 막을 수 있습니다.
    """
    csv_files = sorted(data_dir.glob("*.csv"))
    product_files = [p for p in csv_files if "(info)" in p.name]

    chosen: dict[str, tuple[int, Path]] = {}
    for path in product_files:
        name = path.name
        key = re.sub(r"_cleaned(?=\.csv$)", "", name)
        key = re.sub(r"_ingredients_kor(?=\.csv$)", "", key)

        # 우선순위: cleaned > ingredients_kor > 일반 csv
        priority = 0
        if "_ingredients_kor" in name:
            priority = 1
        if "_cleaned" in name:
            priority = 2

        current = chosen.get(key)
        if current is None or priority > current[0]:
            chosen[key] = (priority, path)

    return sorted(path for _, path in chosen.values())


def upsert_product(conn: sqlite3.Connection, row: pd.Series, goods_no: str) -> None:
    collected_date = clean_text(row.get("date"))
    product_name_raw = clean_text(row.get("product_name"))
    product_name_clean = clean_text(row.get("product_name_clean"))
    display_name = product_name_clean or product_name_raw or "상품명 없음"

    conn.execute(
        """
        INSERT INTO products (
            goods_no, brand, product_name, product_name_raw, product_name_clean,
            volume_ml, url, first_collected_date, last_collected_date
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(goods_no) DO UPDATE SET
            brand = COALESCE(excluded.brand, products.brand),
            product_name = COALESCE(excluded.product_name, products.product_name),
            product_name_raw = COALESCE(excluded.product_name_raw, products.product_name_raw),
            product_name_clean = COALESCE(excluded.product_name_clean, products.product_name_clean),
            volume_ml = COALESCE(excluded.volume_ml, products.volume_ml),
            url = COALESCE(excluded.url, products.url),
            first_collected_date = CASE
                WHEN products.first_collected_date IS NULL THEN excluded.first_collected_date
                WHEN excluded.first_collected_date IS NULL THEN products.first_collected_date
                WHEN excluded.first_collected_date < products.first_collected_date THEN excluded.first_collected_date
                ELSE products.first_collected_date
            END,
            last_collected_date = CASE
                WHEN products.last_collected_date IS NULL THEN excluded.last_collected_date
                WHEN excluded.last_collected_date IS NULL THEN products.last_collected_date
                WHEN excluded.last_collected_date > products.last_collected_date THEN excluded.last_collected_date
                ELSE products.last_collected_date
            END,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            goods_no,
            clean_text(row.get("brand")),
            display_name,
            product_name_raw,
            product_name_clean,
            clean_text(row.get("volume_ml")),
            clean_text(row.get("url")),
            collected_date,
            collected_date,
        ),
    )


def upsert_snapshot(conn: sqlite3.Connection, row: pd.Series, goods_no: str) -> None:
    conn.execute(
        """
        INSERT INTO product_snapshots (
            goods_no, collected_date, platform,
            regular_price, discount, sales_price, rating, review_count
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(goods_no, collected_date, platform) DO UPDATE SET
            regular_price = COALESCE(excluded.regular_price, product_snapshots.regular_price),
            discount = COALESCE(excluded.discount, product_snapshots.discount),
            sales_price = COALESCE(excluded.sales_price, product_snapshots.sales_price),
            rating = COALESCE(excluded.rating, product_snapshots.rating),
            review_count = COALESCE(excluded.review_count, product_snapshots.review_count),
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            goods_no,
            clean_text(row.get("date")),
            clean_text(row.get("platform")) or "oliveyoung",
            to_int(row.get("regular_price")),
            clean_text(row.get("discount")),
            to_int(row.get("sales_price")),
            to_float(row.get("rating")),
            to_int(row.get("review_count")),
        ),
    )


def upsert_ranking(conn: sqlite3.Connection, row: pd.Series, goods_no: str) -> None:
    sort_type = clean_text(row.get("sort_type"))
    if not sort_type:
        return
    conn.execute(
        """
        INSERT INTO product_rankings (
            goods_no, collected_date, platform, sort_type, rank
        )
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(goods_no, collected_date, platform, sort_type) DO UPDATE SET
            rank = COALESCE(excluded.rank, product_rankings.rank),
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            goods_no,
            clean_text(row.get("date")),
            clean_text(row.get("platform")) or "oliveyoung",
            sort_type,
            to_int(row.get("rank")),
        ),
    )


def insert_main_ingredients(conn: sqlite3.Connection, row: pd.Series, goods_no: str) -> int:
    # 한글 주성분이 있으면 그것을 우선 사용합니다.
    source_column = None
    main_value = None
    for col in ["main_ingredients_kor", "main_ingredients_simple", "main_ingredients"]:
        if col in row.index and not is_empty(row.get(col)):
            source_column = col
            main_value = row.get(col)
            break

    count = 0
    for order, ingredient in enumerate(split_by_comma_outside_parentheses(main_value), start=1):
        before = conn.total_changes
        conn.execute(
            """
            INSERT OR IGNORE INTO product_main_ingredients (
                goods_no, ingredient_order, ingredient_name, source_column
            )
            VALUES (?, ?, ?, ?)
            """,
            (goods_no, order, ingredient, source_column),
        )
        if conn.total_changes > before:
            count += 1
    return count


def insert_full_ingredients(conn: sqlite3.Connection, row: pd.Series, goods_no: str) -> int:
    count = 0
    ing_source = clean_text(row.get("ing_source"))
    for order, ingredient in enumerate(split_by_comma_outside_parentheses(row.get("ingredients")), start=1):
        before = conn.total_changes
        conn.execute(
            """
            INSERT OR IGNORE INTO product_full_ingredients (
                goods_no, ingredient_order, ingredient_name, ing_source
            )
            VALUES (?, ?, ?, ?)
            """,
            (goods_no, order, ingredient, ing_source),
        )
        if conn.total_changes > before:
            count += 1
    return count


def count_rows(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def import_products(data_dir: Path, db_path: Path, reset: bool = False) -> None:
    conn = connect_db(db_path)
    if reset:
        reset_tables(conn)
    else:
        create_tables(conn)

    files = choose_product_csv_files(data_dir)
    if not files:
        raise FileNotFoundError(f"상품 CSV를 찾지 못했습니다: {data_dir}")

    before_counts = {
        table: count_rows(conn, table)
        for table in [
            "products",
            "product_snapshots",
            "product_rankings",
            "product_main_ingredients",
            "product_full_ingredients",
            "product_reviews",
        ]
    }

    processed_rows = 0
    skipped_rows = 0
    inserted_main = 0
    inserted_full = 0

    print("[선택된 상품 CSV]")
    for path in files:
        print(f"- {path.name}")

    for path in files:
        df = pd.read_csv(path, encoding="utf-8-sig")
        print(f"\n[CSV 처리] {path.name} / {len(df)}행")

        for _, row in df.iterrows():
            goods_no = extract_goods_no(row)
            if not goods_no:
                skipped_rows += 1
                continue

            upsert_product(conn, row, goods_no)
            upsert_snapshot(conn, row, goods_no)
            upsert_ranking(conn, row, goods_no)
            inserted_main += insert_main_ingredients(conn, row, goods_no)
            inserted_full += insert_full_ingredients(conn, row, goods_no)
            processed_rows += 1

    conn.commit()

    after_counts = {table: count_rows(conn, table) for table in before_counts}
    conn.close()

    print("\n[DB 적재 완료]")
    print(f"사용한 상품 CSV 파일 수: {len(files)}")
    print(f"처리한 상품 행 수: {processed_rows}")
    print(f"goodsNo 없어서 건너뛴 행 수: {skipped_rows}")
    print(f"이번 실행에서 새로 추가된 주성분 행 수: {inserted_main}")
    print(f"이번 실행에서 새로 추가된 전성분 행 수: {inserted_full}")
    print(f"DB 경로: {db_path}")
    print("\n[테이블별 행 수 변화]")
    for table in before_counts:
        print(f"{table}: {before_counts[table]} -> {after_counts[table]} (+{after_counts[table] - before_counts[table]})")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="Data", help="CSV가 들어있는 Data 폴더 경로")
    parser.add_argument("--db-path", default="db/oliveyoung.sqlite", help="생성할 SQLite DB 경로")
    parser.add_argument("--reset", action="store_true", help="기존 테이블을 삭제하고 처음부터 다시 적재")
    args = parser.parse_args()

    import_products(Path(args.data_dir), Path(args.db_path), reset=args.reset)


if __name__ == "__main__":
    main()
