"""
Olive Young DB schema v3

이번 버전의 핵심:
- 원본 CSV와 _cleaned.csv가 같이 있을 때 _cleaned.csv만 적재하기 위한 구조
- product_name_clean 컬럼을 반영
- rank는 product_rankings로 분리
- 상품 기본정보/날짜별 상태/날짜별 랭킹/주성분/전성분을 분리 저장
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


def connect_db(db_path: str | Path) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS products (
            goods_no TEXT PRIMARY KEY,
            brand TEXT,
            product_name TEXT NOT NULL,
            product_name_raw TEXT,
            product_name_clean TEXT,
            volume_ml TEXT,
            url TEXT,
            first_collected_date TEXT,
            last_collected_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS product_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goods_no TEXT NOT NULL,
            collected_date TEXT NOT NULL,
            platform TEXT NOT NULL DEFAULT 'oliveyoung',
            regular_price INTEGER,
            discount TEXT,
            sales_price INTEGER,
            rating REAL,
            review_count INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(goods_no, collected_date, platform),
            FOREIGN KEY (goods_no) REFERENCES products(goods_no) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS product_rankings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goods_no TEXT NOT NULL,
            collected_date TEXT NOT NULL,
            platform TEXT NOT NULL DEFAULT 'oliveyoung',
            sort_type TEXT NOT NULL,
            rank INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(goods_no, collected_date, platform, sort_type),
            FOREIGN KEY (goods_no) REFERENCES products(goods_no) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS product_main_ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goods_no TEXT NOT NULL,
            ingredient_order INTEGER,
            ingredient_name TEXT NOT NULL,
            source_column TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(goods_no, ingredient_name),
            FOREIGN KEY (goods_no) REFERENCES products(goods_no) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS product_full_ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goods_no TEXT NOT NULL,
            ingredient_order INTEGER NOT NULL,
            ingredient_name TEXT NOT NULL,
            ing_source TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(goods_no, ingredient_order, ingredient_name),
            FOREIGN KEY (goods_no) REFERENCES products(goods_no) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS product_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goods_no TEXT NOT NULL,
            collected_date TEXT,
            platform TEXT DEFAULT 'oliveyoung',
            sort_type TEXT,
            rank INTEGER,
            review_rating REAL,
            skin_type TEXT,
            review_text TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(goods_no, review_text),
            FOREIGN KEY (goods_no) REFERENCES products(goods_no) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_products_brand
            ON products(brand);
        CREATE INDEX IF NOT EXISTS idx_products_name
            ON products(product_name);
        CREATE INDEX IF NOT EXISTS idx_snapshots_goods_date
            ON product_snapshots(goods_no, collected_date);
        CREATE INDEX IF NOT EXISTS idx_rankings_goods_date_sort
            ON product_rankings(goods_no, collected_date, sort_type);
        CREATE INDEX IF NOT EXISTS idx_rankings_sort_date_rank
            ON product_rankings(sort_type, collected_date, rank);
        CREATE INDEX IF NOT EXISTS idx_main_ingredient_name
            ON product_main_ingredients(ingredient_name);
        CREATE INDEX IF NOT EXISTS idx_full_ingredient_name
            ON product_full_ingredients(ingredient_name);
        CREATE INDEX IF NOT EXISTS idx_reviews_goods_no
            ON product_reviews(goods_no);
        """
    )
    conn.commit()


def reset_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP TABLE IF EXISTS product_reviews;
        DROP TABLE IF EXISTS product_full_ingredients;
        DROP TABLE IF EXISTS product_main_ingredients;
        DROP TABLE IF EXISTS product_rankings;
        DROP TABLE IF EXISTS product_snapshots;
        DROP TABLE IF EXISTS products;
        """
    )
    conn.commit()
    create_tables(conn)
