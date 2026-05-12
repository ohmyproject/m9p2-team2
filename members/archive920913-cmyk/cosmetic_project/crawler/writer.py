import os
import pandas as pd

from crawler.config import DATA_DIR, PRODUCT_COLUMNS, REVIEW_COLUMNS
from crawler.utils import now_stamp


def save_product_csv(rows, sort_type):
    os.makedirs(DATA_DIR, exist_ok=True)

    filename = f"{now_stamp()}_Data(oliveyoung)_{sort_type}.csv"
    path = os.path.join(DATA_DIR, filename)

    df = pd.DataFrame(rows)
    df = df.reindex(columns=PRODUCT_COLUMNS)
    df.to_csv(path, index=False, encoding="utf-8-sig")

    print(f"[저장] 상품 CSV: {path}")


def save_review_csv(rows, sort_type):
    os.makedirs(DATA_DIR, exist_ok=True)

    filename = f"{now_stamp()}_Review(oliveyoung)_{sort_type}.csv"
    path = os.path.join(DATA_DIR, filename)

    df = pd.DataFrame(rows)
    df = df.reindex(columns=REVIEW_COLUMNS)
    df.to_csv(path, index=False, encoding="utf-8-sig")

    print(f"[저장] 리뷰 CSV: {path}")