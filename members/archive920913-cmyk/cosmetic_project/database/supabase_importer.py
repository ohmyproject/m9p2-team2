import os
import re
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from crawler.config import DATA_DIR


load_dotenv()


def get_engine():
    db_url = os.getenv("SUPABASE_DB_URL")

    if not db_url:
        raise RuntimeError(
            ".env 파일에 SUPABASE_DB_URL이 없습니다.\n"
            "예: SUPABASE_DB_URL=postgresql://postgres.xxxxx:비밀번호@xxxx.pooler.supabase.com:5432/postgres"
        )

    return create_engine(db_url, pool_pre_ping=True)


def read_csv_safely(file_path):
    try:
        return pd.read_csv(file_path, encoding="utf-8-sig", dtype=str).fillna("")
    except UnicodeDecodeError:
        return pd.read_csv(file_path, encoding="cp949", dtype=str).fillna("")
    except Exception:
        return pd.read_csv(file_path, dtype=str).fillna("")


def clean_text_value(value):
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    value = str(value).strip()

    if value == "":
        return None

    if value.lower() in ["nan", "none", "null"]:
        return None

    return value


def clean_int_value(value):
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    text_value = str(value).strip()

    if text_value == "":
        return None

    text_value = text_value.replace(",", "")
    text_value = text_value.replace("원", "")
    text_value = re.sub(r"[^0-9.\-]", "", text_value)

    if text_value in ["", "-", ".", "-."]:
        return None

    try:
        return int(float(text_value))
    except Exception:
        return None


def clean_float_value(value):
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    text_value = str(value).strip()

    if text_value == "":
        return None

    text_value = re.sub(r"[^0-9.]", "", text_value)

    if text_value == "":
        return None

    try:
        return float(text_value)
    except Exception:
        return None


def split_ingredients(value):
    if not value:
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
    if not url:
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

    except Exception:
        pass

    match = re.search(r"goodsNo=([^&]+)", url)

    if match:
        return match.group(1).strip()

    return None


def get_value(row, column_name):
    if column_name not in row:
        return None

    return row.get(column_name)


def normalize_date(value):
    value = clean_text_value(value)

    if not value:
        return None

    return value


def is_product_cleaned_file(file_path):
    name = file_path.name

    if "_cleaned.csv" not in name:
        return False

    if "_Review(oliveyoung)_" in name:
        return False

    if "(review)" in name:
        return False

    if "Review" in name:
        return False

    if "_Data(oliveyoung)_" in name:
        return True

    if "(info)" in name:
        return True

    return False


def is_review_cleaned_file(file_path):
    name = file_path.name

    if "_cleaned.csv" not in name:
        return False

    if "_Review(oliveyoung)_" in name:
        return True

    if "(review)" in name:
        return True

    if "Review" in name:
        return True

    return False


def remove_retry_suffix_from_cleaned(filename):
    name = filename
    name = name.replace("_retry_cleaned.csv", "_cleaned.csv")
    return name


def cleaned_file_score(path):
    name = path.name
    score = 0

    if "_retry_cleaned.csv" in name:
        score += 100

    if "_save" in name:
        score += 50

    return score


def select_effective_cleaned_files(files, kind):
    grouped = {}

    for path in files:
        key = remove_retry_suffix_from_cleaned(path.name)

        if kind == "review":
            key = key.replace("(info)", "(review)")
            key = key.replace("_Data(oliveyoung)_", "_Review(oliveyoung)_")

        if key not in grouped:
            grouped[key] = path
            continue

        if cleaned_file_score(path) > cleaned_file_score(grouped[key]):
            grouped[key] = path

    return sorted(grouped.values())


def find_cleaned_product_csvs(data_dir):
    data_dir = Path(data_dir)
    cleaned_files = sorted(data_dir.glob("*_cleaned.csv"))

    product_candidates = [
        file for file in cleaned_files
        if is_product_cleaned_file(file)
    ]

    return select_effective_cleaned_files(
        product_candidates,
        kind="product",
    )


