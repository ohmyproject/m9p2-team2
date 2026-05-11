from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Query

DB_PATH = Path("db/oliveyoung.sqlite")

app = FastAPI(title="OliveYoung Product API", version="3.0-cleaned-priority")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def rows_to_dicts(rows) -> list[dict]:
    return [dict(row) for row in rows]


@app.get("/health")
def health():
    return {"status": "ok", "db_path": str(DB_PATH)}


@app.get("/products")
def get_products(
    q: str | None = None,
    brand: str | None = None,
    sort_type: str | None = None,
    collected_date: str | None = None,
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """상품 목록 조회. 최신 snapshot과 선택한 랭킹 정보를 같이 보여줍니다."""
    conn = get_conn()

    where = []
    params = []

    if q:
        where.append("(p.product_name LIKE ? OR p.product_name_raw LIKE ? OR p.product_name_clean LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])
    if brand:
        where.append("p.brand LIKE ?")
        params.append(f"%{brand}%")
    if sort_type:
        where.append("r.sort_type = ?")
        params.append(sort_type)
    if collected_date:
        where.append("r.collected_date = ?")
        params.append(collected_date)

    where_sql = "WHERE " + " AND ".join(where) if where else ""

    sql = f"""
        WITH latest_snapshot AS (
            SELECT s.*
            FROM product_snapshots s
            JOIN (
                SELECT goods_no, MAX(collected_date) AS max_date
                FROM product_snapshots
                GROUP BY goods_no
            ) x ON x.goods_no = s.goods_no AND x.max_date = s.collected_date
        ), latest_ranking AS (
            SELECT r.*
            FROM product_rankings r
            JOIN (
                SELECT goods_no, sort_type, MAX(collected_date) AS max_date
                FROM product_rankings
                GROUP BY goods_no, sort_type
            ) x ON x.goods_no = r.goods_no
               AND x.sort_type = r.sort_type
               AND x.max_date = r.collected_date
        )
        SELECT
            p.goods_no,
            p.brand,
            p.product_name,
            p.volume_ml,
            p.url,
            s.sales_price,
            s.regular_price,
            s.discount,
            s.rating,
            s.review_count,
            r.collected_date AS ranking_date,
            r.sort_type,
            r.rank
        FROM products p
        LEFT JOIN latest_snapshot s ON s.goods_no = p.goods_no
        LEFT JOIN latest_ranking r ON r.goods_no = p.goods_no
        {where_sql}
        ORDER BY
            CASE WHEN r.rank IS NULL THEN 1 ELSE 0 END,
            r.rank ASC,
            p.goods_no ASC
        LIMIT ? OFFSET ?
    """
    rows = conn.execute(sql, (*params, limit, offset)).fetchall()
    conn.close()
    return {"items": rows_to_dicts(rows), "limit": limit, "offset": offset}


@app.get("/products/{goods_no}")
def get_product_detail(goods_no: str):
    conn = get_conn()

    product = conn.execute("SELECT * FROM products WHERE goods_no = ?", (goods_no,)).fetchone()
    if not product:
        conn.close()
        return {"error": "상품을 찾지 못했습니다.", "goods_no": goods_no}

    snapshots = conn.execute(
        """
        SELECT collected_date, platform, regular_price, discount, sales_price, rating, review_count
        FROM product_snapshots
        WHERE goods_no = ?
        ORDER BY collected_date
        """,
        (goods_no,),
    ).fetchall()

    rankings = conn.execute(
        """
        SELECT collected_date, platform, sort_type, rank
        FROM product_rankings
        WHERE goods_no = ?
        ORDER BY sort_type, collected_date
        """,
        (goods_no,),
    ).fetchall()

    main_ingredients = conn.execute(
        """
        SELECT ingredient_order, ingredient_name, source_column
        FROM product_main_ingredients
        WHERE goods_no = ?
        ORDER BY ingredient_order, ingredient_name
        """,
        (goods_no,),
    ).fetchall()

    full_ingredients = conn.execute(
        """
        SELECT ingredient_order, ingredient_name, ing_source
        FROM product_full_ingredients
        WHERE goods_no = ?
        ORDER BY ingredient_order
        """,
        (goods_no,),
    ).fetchall()

    reviews = conn.execute(
        """
        SELECT collected_date, sort_type, rank, review_rating, skin_type, review_text
        FROM product_reviews
        WHERE goods_no = ?
        ORDER BY id DESC
        LIMIT 50
        """,
        (goods_no,),
    ).fetchall()

    conn.close()
    return {
        "product": dict(product),
        "snapshots": rows_to_dicts(snapshots),
        "rankings": rows_to_dicts(rankings),
        "main_ingredients": rows_to_dicts(main_ingredients),
        "full_ingredients": rows_to_dicts(full_ingredients),
        "reviews": rows_to_dicts(reviews),
    }


@app.get("/rankings")
def get_rankings(
    sort_type: str | None = None,
    collected_date: str | None = None,
    limit: int = Query(50, ge=1, le=500),
):
    conn = get_conn()
    where = []
    params = []
    if sort_type:
        where.append("r.sort_type = ?")
        params.append(sort_type)
    if collected_date:
        where.append("r.collected_date = ?")
        params.append(collected_date)
    where_sql = "WHERE " + " AND ".join(where) if where else ""

    rows = conn.execute(
        f"""
        SELECT r.collected_date, r.sort_type, r.rank,
               p.goods_no, p.brand, p.product_name,
               s.sales_price, s.rating, s.review_count
        FROM product_rankings r
        JOIN products p ON p.goods_no = r.goods_no
        LEFT JOIN product_snapshots s
          ON s.goods_no = r.goods_no
         AND s.collected_date = r.collected_date
         AND s.platform = r.platform
        {where_sql}
        ORDER BY r.collected_date, r.sort_type, r.rank
        LIMIT ?
        """,
        (*params, limit),
    ).fetchall()
    conn.close()
    return {"items": rows_to_dicts(rows)}


@app.get("/ingredients/search")
def search_ingredients(
    q: str,
    kind: Literal["main", "full", "all"] = "all",
    limit: int = Query(50, ge=1, le=200),
):
    conn = get_conn()
    params = [f"%{q}%"]
    queries = []

    if kind in {"main", "all"}:
        queries.append(
            """
            SELECT 'main' AS kind, i.ingredient_name, p.goods_no, p.brand, p.product_name
            FROM product_main_ingredients i
            JOIN products p ON p.goods_no = i.goods_no
            WHERE i.ingredient_name LIKE ?
            """
        )
    if kind in {"full", "all"}:
        queries.append(
            """
            SELECT 'full' AS kind, i.ingredient_name, p.goods_no, p.brand, p.product_name
            FROM product_full_ingredients i
            JOIN products p ON p.goods_no = i.goods_no
            WHERE i.ingredient_name LIKE ?
            """
        )

    sql = " UNION ALL ".join(queries) + " LIMIT ?"
    # kind=all이면 q 파라미터가 두 번 필요합니다.
    if kind == "all":
        final_params = [f"%{q}%", f"%{q}%", limit]
    else:
        final_params = [f"%{q}%", limit]

    rows = conn.execute(sql, final_params).fetchall()
    conn.close()
    return {"items": rows_to_dicts(rows)}


@app.get("/dashboard/summary")
def dashboard_summary():
    conn = get_conn()
    tables = [
        "products",
        "product_snapshots",
        "product_rankings",
        "product_main_ingredients",
        "product_full_ingredients",
        "product_reviews",
    ]
    counts = {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in tables}

    brand_top = conn.execute(
        """
        SELECT brand, COUNT(*) AS product_count
        FROM products
        GROUP BY brand
        ORDER BY product_count DESC
        LIMIT 10
        """
    ).fetchall()

    latest_dates = conn.execute(
        """
        SELECT collected_date, COUNT(*) AS ranking_count
        FROM product_rankings
        GROUP BY collected_date
        ORDER BY collected_date
        """
    ).fetchall()

    conn.close()
    return {
        "counts": counts,
        "brand_top": rows_to_dicts(brand_top),
        "ranking_count_by_date": rows_to_dicts(latest_dates),
    }
