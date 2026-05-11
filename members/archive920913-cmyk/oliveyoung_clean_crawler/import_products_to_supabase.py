import argparse
import re
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# =========================
# 1. 기본 설정
# =========================

load_dotenv()


def get_engine():
    import os

    db_url = os.getenv("SUPABASE_DB_URL")

    if not db_url:
        raise RuntimeError(
            ".env 파일에 SUPABASE_DB_URL이 없습니다.\n"
            "예: SUPABASE_DB_URL=postgresql://postgres:비밀번호@db.xxxxx.supabase.co:5432/postgres"
        )

    return create_engine(db_url, pool_pre_ping=True)


# =========================
# 2. CSV 읽기
# =========================

def read_csv_safely(file_path):
    try:
        return pd.read_csv(file_path, encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv(file_path, encoding="cp949")


# =========================
# 3. 값 정리 함수
# =========================

def clean_text_value(value):
    if pd.isna(value):
        return None

    value = str(value).strip()

    if value == "":
        return None

    return value


def clean_int_value(value):
    if pd.isna(value):
        return None

    text_value = str(value).strip()

    if text_value == "":
        return None

    text_value = text_value.replace(",", "")
    text_value = re.sub(r"[^0-9\-]", "", text_value)

    if text_value == "":
        return None

    try:
        return int(text_value)
    except ValueError:
        return None


def clean_float_value(value):
    if pd.isna(value):
        return None

    text_value = str(value).strip()

    if text_value == "":
        return None

    text_value = re.sub(r"[^0-9.]", "", text_value)

    if text_value == "":
        return None

    try:
        return float(text_value)
    except ValueError:
        return None


def split_ingredients(value):
    if pd.isna(value):
        return []

    text_value = str(value).strip()

    if text_value == "":
        return []

    result = []

    for item in text_value.split(","):
        item = item.strip()
        if item and item not in result:
            result.append(item)

    return result


def extract_goods_no_from_url(url):
    if pd.isna(url):
        return None

    url = str(url).strip()

    if url == "":
        return None

    try:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        goods_no_list = query_params.get("goodsNo", [])

        if goods_no_list:
            return goods_no_list[0]

        return None

    except Exception:
        return None


def get_value(row, column_name):
    if column_name not in row:
        return None

    return row.get(column_name)


def normalize_date(value):
    value = clean_text_value(value)

    if not value:
        return None

    # 이미 2026-05-01 형태면 그대로 사용
    return value


# =========================
# 4. 사용할 CSV 선택
# =========================

def find_cleaned_product_csvs(data_dir):
    data_dir = Path(data_dir)

    cleaned_files = sorted(data_dir.glob("*_cleaned.csv"))

    # 상품정보 CSV만 사용
    product_files = [
        file for file in cleaned_files
        if "(info)" in file.name
    ]

    return product_files


# =========================
# 5. DB 초기화
# =========================

def reset_tables(conn):
    conn.execute(text("DROP TABLE IF EXISTS product_reviews;"))
    conn.execute(text("DROP TABLE IF EXISTS product_full_ingredients;"))
    conn.execute(text("DROP TABLE IF EXISTS product_main_ingredients;"))
    conn.execute(text("DROP TABLE IF EXISTS product_rankings;"))
    conn.execute(text("DROP TABLE IF EXISTS product_snapshots;"))
    conn.execute(text("DROP TABLE IF EXISTS products;"))

    create_schema(conn)


def create_schema(conn):
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS products (
            goods_no TEXT PRIMARY KEY,
            brand TEXT,
            product_name_raw TEXT,
            product_name_clean TEXT,
            product_name TEXT,
            volume_ml TEXT,
            url TEXT,
            first_collected_date DATE,
            last_collected_date DATE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS product_snapshots (
            id BIGSERIAL PRIMARY KEY,
            goods_no TEXT NOT NULL REFERENCES products(goods_no) ON DELETE CASCADE,
            collected_date DATE NOT NULL,
            platform TEXT DEFAULT 'oliveyoung',
            regular_price INTEGER,
            discount TEXT,
            sales_price INTEGER,
            rating NUMERIC,
            review_count INTEGER,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(goods_no, collected_date, platform)
        );
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS product_rankings (
            id BIGSERIAL PRIMARY KEY,
            goods_no TEXT NOT NULL REFERENCES products(goods_no) ON DELETE CASCADE,
            collected_date DATE NOT NULL,
            platform TEXT DEFAULT 'oliveyoung',
            sort_type TEXT NOT NULL,
            rank INTEGER,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(goods_no, collected_date, platform, sort_type)
        );
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS product_main_ingredients (
            id BIGSERIAL PRIMARY KEY,
            goods_no TEXT NOT NULL REFERENCES products(goods_no) ON DELETE CASCADE,
            ingredient_name TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(goods_no, ingredient_name)
        );
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS product_full_ingredients (
            id BIGSERIAL PRIMARY KEY,
            goods_no TEXT NOT NULL REFERENCES products(goods_no) ON DELETE CASCADE,
            ingredient_order INTEGER,
            ingredient_name TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(goods_no, ingredient_order, ingredient_name)
        );
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS product_reviews (
            id BIGSERIAL PRIMARY KEY,
            goods_no TEXT REFERENCES products(goods_no) ON DELETE CASCADE,
            collected_date DATE,
            platform TEXT DEFAULT 'oliveyoung',
            sort_type TEXT,
            rank INTEGER,
            review_rating NUMERIC,
            skin_type TEXT,
            review_text TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """))


# =========================
# 6. 한 행 적재
# =========================

def import_one_row(conn, row):
    url = clean_text_value(get_value(row, "url"))

    goods_no = clean_text_value(get_value(row, "goodsNo"))

    if not goods_no:
        goods_no = extract_goods_no_from_url(url)

    if not goods_no:
        return False

    collected_date = normalize_date(get_value(row, "date"))
    platform = clean_text_value(get_value(row, "platform")) or "oliveyoung"
    sort_type = clean_text_value(get_value(row, "sort_type"))

    product_name_raw = clean_text_value(get_value(row, "product_name"))
    product_name_clean = clean_text_value(get_value(row, "product_name_clean"))
    product_name = product_name_clean or product_name_raw

    brand = clean_text_value(get_value(row, "brand"))
    volume_ml = clean_text_value(get_value(row, "volume_ml"))

    regular_price = clean_int_value(get_value(row, "regular_price"))
    discount = clean_text_value(get_value(row, "discount"))
    sales_price = clean_int_value(get_value(row, "sales_price"))
    rating = clean_float_value(get_value(row, "rating"))
    review_count = clean_int_value(get_value(row, "review_count"))
    rank = clean_int_value(get_value(row, "rank"))

    # 1. products
    conn.execute(text("""
        INSERT INTO products (
            goods_no,
            brand,
            product_name_raw,
            product_name_clean,
            product_name,
            volume_ml,
            url,
            first_collected_date,
            last_collected_date,
            updated_at
        )
        VALUES (
            :goods_no,
            :brand,
            :product_name_raw,
            :product_name_clean,
            :product_name,
            :volume_ml,
            :url,
            :collected_date,
            :collected_date,
            NOW()
        )
        ON CONFLICT (goods_no)
        DO UPDATE SET
            brand = EXCLUDED.brand,
            product_name_raw = EXCLUDED.product_name_raw,
            product_name_clean = EXCLUDED.product_name_clean,
            product_name = EXCLUDED.product_name,
            volume_ml = EXCLUDED.volume_ml,
            url = EXCLUDED.url,
            last_collected_date = GREATEST(products.last_collected_date, EXCLUDED.last_collected_date),
            updated_at = NOW();
    """), {
        "goods_no": goods_no,
        "brand": brand,
        "product_name_raw": product_name_raw,
        "product_name_clean": product_name_clean,
        "product_name": product_name,
        "volume_ml": volume_ml,
        "url": url,
        "collected_date": collected_date,
    })

    # 2. product_snapshots
    if collected_date:
        conn.execute(text("""
            INSERT INTO product_snapshots (
                goods_no,
                collected_date,
                platform,
                regular_price,
                discount,
                sales_price,
                rating,
                review_count,
                updated_at
            )
            VALUES (
                :goods_no,
                :collected_date,
                :platform,
                :regular_price,
                :discount,
                :sales_price,
                :rating,
                :review_count,
                NOW()
            )
            ON CONFLICT (goods_no, collected_date, platform)
            DO UPDATE SET
                regular_price = EXCLUDED.regular_price,
                discount = EXCLUDED.discount,
                sales_price = EXCLUDED.sales_price,
                rating = EXCLUDED.rating,
                review_count = EXCLUDED.review_count,
                updated_at = NOW();
        """), {
            "goods_no": goods_no,
            "collected_date": collected_date,
            "platform": platform,
            "regular_price": regular_price,
            "discount": discount,
            "sales_price": sales_price,
            "rating": rating,
            "review_count": review_count,
        })

    # 3. product_rankings
    if collected_date and sort_type:
        conn.execute(text("""
            INSERT INTO product_rankings (
                goods_no,
                collected_date,
                platform,
                sort_type,
                rank,
                updated_at
            )
            VALUES (
                :goods_no,
                :collected_date,
                :platform,
                :sort_type,
                :rank,
                NOW()
            )
            ON CONFLICT (goods_no, collected_date, platform, sort_type)
            DO UPDATE SET
                rank = EXCLUDED.rank,
                updated_at = NOW();
        """), {
            "goods_no": goods_no,
            "collected_date": collected_date,
            "platform": platform,
            "sort_type": sort_type,
            "rank": rank,
        })

    # 4. 주성분
    main_ingredients_text = clean_text_value(get_value(row, "main_ingredients_kor"))

    if not main_ingredients_text:
        main_ingredients_text = clean_text_value(get_value(row, "main_ingredients"))

    for ingredient_name in split_ingredients(main_ingredients_text):
        conn.execute(text("""
            INSERT INTO product_main_ingredients (
                goods_no,
                ingredient_name
            )
            VALUES (
                :goods_no,
                :ingredient_name
            )
            ON CONFLICT (goods_no, ingredient_name)
            DO NOTHING;
        """), {
            "goods_no": goods_no,
            "ingredient_name": ingredient_name,
        })

    # 5. 전성분
    full_ingredients_text = clean_text_value(get_value(row, "ingredients"))

    full_ingredients = split_ingredients(full_ingredients_text)

    for index, ingredient_name in enumerate(full_ingredients, start=1):
        conn.execute(text("""
            INSERT INTO product_full_ingredients (
                goods_no,
                ingredient_order,
                ingredient_name
            )
            VALUES (
                :goods_no,
                :ingredient_order,
                :ingredient_name
            )
            ON CONFLICT (goods_no, ingredient_order, ingredient_name)
            DO NOTHING;
        """), {
            "goods_no": goods_no,
            "ingredient_order": index,
            "ingredient_name": ingredient_name,
        })

    return True


# =========================
# 7. 전체 적재
# =========================

def import_products(data_dir, reset=False):
    engine = get_engine()

    csv_files = find_cleaned_product_csvs(data_dir)

    if not csv_files:
        raise RuntimeError(
            f"{data_dir} 폴더에서 *_cleaned.csv 상품 파일을 찾지 못했습니다.\n"
            "먼저 python preprocess_all_columns.py 를 실행하세요."
        )

    total_rows = 0
    imported_rows = 0
    skipped_rows = 0

    with engine.begin() as conn:
        if reset:
            print("[초기화] Supabase 테이블 삭제 후 재생성")
            reset_tables(conn)
        else:
            create_schema(conn)

        print("[사용할 CSV]")
        for csv_file in csv_files:
            print(f"- {csv_file.name}")

        for csv_file in csv_files:
            df = read_csv_safely(csv_file)

            for _, row in df.iterrows():
                total_rows += 1

                ok = import_one_row(conn, row)

                if ok:
                    imported_rows += 1
                else:
                    skipped_rows += 1

    print()
    print("[Supabase DB 적재 완료]")
    print(f"사용한 CSV 파일 수: {len(csv_files)}")
    print(f"처리한 CSV 행 수: {total_rows}")
    print(f"적재 처리된 행 수: {imported_rows}")
    print(f"goodsNo 없어서 건너뛴 행 수: {skipped_rows}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="Data")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    import_products(
        data_dir=args.data_dir,
        reset=args.reset
    )


if __name__ == "__main__":
    main()