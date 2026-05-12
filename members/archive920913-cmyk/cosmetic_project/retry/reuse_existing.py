import os
import re
from urllib.parse import urlparse, parse_qs

import pandas as pd

from crawler.config import DATA_DIR, REVIEW_COLUMNS


PRODUCT_COPY_COLUMNS = [
    "brand",
    "volume_ml",
    "regular_price",
    "discount",
    "sales_price",
    "rating",
    "review_count",
    "main_ingredients",
    "ingredients",
    "ing_source",
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
        text = str(value).replace(",", "").replace("원", "").strip()
        text = re.sub(r"[^0-9.\-]", "", text)

        if text in ["", "-", ".", "-."]:
            return 0

        return int(float(text))
    except Exception:
        return 0


def is_zero_or_empty(value):
    if is_empty(value):
        return True

    return to_int(value) == 0


def extract_goods_no_from_url(url):
    if is_empty(url):
        return ""

    try:
        parsed = urlparse(str(url))
        query = parse_qs(parsed.query)
        goods_no = query.get("goodsNo", [])

        if goods_no:
            return goods_no[0]

    except Exception:
        pass

    match = re.search(r"goodsNo=([^&]+)", str(url))

    if match:
        return match.group(1).strip()

    return ""


def get_goods_key(row):
    for col in ["goodsNo", "goods_no", "goods_no"]:
        if col in row and not is_empty(row.get(col, "")):
            return str(row.get(col, "")).strip()

    goods_no = extract_goods_no_from_url(row.get("url", ""))

    if goods_no:
        return goods_no

    product_name = str(row.get("product_name", "")).strip()
    brand = str(row.get("brand", "")).strip()

    if product_name and brand:
        return f"{brand}::{product_name}"

    if product_name:
        return f"NAME::{product_name}"

    return ""


def has_product_shape(path):
    try:
        df = read_csv_safely(path)
    except Exception:
        return False

    columns = set(df.columns)

    if "review_text" in columns:
        return False

    product_signals = [
        "brand",
        "volume_ml",
        "regular_price",
        "sales_price",
        "ingredients",
        "url",
    ]

    score = sum(1 for col in product_signals if col in columns)

    return score >= 4


def has_review_shape(path):
    try:
        df = read_csv_safely(path)
    except Exception:
        return False

    columns = set(df.columns)

    return (
        "review_text" in columns
        or "review_rating" in columns
        or "skin_type" in columns
    )


def make_retry_path(path):
    base, ext = os.path.splitext(path)

    if base.endswith("_retry"):
        return path

    return f"{base}_retry{ext}"


def make_review_retry_path_from_product(product_file, review_file=None):
    product_dir = os.path.dirname(product_file)

    if review_file and has_review_shape(review_file):
        base, ext = os.path.splitext(review_file)

        if base.endswith("_retry"):
            return review_file

        return f"{base}_retry{ext}"

    name = os.path.basename(product_file)

    base, ext = os.path.splitext(name)

    if base.endswith("_retry"):
        base = base[:-6]

    if "_Data(oliveyoung)_" in base:
        base = base.replace("_Data(oliveyoung)_", "_Review(oliveyoung)_")
        return os.path.join(product_dir, f"{base}_retry{ext}")

    if "(info)" in base:
        base = base.replace("(info)", "(review)")
        return os.path.join(product_dir, f"{base}_retry{ext}")

    return os.path.join(product_dir, f"{base}_review_retry{ext}")


def score_product_row(row):
    score = 0

    for col in PRODUCT_COPY_COLUMNS:
        value = row.get(col, "")

        if col in ["regular_price", "sales_price", "rating", "review_count"]:
            if not is_zero_or_empty(value):
                score += 2
        else:
            if not is_empty(value):
                score += 2

    ingredients = str(row.get("ingredients", "")).strip()
    score += min(len(ingredients) // 50, 10)

    main_ingredients = str(row.get("main_ingredients", "")).strip()
    score += min(len(main_ingredients) // 20, 5)

    return score


def build_product_history(product_files):
    history = {}

    for path in product_files:
        if not has_product_shape(path):
            continue

        try:
            df = read_csv_safely(path)
        except Exception:
            continue

        for _, row in df.iterrows():
            key = get_goods_key(row)

            if not key:
                continue

            row_dict = row.to_dict()
            row_score = score_product_row(row_dict)

            if key not in history:
                history[key] = {
                    "score": row_score,
                    "row": row_dict,
                    "source": path,
                }
                continue

            if row_score > history[key]["score"]:
                history[key] = {
                    "score": row_score,
                    "row": row_dict,
                    "source": path,
                }

    return history


def fill_product_file_from_history(path, history):
    if not has_product_shape(path):
        return path, 0

    df = read_csv_safely(path)

    changed = 0

    for index, row in df.iterrows():
        key = get_goods_key(row)

        if not key:
            continue

        if key not in history:
            continue

        source_row = history[key]["row"]

        for col in PRODUCT_COPY_COLUMNS:
            if col not in df.columns:
                df[col] = ""

            old_value = row.get(col, "")

            if col in ["regular_price", "sales_price", "rating", "review_count"]:
                needs_fill = is_zero_or_empty(old_value)
            else:
                needs_fill = is_empty(old_value)

            if not needs_fill:
                continue

            new_value = source_row.get(col, "")

            if is_empty(new_value):
                continue

            if col in ["regular_price", "sales_price", "rating", "review_count"]:
                if is_zero_or_empty(new_value):
                    continue

            df.at[index, col] = str(new_value)
            changed += 1

    if changed > 0:
        output_path = make_retry_path(path)
        df = df.astype(str)
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        return output_path, changed

    return path, 0


def normalize_review_row(review_row, product_row):
    result = {}

    for col in REVIEW_COLUMNS:
        result[col] = ""

    result["date"] = str(product_row.get("date", review_row.get("date", ""))).strip()
    result["platform"] = str(product_row.get("platform", review_row.get("platform", "oliveyoung"))).strip()
    result["sort_type"] = str(product_row.get("sort_type", review_row.get("sort_type", ""))).strip()
    result["rank"] = str(product_row.get("rank", review_row.get("rank", ""))).strip()
    result["main_ingredients"] = str(
        product_row.get(
            "main_ingredients",
            review_row.get("main_ingredients", ""),
        )
    ).strip()
    result["product_name"] = str(product_row.get("product_name", review_row.get("product_name", ""))).strip()
    result["review_count"] = str(product_row.get("review_count", review_row.get("review_count", ""))).strip()
    result["review_rating"] = str(review_row.get("review_rating", "")).strip()
    result["skin_type"] = str(review_row.get("skin_type", "")).strip()
    result["review_text"] = str(review_row.get("review_text", "")).strip()
    result["url"] = str(product_row.get("url", review_row.get("url", ""))).strip()

    return result


def build_review_history(review_files):
    history = {}

    for path in review_files:
        if not has_review_shape(path):
            continue

        try:
            df = read_csv_safely(path)
        except Exception:
            continue

        if "review_text" not in df.columns:
            continue

        for _, row in df.iterrows():
            review_text = str(row.get("review_text", "")).strip()

            if not review_text:
                continue

            key = get_goods_key(row)

            if not key:
                product_name = str(row.get("product_name", "")).strip()

                if not product_name:
                    continue

                key = f"NAME::{product_name}"

            if key not in history:
                history[key] = []

            exists = any(
                old.get("review_text", "") == review_text
                for old in history[key]
            )

            if not exists:
                history[key].append(row.to_dict())

    return history


def find_matching_review_file(product_file, review_files):
    product_name = os.path.basename(product_file)
    product_dir = os.path.dirname(product_file)

    candidates = []

    name1 = product_name.replace("_Data(oliveyoung)_", "_Review(oliveyoung)_")
    name1 = remove_retry_suffix(name1)
    candidates.append(os.path.join(product_dir, name1))

    name2 = product_name.replace("(info)", "(review)")
    name2 = remove_retry_suffix(name2)
    candidates.append(os.path.join(product_dir, name2))

    for candidate in candidates:
        if os.path.exists(candidate) and has_review_shape(candidate):
            return candidate

    sort_type = extract_sort_type(product_file)
    date_key = extract_date_key(product_file)

    for path in review_files:
        if not has_review_shape(path):
            continue

        name = os.path.basename(path)

        if "(info)" in name:
            continue

        if sort_type and sort_type not in name:
            continue

        if date_key and date_key not in name:
            continue

        return path

    return None


def remove_retry_suffix(name):
    base, ext = os.path.splitext(name)

    if base.endswith("_retry"):
        base = base[:-6]

    return base + ext


def extract_sort_type(path):
    name = os.path.basename(path)

    if "_Data(oliveyoung)_" in name:
        value = name.split("_Data(oliveyoung)_", 1)[1]
        value = value.replace(".csv", "")
        value = value.replace("_retry", "")
        value = value.replace("_cleaned", "")
        return value

    if name.startswith("oliveyoung_") and "(info)" in name:
        part = name.replace("oliveyoung_", "")
        part = part.split("(info)", 1)[0]
        return part.strip("_")

    return ""


def extract_date_key(path):
    name = os.path.basename(path)

    match = re.search(r"_(\d{6})(?:_retry)?(?:_cleaned)?\.csv$", name)

    if match:
        return match.group(1)

    match = re.search(r"(\d{4}-\d{2}-\d{2})", name)

    if match:
        return match.group(1)

    return ""


def count_reviews_for_product(review_df, product_name):
    if review_df is None or len(review_df) == 0:
        return 0

    if "product_name" not in review_df.columns or "review_text" not in review_df.columns:
        return 0

    matched = review_df[
        (review_df["product_name"].astype(str) == str(product_name))
        & (review_df["review_text"].astype(str).str.strip() != "")
    ]

    return len(matched)


def fill_review_file_from_history(product_file, review_files, review_history, target_reviews):
    if not has_product_shape(product_file):
        return None, 0

    product_df = read_csv_safely(product_file)

    review_file = find_matching_review_file(product_file, review_files)

    if review_file:
        review_df = read_csv_safely(review_file)
    else:
        review_df = pd.DataFrame(columns=REVIEW_COLUMNS)

    added_rows = []

    for _, product_row in product_df.iterrows():
        product_name = str(product_row.get("product_name", "")).strip()

        if not product_name:
            continue

        current_count = count_reviews_for_product(review_df, product_name)

        if current_count >= target_reviews:
            continue

        key = get_goods_key(product_row)

        candidates = []

        if key and key in review_history:
            candidates.extend(review_history[key])

        name_key = f"NAME::{product_name}"

        if name_key in review_history:
            candidates.extend(review_history[name_key])

        if not candidates:
            continue

        need_count = target_reviews - current_count

        existing_texts = set()

        if "review_text" in review_df.columns:
            existing_texts.update(
                review_df["review_text"].astype(str).str.strip().tolist()
            )

        for review_row in candidates:
            review_text = str(review_row.get("review_text", "")).strip()

            if not review_text:
                continue

            if review_text in existing_texts:
                continue

            added_rows.append(
                normalize_review_row(
                    review_row=review_row,
                    product_row=product_row,
                )
            )

            existing_texts.add(review_text)
            need_count -= 1

            if need_count <= 0:
                break

    if not added_rows:
        return review_file, 0

    new_df = pd.DataFrame(added_rows)

    for col in REVIEW_COLUMNS:
        if col not in review_df.columns:
            review_df[col] = ""

        if col not in new_df.columns:
            new_df[col] = ""

    review_df = review_df.reindex(columns=REVIEW_COLUMNS)
    new_df = new_df.reindex(columns=REVIEW_COLUMNS)

    output_df = pd.concat([review_df, new_df], ignore_index=True)

    output_path = make_review_retry_path_from_product(product_file, review_file)
    output_df = output_df.astype(str)
    output_df.to_csv(output_path, index=False, encoding="utf-8-sig")

    return output_path, len(added_rows)


def prefill_from_existing(product_files, review_files, target_reviews=10):
    print("=" * 70)
    print("[0단계] 기존 CSV 데이터 재사용")
    print("같은 goodsNo / 상품명 기준으로 상품정보와 리뷰를 먼저 복사합니다.")

    product_history = build_product_history(product_files)
    review_history = build_review_history(review_files)

    print(f"[상품정보 이력] {len(product_history)}개 상품")
    print(f"[리뷰 이력] {len(review_history)}개 상품")

    total_product_filled = 0
    updated_product_files = []

    print("-" * 70)
    print("[상품정보 기존 값 복사]")

    for path in product_files:
        output_path, changed = fill_product_file_from_history(path, product_history)

        if changed > 0:
            print(f"- {os.path.basename(path)} → {os.path.basename(output_path)} / {changed}칸 채움")
            updated_product_files.append(output_path)
            total_product_filled += changed
        else:
            print(f"- {os.path.basename(path)} / 복사할 값 없음")

    total_review_added = 0
    updated_review_files = []

    print("-" * 70)
    print("[리뷰 기존 값 복사]")

    effective_product_files = list(dict.fromkeys(product_files + updated_product_files))

    for path in effective_product_files:
        output_path, added = fill_review_file_from_history(
            product_file=path,
            review_files=review_files,
            review_history=review_history,
            target_reviews=target_reviews,
        )

        if added > 0:
            print(f"- {os.path.basename(path)} → {os.path.basename(output_path)} / 리뷰 {added}개 복사")
            updated_review_files.append(output_path)
            total_review_added += added
        else:
            print(f"- {os.path.basename(path)} / 복사할 리뷰 없음")

    print("=" * 70)
    print("[기존 데이터 재사용 완료]")
    print(f"상품정보 채운 칸 수: {total_product_filled}")
    print(f"리뷰 복사 개수: {total_review_added}")

    return updated_product_files, updated_review_files