import os

from dotenv import load_dotenv
from fastapi import FastAPI, Query
from sqlalchemy import create_engine, text


load_dotenv()

DB_URL = os.getenv("SUPABASE_DB_URL")

if not DB_URL:
    raise Exception(".env 파일에 SUPABASE_DB_URL이 없습니다.")

engine = create_engine(DB_URL)

app = FastAPI(title="Cosmetic Project API")


@app.get("/")
def root():
    return {
        "message": "Cosmetic Project API",
        "docs": "/docs",
    }


@app.get("/products")
def get_products(
    keyword: str = Query("", description="상품명 또는 브랜드 검색어"),
    sort_type: str = Query("", description="정렬명 예: 판매순, 신상품순"),
    ingredient: str = Query("", description="주요성분 검색어"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    sql = """
        SELECT
            id, date, platform, sort_type, rank,
            product_name, brand, volume_ml,
            regular_price, discount, sales_price,
            rating, review_count,
            main_ingredients, ingredients, ing_source, url
        FROM products
        WHERE 1=1
    """

    params = {}

    if keyword:
        sql += """
            AND (
                product_name ILIKE :keyword
                OR brand ILIKE :keyword
            )
        """
        params["keyword"] = f"%{keyword}%"

    if sort_type:
        sql += " AND sort_type = :sort_type"
        params["sort_type"] = sort_type

    if ingredient:
        sql += """
            AND (
                main_ingredients ILIKE :ingredient
                OR ingredients ILIKE :ingredient
            )
        """
        params["ingredient"] = f"%{ingredient}%"

    sql += """
        ORDER BY date DESC, sort_type ASC, rank ASC
        LIMIT :limit OFFSET :offset
    """

    params["limit"] = limit
    params["offset"] = offset

    rows = fetch_all(sql, params)

    return {
        "count": len(rows),
        "items": rows,
    }


@app.get("/products/{product_id}")
def get_product_detail(product_id: int):
    product_sql = """
        SELECT
            id, date, platform, sort_type, rank,
            product_name, brand, volume_ml,
            regular_price, discount, sales_price,
            rating, review_count,
            main_ingredients, ingredients, ing_source, url
        FROM products
        WHERE id = :product_id
    """

    product = fetch_one(product_sql, {"product_id": product_id})

    if not product:
        return {
            "error": "상품을 찾지 못했습니다.",
            "product_id": product_id,
        }

    review_sql = """
        SELECT
            id, date, platform, sort_type, rank,
            product_name, review_count,
            review_rating, skin_type, review_text, url
        FROM reviews
        WHERE product_name = :product_name
        ORDER BY id ASC
        LIMIT 50
    """

    reviews = fetch_all(
        review_sql,
        {"product_name": product["product_name"]},
    )

    return {
        "product": product,
        "reviews": reviews,
    }


@app.get("/reviews")
def get_reviews(
    keyword: str = Query("", description="상품명 또는 리뷰 내용 검색어"),
    product_name: str = Query("", description="상품명 정확 검색"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    sql = """
        SELECT
            id, date, platform, sort_type, rank,
            product_name, review_count,
            review_rating, skin_type, review_text, url
        FROM reviews
        WHERE 1=1
    """

    params = {}

    if keyword:
        sql += """
            AND (
                product_name ILIKE :keyword
                OR review_text ILIKE :keyword
            )
        """
        params["keyword"] = f"%{keyword}%"

    if product_name:
        sql += " AND product_name = :product_name"
        params["product_name"] = product_name

    sql += """
        ORDER BY id ASC
        LIMIT :limit OFFSET :offset
    """

    params["limit"] = limit
    params["offset"] = offset

    rows = fetch_all(sql, params)

    return {
        "count": len(rows),
        "items": rows,
    }


@app.get("/summary")
def get_summary():
    product_count = fetch_value("SELECT COUNT(*) FROM products")
    review_count = fetch_value("SELECT COUNT(*) FROM reviews")

    empty_main = fetch_value(
        """
        SELECT COUNT(*)
        FROM products
        WHERE main_ingredients IS NULL
           OR TRIM(main_ingredients) = ''
        """
    )

    avg_rating = fetch_value(
        """
        SELECT ROUND(AVG(rating)::numeric, 2)
        FROM products
        WHERE rating > 0
        """
    )

    top_brands = fetch_all(
        """
        SELECT brand, COUNT(*) AS count
        FROM products
        WHERE brand IS NOT NULL
          AND TRIM(brand) != ''
        GROUP BY brand
        ORDER BY count DESC
        LIMIT 10
        """,
        {},
    )

    top_ingredients = fetch_all(
        """
        SELECT main_ingredients, COUNT(*) AS count
        FROM products
        WHERE main_ingredients IS NOT NULL
          AND TRIM(main_ingredients) != ''
        GROUP BY main_ingredients
        ORDER BY count DESC
        LIMIT 10
        """,
        {},
    )

    return {
        "product_count": product_count,
        "review_count": review_count,
        "empty_main_ingredients": empty_main,
        "average_rating": avg_rating,
        "top_brands": top_brands,
        "top_ingredients": top_ingredients,
    }


@app.get("/search")
def search_all(
    q: str = Query(..., description="통합 검색어"),
    limit: int = Query(30, ge=1, le=100),
):
    products = fetch_all(
        """
        SELECT
            id, product_name, brand, main_ingredients,
            sales_price, rating, review_count, url
        FROM products
        WHERE product_name ILIKE :q
           OR brand ILIKE :q
           OR main_ingredients ILIKE :q
           OR ingredients ILIKE :q
        ORDER BY rating DESC, review_count DESC
        LIMIT :limit
        """,
        {
            "q": f"%{q}%",
            "limit": limit,
        },
    )

    reviews = fetch_all(
        """
        SELECT
            id, product_name, review_rating, skin_type, review_text, url
        FROM reviews
        WHERE product_name ILIKE :q
           OR review_text ILIKE :q
        ORDER BY id ASC
        LIMIT :limit
        """,
        {
            "q": f"%{q}%",
            "limit": limit,
        },
    )

    return {
        "query": q,
        "products": products,
        "reviews": reviews,
    }


def fetch_all(sql, params=None):
    if params is None:
        params = {}

    with engine.begin() as conn:
        result = conn.execute(text(sql), params)
        rows = result.mappings().all()

    return [dict(row) for row in rows]


def fetch_one(sql, params=None):
    rows = fetch_all(sql, params)

    if not rows:
        return None

    return rows[0]


def fetch_value(sql, params=None):
    if params is None:
        params = {}

    with engine.begin() as conn:
        value = conn.execute(text(sql), params).scalar()

    return value