import os
from datetime import date, datetime
from decimal import Decimal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text


# =========================================
# 1. .env 불러오기
# =========================================
load_dotenv()


# =========================================
# 2. FastAPI 앱 생성
# =========================================
app = FastAPI(
    title="OliveYoung Product API",
    description="올리브영 상품/랭킹/성분 데이터를 Supabase PostgreSQL에서 조회하는 API",
    version="1.0.0"
)


# =========================================
# 3. CORS 설정
# =========================================
# Next.js / React 프론트에서 API를 호출할 수 있게 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================
# 4. Supabase DB 연결
# =========================================
def get_engine():
    db_url = os.getenv("SUPABASE_DB_URL")

    if not db_url:
        raise RuntimeError(
            ".env 파일에 SUPABASE_DB_URL이 없습니다.\n"
            "예: SUPABASE_DB_URL=postgresql://postgres.xxxx:비밀번호@xxxx.pooler.supabase.com:5432/postgres"
        )

    return create_engine(db_url, pool_pre_ping=True)


engine = get_engine()


# =========================================
# 5. JSON 변환 보조 함수
# =========================================
def convert_value(value):
    """
    DB에서 가져온 값 중 JSON으로 바로 변환하기 어려운 값을 처리합니다.
    date, datetime, Decimal 같은 값은 문자열/숫자로 변환합니다.
    """
    if isinstance(value, (date, datetime)):
        return value.isoformat()

    if isinstance(value, Decimal):
        return float(value)

    return value


def row_to_dict(row):
    """
    SQLAlchemy Row 객체를 dict로 변환합니다.
    """
    return {
        key: convert_value(value)
        for key, value in dict(row._mapping).items()
    }


def rows_to_dicts(rows):
    """
    여러 Row를 list[dict]로 변환합니다.
    """
    return [row_to_dict(row) for row in rows]


# =========================================
# 6. 서버 / DB 상태 확인
# =========================================
@app.get("/health")
def health():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1 AS test")).first()

    return {
        "status": "ok",
        "db": "supabase_postgres",
        "test": row_to_dict(result)["test"]
    }


# =========================================
# 7. 상품 목록 조회
# =========================================
@app.get("/products")
def get_products(
    q: str | None = Query(None, description="상품명 검색어"),
    brand: str | None = Query(None, description="브랜드 검색어"),
    limit: int = Query(30, ge=1, le=200, description="조회 개수"),
    offset: int = Query(0, ge=0, description="시작 위치"),
):
    """
    상품 목록을 조회합니다.

    - q: 상품명 검색
    - brand: 브랜드 검색
    - limit: 가져올 개수
    - offset: 페이지 시작 위치
    """

    sql = """
        SELECT
            p.goods_no,
            p.brand,
            p.product_name,
            p.product_name_raw,
            p.product_name_clean,
            p.volume_ml,
            p.url,
            p.first_collected_date,
            p.last_collected_date,
            latest.sales_price,
            latest.rating,
            latest.review_count
        FROM products p
        LEFT JOIN LATERAL (
            SELECT
                s.sales_price,
                s.rating,
                s.review_count
            FROM product_snapshots s
            WHERE s.goods_no = p.goods_no
            ORDER BY s.collected_date DESC
            LIMIT 1
        ) latest ON TRUE
        WHERE 1 = 1
    """

    params = {
        "limit": limit,
        "offset": offset,
    }

    if q:
        sql += " AND p.product_name ILIKE :q"
        params["q"] = f"%{q}%"

    if brand:
        sql += " AND p.brand ILIKE :brand"
        params["brand"] = f"%{brand}%"

    sql += """
        ORDER BY p.last_collected_date DESC, p.product_name
        LIMIT :limit OFFSET :offset
    """

    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).fetchall()

    return {
        "count": len(rows),
        "items": rows_to_dicts(rows)
    }


# =========================================
# 8. 상품 상세 조회
# =========================================
@app.get("/products/{goods_no}")
def get_product_detail(goods_no: str):
    """
    특정 상품의 상세 정보를 조회합니다.

    포함 정보:
    - 상품 기본정보
    - 날짜별 가격/평점/리뷰수
    - 날짜별/정렬별 랭킹
    - 주성분
    - 전성분
    """

    with engine.connect() as conn:
        product = conn.execute(text("""
            SELECT
                goods_no,
                brand,
                product_name,
                product_name_raw,
                product_name_clean,
                volume_ml,
                url,
                first_collected_date,
                last_collected_date,
                created_at,
                updated_at
            FROM products
            WHERE goods_no = :goods_no
        """), {"goods_no": goods_no}).first()

        if not product:
            raise HTTPException(
                status_code=404,
                detail="상품을 찾을 수 없습니다."
            )

        snapshots = conn.execute(text("""
            SELECT
                collected_date,
                platform,
                regular_price,
                discount,
                sales_price,
                rating,
                review_count
            FROM product_snapshots
            WHERE goods_no = :goods_no
            ORDER BY collected_date
        """), {"goods_no": goods_no}).fetchall()

        rankings = conn.execute(text("""
            SELECT
                collected_date,
                platform,
                sort_type,
                rank
            FROM product_rankings
            WHERE goods_no = :goods_no
            ORDER BY collected_date, sort_type
        """), {"goods_no": goods_no}).fetchall()

        main_ingredients = conn.execute(text("""
            SELECT
                ingredient_name
            FROM product_main_ingredients
            WHERE goods_no = :goods_no
            ORDER BY ingredient_name
        """), {"goods_no": goods_no}).fetchall()

        full_ingredients = conn.execute(text("""
            SELECT
                ingredient_order,
                ingredient_name
            FROM product_full_ingredients
            WHERE goods_no = :goods_no
            ORDER BY ingredient_order
        """), {"goods_no": goods_no}).fetchall()

    return {
        "product": row_to_dict(product),
        "snapshots": rows_to_dicts(snapshots),
        "rankings": rows_to_dicts(rankings),
        "main_ingredients": rows_to_dicts(main_ingredients),
        "full_ingredients": rows_to_dicts(full_ingredients),
        "reviews": []
    }


