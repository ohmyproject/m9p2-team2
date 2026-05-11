from __future__ import annotations

import argparse
from pathlib import Path

from schema import connect_db, create_tables


def print_rows(title: str, rows) -> None:
    print(f"\n[{title}]")
    for row in rows:
        print(dict(row))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path", default="db/oliveyoung.sqlite")
    args = parser.parse_args()

    conn = connect_db(Path(args.db_path))
    create_tables(conn)

    tables = [
        "products",
        "product_snapshots",
        "product_rankings",
        "product_main_ingredients",
        "product_full_ingredients",
        "product_reviews",
    ]

    print("[테이블별 행 수]")
    for table in tables:
        count = conn.execute(f"SELECT COUNT(*) AS cnt FROM {table}").fetchone()["cnt"]
        print(f"{table}: {count}")

    print_rows(
        "상품 예시 5개",
        conn.execute(
            """
            SELECT goods_no, brand, product_name, product_name_raw, product_name_clean, volume_ml, first_collected_date, last_collected_date
            FROM products
            ORDER BY last_collected_date DESC, goods_no
            LIMIT 5
            """
        ).fetchall(),
    )

    print_rows(
        "랭킹 변화 예시: 날짜별/정렬별 rank",
        conn.execute(
            """
            SELECT p.brand, p.product_name, r.goods_no, r.collected_date, r.sort_type, r.rank
            FROM product_rankings r
            JOIN products p ON p.goods_no = r.goods_no
            ORDER BY r.goods_no, r.sort_type, r.collected_date
            LIMIT 20
            """
        ).fetchall(),
    )

    print_rows(
        "같은 상품이 여러 날짜에 랭킹을 가진 예시",
        conn.execute(
            """
            SELECT p.brand, p.product_name, r.goods_no, r.sort_type,
                   COUNT(*) AS ranking_rows,
                   GROUP_CONCAT(r.collected_date || ':' || r.rank, ' / ') AS date_rank_list
            FROM product_rankings r
            JOIN products p ON p.goods_no = r.goods_no
            GROUP BY r.goods_no, r.sort_type
            HAVING COUNT(*) >= 2
            ORDER BY ranking_rows DESC
            LIMIT 10
            """
        ).fetchall(),
    )

    print_rows(
        "중복 검사용: snapshots 중복 여부",
        conn.execute(
            """
            SELECT goods_no, collected_date, platform, COUNT(*) AS cnt
            FROM product_snapshots
            GROUP BY goods_no, collected_date, platform
            HAVING COUNT(*) > 1
            LIMIT 10
            """
        ).fetchall(),
    )

    print_rows(
        "중복 검사용: rankings 중복 여부",
        conn.execute(
            """
            SELECT goods_no, collected_date, platform, sort_type, COUNT(*) AS cnt
            FROM product_rankings
            GROUP BY goods_no, collected_date, platform, sort_type
            HAVING COUNT(*) > 1
            LIMIT 10
            """
        ).fetchall(),
    )

    conn.close()


if __name__ == "__main__":
    main()
