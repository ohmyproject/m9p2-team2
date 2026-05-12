import os
import re
import pandas as pd

from crawler.config import DATA_DIR


PRODUCT_REQUIRED_COLUMNS = [
    "product_name",
    "brand",
    "volume_ml",
    "regular_price",
    "sales_price",
    "ingredients",
    "url",
]

REVIEW_REQUIRED_COLUMNS = [
    "product_name",
    "review_text",
    "review_rating",
    "skin_type",
    "url",
]


def read_csv_safely(path):
    try:
        return pd.read_csv(path, dtype=str, encoding="utf-8-sig").fillna("")
    except UnicodeDecodeError:
        return pd.read_csv(path, dtype=str, encoding="cp949").fillna("")
    except Exception:
        return pd.read_csv(path, dtype=str).fillna("")


def is_empty(value):
    try:
        if pd.isna(value):
            return True
    except Exception:
        pass

    text = str(value).strip()
    return text == "" or text.lower() in ["nan", "none", "null"]


def to_int(value):
    try:
        text = str(value).strip()

        if text == "":
            return 0

        text = text.replace(",", "")
        text = text.replace("원", "")
        text = re.sub(r"[^0-9.\-]", "", text)

        if text in ["", "-", ".", "-."]:
            return 0

        return int(float(text))

    except Exception:
        return 0


def get_columns(path):
    try:
        df = read_csv_safely(path)
        return list(df.columns)
    except Exception:
        return []


def has_product_shape(columns):
    """
    상품 CSV인지 컬럼 구조로 판단.
    리뷰 컬럼 review_text가 있으면 상품으로 보지 않음.
    """

    if "review_text" in columns:
        return False

    score = 0

    for col in PRODUCT_REQUIRED_COLUMNS:
        if col in columns:
            score += 1

    return score >= 5


def has_review_shape(columns):
    """
    리뷰 CSV인지 컬럼 구조로 판단.
    파일명이 아니라 review_text/review_rating/skin_type 기준.
    """

    if "review_text" in columns:
        return True

    score = 0

    for col in REVIEW_REQUIRED_COLUMNS:
        if col in columns:
            score += 1

    return score >= 3


def is_product_csv(path):
    name = os.path.basename(path)

    if not name.endswith(".csv"):
        return False

    if "_cleaned" in name:
        return False

    columns = get_columns(path)

    if has_review_shape(columns):
        return False

    return has_product_shape(columns)


def is_review_csv(path):
    name = os.path.basename(path)

    if not name.endswith(".csv"):
        return False

    if "_cleaned" in name:
        return False

    columns = get_columns(path)

    return has_review_shape(columns)


def remove_retry_suffix(filename):
    base, ext = os.path.splitext(filename)

    if base.endswith("_retry"):
        base = base[:-6]

    return base + ext


def normalize_file_group_key(path, kind):
    """
    원본과 _retry를 같은 그룹으로 묶기 위한 key 생성.

    예:
    2026..._Data(oliveyoung)_판매순.csv
    2026..._Data(oliveyoung)_판매순_retry.csv
    → 같은 key

    oliveyoung_판매순(info)_260505.csv
    oliveyoung_판매순(info)_260505_retry.csv
    → 같은 key
    """

    name = os.path.basename(path)
    name = remove_retry_suffix(name)

    if kind == "review":
        # 잘못된 info retry 리뷰 파일도 review 그룹으로 보정
        name = name.replace("(info)", "(review)")
        name = name.replace("_Data(oliveyoung)_", "_Review(oliveyoung)_")

    return name


def file_score(path):
    """
    같은 그룹 안에서 어떤 파일을 우선 쓸지 결정.
    _retry가 있으면 _retry 우선.
    단, _save 파일은 그 다음 우선.
    """

    name = os.path.basename(path)
    score = 0

    if "_retry" in name:
        score += 100

    if "_save" in name:
        score += 50

    return score


def select_effective_files(files, kind):
    """
    원본과 _retry 중 하나만 선택.
    같은 그룹이면 _retry 우선.
    """

    grouped = {}

    for path in files:
        key = normalize_file_group_key(path, kind)

        if key not in grouped:
            grouped[key] = path
            continue

        if file_score(path) > file_score(grouped[key]):
            grouped[key] = path

    return sorted(grouped.values())