# =========================================
# 9. 랭킹 조회
# =========================================
@app.get("/rankings")
def get_rankings(
    collected_date: str | None = Query(None, description="수집 날짜 예: 2026-05-05"),
    sort_type: str | None = Query(None, description="정렬 기준 예: 판매순, 신상품순"),
    limit: int = Query(50, ge=1, le=300, description="조회 개수"),
):
    """
    날짜별 / 정렬별 랭킹을 조회합니다.
    """

    sql = """
        SELECT
            r.collected_date,
            r.platform,
            r.sort_type,
            r.rank,
            p.goods_no,
            p.brand,
            p.product_name,
            p.product_name_clean,
            p.volume_ml,
            p.url
        FROM product_rankings r
        JOIN products p
        ON r.goods_no = p.goods_no
        WHERE 1 = 1
    """

    params = {
        "limit": limit
    }

    if collected_date:
        sql += " AND r.collected_date = :collected_date"
        params["collected_date"] = collected_date

    if sort_type:
        sql += " AND r.sort_type = :sort_type"
        params["sort_type"] = sort_type

    sql += """
        ORDER BY r.collected_date DESC, r.sort_type, r.rank
        LIMIT :limit
    """

    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).fetchall()

    return {
        "count": len(rows),
        "items": rows_to_dicts(rows)
    }


# =========================================
# 10. 성분 검색
# =========================================
@app.get("/ingredients/search")
def search_ingredients(
    q: str = Query(..., description="검색할 성분명"),
    kind: str = Query("all", pattern="^(all|main|full)$", description="all, main, full 중 하나"),
    limit: int = Query(100, ge=1, le=300, description="조회 개수"),
):
    """
    주성분 또는 전성분에서 성분명을 검색합니다.

    kind:
    - all: 주성분 + 전성분 모두 검색
    - main: 주성분만 검색
    - full: 전성분만 검색
    """

    results = {}

    with engine.connect() as conn:
        if kind in ("all", "main"):
            main_rows = conn.execute(text("""
                SELECT
                    p.goods_no,
                    p.brand,
                    p.product_name,
                    m.ingredient_name,
                    'main' AS ingredient_type
                FROM product_main_ingredients m
                JOIN products p
                ON m.goods_no = p.goods_no
                WHERE m.ingredient_name ILIKE :q
                ORDER BY p.product_name
                LIMIT :limit
            """), {
                "q": f"%{q}%",
                "limit": limit
            }).fetchall()

            results["main"] = rows_to_dicts(main_rows)

        if kind in ("all", "full"):
            full_rows = conn.execute(text("""
                SELECT
                    p.goods_no,
                    p.brand,
                    p.product_name,
                    f.ingredient_order,
                    f.ingredient_name,
                    'full' AS ingredient_type
                FROM product_full_ingredients f
                JOIN products p
                ON f.goods_no = p.goods_no
                WHERE f.ingredient_name ILIKE :q
                ORDER BY p.product_name, f.ingredient_order
                LIMIT :limit
            """), {
                "q": f"%{q}%",
                "limit": limit
            }).fetchall()

            results["full"] = rows_to_dicts(full_rows)

    return results


# =========================================
# 11. 대시보드 요약
# =========================================
@app.get("/dashboard/summary")
def dashboard_summary():
    """
    대시보드용 요약 데이터를 조회합니다.
    """

    with engine.connect() as conn:
        counts = conn.execute(text("""
            SELECT 'products' AS table_name, COUNT(*) AS cnt FROM products
            UNION ALL
            SELECT 'product_snapshots', COUNT(*) FROM product_snapshots
            UNION ALL
            SELECT 'product_rankings', COUNT(*) FROM product_rankings
            UNION ALL
            SELECT 'product_main_ingredients', COUNT(*) FROM product_main_ingredients
            UNION ALL
            SELECT 'product_full_ingredients', COUNT(*) FROM product_full_ingredients
            UNION ALL
            SELECT 'product_reviews', COUNT(*) FROM product_reviews
        """)).fetchall()

        latest_rankings = conn.execute(text("""
            SELECT
                r.collected_date,
                r.sort_type,
                r.rank,
                p.goods_no,
                p.brand,
                p.product_name,
                p.volume_ml
            FROM product_rankings r
            JOIN products p
            ON r.goods_no = p.goods_no
            ORDER BY r.collected_date DESC, r.sort_type, r.rank
            LIMIT 20
        """)).fetchall()

        top_review_products = conn.execute(text("""
            SELECT
                p.goods_no,
                p.brand,
                p.product_name,
                s.review_count,
                s.rating,
                s.sales_price
            FROM products p
            JOIN LATERAL (
                SELECT
                    review_count,
                    rating,
                    sales_price
                FROM product_snapshots s
                WHERE s.goods_no = p.goods_no
                ORDER BY s.collected_date DESC
                LIMIT 1
            ) s ON TRUE
            ORDER BY s.review_count DESC NULLS LAST
            LIMIT 10
        """)).fetchall()

    return {
        "counts": rows_to_dicts(counts),
        "latest_rankings": rows_to_dicts(latest_rankings),
        "top_review_products": rows_to_dicts(top_review_products),
        "review_data_status": "리뷰 데이터는 아직 적재되지 않았습니다."
    }