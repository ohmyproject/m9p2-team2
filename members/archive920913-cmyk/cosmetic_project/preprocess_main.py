import os
import re
import pandas as pd

from crawler.config import DATA_DIR
from preprocess.preprocess_all_columns import (
    preprocess_product_file,
    preprocess_review_file,
)


def read_csv_safely(path):
    try:
        return pd.read_csv(path, dtype=str, encoding="utf-8-sig", nrows=5).fillna("")
    except UnicodeDecodeError:
        return pd.read_csv(path, dtype=str, encoding="cp949", nrows=5).fillna("")
    except Exception:
        return pd.read_csv(path, dtype=str, nrows=5).fillna("")


def get_columns(path):
    try:
        df = read_csv_safely(path)
        return list(df.columns)
    except Exception:
        return []


def has_review_shape(columns):
    if "review_text" in columns:
        return True

    review_cols = [
        "review_rating",
        "skin_type",
        "review_text",
    ]

    score = 0

    for col in review_cols:
        if col in columns:
            score += 1

    return score >= 2


def has_product_shape(columns):
    if "review_text" in columns:
        return False

    product_cols = [
        "brand",
        "product_name",
        "volume_ml",
        "regular_price",
        "sales_price",
        "ingredients",
        "url",
    ]

    score = 0

    for col in product_cols:
        if col in columns:
            score += 1

    return score >= 5


def is_cleaned_file(filename):
    return "_cleaned" in filename


def is_csv_file(filename):
    return filename.lower().endswith(".csv")


def is_product_csv(path):
    filename = os.path.basename(path)

    if not is_csv_file(filename):
        return False

    if is_cleaned_file(filename):
        return False

    columns = get_columns(path)

    if has_review_shape(columns):
        return False

    if has_product_shape(columns):
        return True

    # 기존 cosmetic_project 방식
    if "_Data(oliveyoung)_" in filename:
        return True

    # A 방식
    if "(info)" in filename:
        return True

    return False


def is_review_csv(path):
    filename = os.path.basename(path)

    if not is_csv_file(filename):
        return False

    if is_cleaned_file(filename):
        return False

    columns = get_columns(path)

    if has_review_shape(columns):
        return True

    # 기존 cosmetic_project 방식
    if "_Review(oliveyoung)_" in filename:
        return True

    # A 방식
    if "(review)" in filename:
        return True

    return False


def remove_retry_suffix(filename):
    base, ext = os.path.splitext(filename)

    if base.endswith("_retry"):
        base = base[:-6]

    return base + ext


def normalize_group_key(path, kind):
    """
    원본과 _retry를 같은 파일 그룹으로 묶기 위한 key.

    예:
    oliveyoung_판매순(info)_260501.csv
    oliveyoung_판매순(info)_260501_retry.csv
    → 같은 key

    리뷰 파일은 (info)로 잘못 저장된 경우도 (review) 기준으로 보정.
    """
    filename = os.path.basename(path)
    filename = remove_retry_suffix(filename)

    if kind == "review":
        filename = filename.replace("(info)", "(review)")
        filename = filename.replace("_Data(oliveyoung)_", "_Review(oliveyoung)_")

    return filename


def file_score(path):
    """
    같은 그룹에서 어떤 파일을 전처리할지 결정.
    _retry 파일 우선.
    _save 파일은 retry 다음 우선.
    """
    filename = os.path.basename(path)

    score = 0

    if "_retry" in filename:
        score += 100

    if "_save" in filename:
        score += 50

    return score


def select_effective_files(files, kind):
    """
    원본과 _retry가 둘 다 있으면 _retry만 선택.
    """
    grouped = {}

    for path in files:
        key = normalize_group_key(path, kind)

        if key not in grouped:
            grouped[key] = path
            continue

        if file_score(path) > file_score(grouped[key]):
            grouped[key] = path

    return sorted(grouped.values())


def find_target_files():
    product_candidates = []
    review_candidates = []

    if not os.path.exists(DATA_DIR):
        return [], []

    for filename in os.listdir(DATA_DIR):
        path = os.path.join(DATA_DIR, filename)

        if not os.path.isfile(path):
            continue

        if is_product_csv(path):
            product_candidates.append(path)
            continue

        if is_review_csv(path):
            review_candidates.append(path)
            continue

    product_files = select_effective_files(product_candidates, kind="product")
    review_files = select_effective_files(review_candidates, kind="review")

    return product_files, review_files


def main():
    print("=" * 70)
    print("CSV 최종 전처리")
    print("=" * 70)

    product_files, review_files = find_target_files()

    if not product_files and not review_files:
        print("[중단] 전처리할 CSV 파일이 없습니다.")
        return

    print("[상품 CSV 대상]")
    for path in product_files:
        print("-", os.path.basename(path))

    print("[리뷰 CSV 대상]")
    for path in review_files:
        print("-", os.path.basename(path))

    print("=" * 70)

    for path in product_files:
        preprocess_product_file(path)

    for path in review_files:
        preprocess_review_file(path)

    print("=" * 70)
    print("[완료] CSV 최종 전처리 종료")


if __name__ == "__main__":
    main()