def find_cleaned_review_csvs(data_dir):
    data_dir = Path(data_dir)
    cleaned_files = sorted(data_dir.glob("*_cleaned.csv"))

    review_candidates = [
        file for file in cleaned_files
        if is_review_cleaned_file(file)
    ]

    return select_effective_cleaned_files(
        review_candidates,
        kind="review",
    )


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
            main_ingredients TEXT,
            review_rating NUMERIC,
            skin_type TEXT,
            review_text TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """))

    conn.execute(text("""
        ALTER TABLE product_reviews
        ADD COLUMN IF NOT EXISTS main_ingredients TEXT;
    """))


def build_product_main_ingredients_map(product_files):
    result = {}

    for csv_file in product_files:
        try:
            df = read_csv_safely(csv_file)
        except Exception as e:
            print(f"[주요성분 매핑 실패] {csv_file.name}: {e}")
            continue

        for _, row in df.iterrows():
            goods_no = clean_text_value(get_value(row, "goodsNo"))

            if not goods_no:
                goods_no = clean_text_value(get_value(row, "goods_no"))

            if not goods_no:
                goods_no = extract_goods_no_from_url(get_value(row, "url"))

            if not goods_no:
                continue

            main_value = clean_text_value(get_value(row, "main_ingredients_kor"))

            if not main_value:
                main_value = clean_text_value(get_value(row, "main_ingredients"))

            if not main_value:
                continue

            old_value = result.get(goods_no)

            if not old_value:
                result[goods_no] = main_value
                continue

            if len(main_value) > len(old_value):
                result[goods_no] = main_value

    return result


def import_one_product_row(conn, row):
    url = clean_text_value(get_value(row, "url"))

    goods_no = clean_text_value(get_value(row, "goodsNo"))

    if not goods_no:
        goods_no = clean_text_value(get_value(row, "goods_no"))

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


def import_one_review_row(conn, row, product_main_ingredients_map=None):
    if product_main_ingredients_map is None:
        product_main_ingredients_map = {}

    url = clean_text_value(get_value(row, "url"))

    goods_no = clean_text_value(get_value(row, "goodsNo"))

    if not goods_no:
        goods_no = clean_text_value(get_value(row, "goods_no"))

    if not goods_no:
        goods_no = extract_goods_no_from_url(url)

    collected_date = normalize_date(get_value(row, "date"))
    platform = clean_text_value(get_value(row, "platform")) or "oliveyoung"
    sort_type = clean_text_value(get_value(row, "sort_type"))
    rank = clean_int_value(get_value(row, "rank"))
    review_rating = clean_float_value(get_value(row, "review_rating"))
    skin_type = clean_text_value(get_value(row, "skin_type"))
    review_text = clean_text_value(get_value(row, "review_text"))

    if not goods_no:
        return False

    if not review_text:
        return False

    main_ingredients = clean_text_value(get_value(row, "main_ingredients_kor"))

    if not main_ingredients:
        main_ingredients = clean_text_value(get_value(row, "main_ingredients"))

    if not main_ingredients:
        main_ingredients = product_main_ingredients_map.get(goods_no)

    exists = conn.execute(
        text(
            """
            SELECT 1
            FROM product_reviews
            WHERE goods_no = :goods_no
              AND review_text = :review_text
            LIMIT 1;
            """
        ),
        {
            "goods_no": goods_no,
            "review_text": review_text,
        },
    ).fetchone()

    if exists:
        conn.execute(
            text(
                """
                UPDATE product_reviews
                SET main_ingredients = :main_ingredients
                WHERE goods_no = :goods_no
                  AND review_text = :review_text;
                """
            ),
            {
                "goods_no": goods_no,
                "review_text": review_text,
                "main_ingredients": main_ingredients,
            },
        )

        return True

    conn.execute(
        text(
            """
            INSERT INTO product_reviews (
                goods_no,
                collected_date,
                platform,
                sort_type,
                rank,
                main_ingredients,
                review_rating,
                skin_type,
                review_text
            )
            VALUES (
                :goods_no,
                :collected_date,
                :platform,
                :sort_type,
                :rank,
                :main_ingredients,
                :review_rating,
                :skin_type,
                :review_text
            );
            """
        ),
        {
            "goods_no": goods_no,
            "collected_date": collected_date,
            "platform": platform,
            "sort_type": sort_type,
            "rank": rank,
            "main_ingredients": main_ingredients,
            "review_rating": review_rating,
            "skin_type": skin_type,
            "review_text": review_text,
        },
    )

    return True


def import_products(data_dir=DATA_DIR, reset=False):
    engine = get_engine()

    product_files = find_cleaned_product_csvs(data_dir)
    review_files = find_cleaned_review_csvs(data_dir)

    if not product_files and not review_files:
        raise RuntimeError(
            f"{data_dir} 폴더에서 *_cleaned.csv 파일을 찾지 못했습니다.\n"
            "먼저 python preprocess_main.py 를 실행하세요."
        )

    total_product_rows = 0
    imported_product_rows = 0
    skipped_product_rows = 0

    total_review_rows = 0
    imported_review_rows = 0
    skipped_review_rows = 0

    with engine.begin() as conn:
        if reset:
            print("[초기화] Supabase 테이블 삭제 후 재생성")
            reset_tables(conn)
        else:
            create_schema(conn)

        print("[사용할 상품 CSV - 원본/retry 중 최종 선택본만 사용]")
        for csv_file in product_files:
            print(f"- {csv_file.name}")

        print("[사용할 리뷰 CSV - 원본/retry 중 최종 선택본만 사용]")
        for csv_file in review_files:
            print(f"- {csv_file.name}")

        product_main_ingredients_map = build_product_main_ingredients_map(
            product_files
        )

        print(f"[리뷰용 주요성분 매핑] {len(product_main_ingredients_map)}개 상품")

        for csv_file in product_files:
            print("-" * 70)
            print(f"[상품 적재 시작] {csv_file.name}")

            df = read_csv_safely(csv_file)
            file_total = len(df)
            file_imported = 0
            file_skipped = 0

            for row_index, row in df.iterrows():
                total_product_rows += 1

                ok = import_one_product_row(conn, row)

                if ok:
                    imported_product_rows += 1
                    file_imported += 1
                else:
                    skipped_product_rows += 1
                    file_skipped += 1

                if (row_index + 1) % 5 == 0 or (row_index + 1) == file_total:
                    print(
                        f"  [상품 진행] {row_index + 1}/{file_total} "
                        f"성공:{file_imported} 건너뜀:{file_skipped}"
                    )

            print(f"[상품 적재 완료] {csv_file.name}")

        for csv_file in review_files:
            print("-" * 70)
            print(f"[리뷰 적재 시작] {csv_file.name}")

            df = read_csv_safely(csv_file)
            file_total = len(df)
            file_imported = 0
            file_skipped = 0

            for row_index, row in df.iterrows():
                total_review_rows += 1

                ok = import_one_review_row(
                    conn,
                    row,
                    product_main_ingredients_map,
                )

                if ok:
                    imported_review_rows += 1
                    file_imported += 1
                else:
                    skipped_review_rows += 1
                    file_skipped += 1

                if (row_index + 1) % 50 == 0 or (row_index + 1) == file_total:
                    print(
                        f"  [리뷰 진행] {row_index + 1}/{file_total} "
                        f"성공:{file_imported} 건너뜀:{file_skipped}"
                    )

            print(f"[리뷰 적재 완료] {csv_file.name}")

    print()
    print("[Supabase DB 적재 완료]")
    print(f"사용한 상품 CSV 파일 수: {len(product_files)}")
    print(f"처리한 상품 CSV 행 수: {total_product_rows}")
    print(f"적재 처리된 상품 행 수: {imported_product_rows}")
    print(f"goodsNo 없어서 건너뛴 상품 행 수: {skipped_product_rows}")
    print(f"사용한 리뷰 CSV 파일 수: {len(review_files)}")
    print(f"처리한 리뷰 CSV 행 수: {total_review_rows}")
    print(f"적재 처리된 리뷰 행 수: {imported_review_rows}")
    print(f"건너뛴 리뷰 행 수: {skipped_review_rows}")


def import_all_cleaned(reset=False):
    import_products(data_dir=DATA_DIR, reset=reset)