from sqlalchemy import text


def create_tables(engine):
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS products (
                    id BIGSERIAL PRIMARY KEY,
                    date TEXT,
                    platform TEXT,
                    sort_type TEXT,
                    rank INTEGER,
                    product_name TEXT,
                    brand TEXT,
                    volume_ml TEXT,
                    regular_price INTEGER,
                    discount INTEGER,
                    sales_price INTEGER,
                    rating DOUBLE PRECISION,
                    review_count INTEGER,
                    main_ingredients TEXT,
                    ingredients TEXT,
                    ing_source TEXT,
                    url TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE(platform, sort_type, product_name, brand)
                );
                """
            )
        )

        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS reviews (
                    id BIGSERIAL PRIMARY KEY,
                    date TEXT,
                    platform TEXT,
                    sort_type TEXT,
                    rank INTEGER,
                    main_ingredients TEXT,
                    product_name TEXT,
                    review_count INTEGER,
                    review_rating DOUBLE PRECISION,
                    skin_type TEXT,
                    review_text TEXT,
                    url TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE(platform, product_name, review_text)
                );
                """
            )
        )