def find_csv_files():
    """
    Data 폴더에서 상품/리뷰 CSV를 찾되,
    원본과 _retry가 둘 다 있으면 _retry만 반환한다.

    이 함수가 핵심.
    retry_main.py는 이 결과만 사용하므로
    원본과 retry를 둘 다 재수집하지 않는다.
    """

    if not os.path.exists(DATA_DIR):
        return [], []

    product_candidates = []
    review_candidates = []

    for name in os.listdir(DATA_DIR):
        path = os.path.join(DATA_DIR, name)

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


def get_column_data(df, column):
    if column not in df.columns:
        return []

    data = df[column]

    if isinstance(data, pd.DataFrame):
        data = data.iloc[:, 0]

    return data.tolist()


def count_empty(df, column):
    if column not in df.columns:
        return len(df)

    count = 0

    for value in get_column_data(df, column):
        if is_empty(value):
            count += 1

    return count


def count_zero(df, column):
    if column not in df.columns:
        return len(df)

    count = 0

    for value in get_column_data(df, column):
        if to_int(value) == 0:
            count += 1

    return count


def validate_product_file(path):
    df = read_csv_safely(path)

    result = {
        "file": path,
        "total": len(df),
        "url_empty": count_empty(df, "url"),
        "product_name_empty": count_empty(df, "product_name"),
        "brand_empty": count_empty(df, "brand"),
        "volume_empty": count_empty(df, "volume_ml"),
        "ingredients_empty": count_empty(df, "ingredients"),
        "main_ingredients_empty": count_empty(df, "main_ingredients"),
        "rating_zero": count_zero(df, "rating"),
        "review_count_zero": count_zero(df, "review_count"),
        "sales_price_zero": count_zero(df, "sales_price"),
        "regular_price_zero": count_zero(df, "regular_price"),
    }

    return result


def validate_review_file(path, target_reviews=10):
    df = read_csv_safely(path)

    if "review_text" not in df.columns:
        review_text_empty = len(df)
    else:
        review_text_empty = count_empty(df, "review_text")

    if "product_name" in df.columns and "review_text" in df.columns:
        valid = df[~df["review_text"].apply(is_empty)]

        if len(valid) > 0:
            counts = valid.groupby("product_name").size()
            lack_count = int((counts < target_reviews).sum())
        else:
            lack_count = 0
    else:
        lack_count = 0

    result = {
        "file": path,
        "total": len(df),
        "review_text_empty": int(review_text_empty),
        "products_lack_reviews": lack_count,
    }

    return result


def print_product_report(result):
    print("=" * 70)
    print("[상품 CSV 검증]")
    print(os.path.basename(result["file"]))
    print(f"총 상품 수: {result['total']}")
    print(f"url 빈 값: {result['url_empty']}")
    print(f"product_name 빈 값: {result['product_name_empty']}")
    print(f"brand 빈 값: {result['brand_empty']}")
    print(f"volume_ml 빈 값: {result['volume_empty']}")
    print(f"ingredients 빈 값: {result['ingredients_empty']}")
    print(f"main_ingredients 빈 값: {result['main_ingredients_empty']}")
    print(f"rating 0: {result['rating_zero']}")
    print(f"review_count 0: {result['review_count_zero']}")
    print(f"sales_price 0: {result['sales_price_zero']}")
    print(f"regular_price 0: {result['regular_price_zero']}")


def print_review_report(result):
    print("=" * 70)
    print("[리뷰 CSV 검증]")
    print(os.path.basename(result["file"]))
    print(f"총 리뷰 수: {result['total']}")
    print(f"review_text 빈 값: {result['review_text_empty']}")
    print(f"목표 리뷰 수 미달 상품 수: {result['products_lack_reviews']}")


def run_validation(target_reviews=10):
    product_files, review_files = find_csv_files()

    if not product_files and not review_files:
        print("[검증] Data 폴더에 CSV 파일이 없습니다.")
        return

    print("=" * 70)
    print("[검증 대상 상품 CSV - 원본/retry 중 최종 선택본만 표시]")
    for path in product_files:
        print("-", os.path.basename(path))

    print("[검증 대상 리뷰 CSV - 원본/retry 중 최종 선택본만 표시]")
    for path in review_files:
        print("-", os.path.basename(path))

    for path in product_files:
        print_product_report(validate_product_file(path))

    for path in review_files:
        print_review_report(validate_review_file(path, target_reviews))

    print("=" * 70)
    print("[검증 완료]")