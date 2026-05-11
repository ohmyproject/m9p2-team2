# CSV 파일명과 컬럼 순서를 고정합니다.

import os
import pandas as pd

from crawler.config import DATA_DIR, PRODUCT_COLUMNS, REVIEW_COLUMNS
from crawler.utils import today, now_time


def make_filename(kind, sort_type):
    sort_name = str(sort_type).replace(" ", "")

    if kind == "product":
        name = f"{today()}_{now_time()}_Data(oliveyoung)_{sort_name}.csv"
    else:
        name = f"{today()}_{now_time()}_Review(oliveyoung)_{sort_name}.csv"

    return os.path.join(DATA_DIR, name)


def save_product_csv(rows, sort_type):
    filename = make_filename("product", sort_type)
    df = pd.DataFrame(rows)

    for col in PRODUCT_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df = df[PRODUCT_COLUMNS]
    df.to_csv(filename, index=False, encoding="utf-8-sig")

    return filename


def save_review_csv(rows, sort_type):
    filename = make_filename("review", sort_type)
    df = pd.DataFrame(rows)

    for col in REVIEW_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df = df[REVIEW_COLUMNS]
    df.to_csv(filename, index=False, encoding="utf-8-sig")

    return filename