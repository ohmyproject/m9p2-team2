import os
import re
import pandas as pd


DATA_DIR = "Data"


def read_csv_safely(path):
    try:
        return pd.read_csv(path, dtype=str, encoding="utf-8-sig").fillna("")
    except UnicodeDecodeError:
        return pd.read_csv(path, dtype=str, encoding="cp949").fillna("")
    except Exception:
        return pd.read_csv(path, dtype=str).fillna("")


def is_product_csv(filename):
    if not filename.endswith(".csv"):
        return False

    if "_cleaned" in filename:
        return False

    if "Review" in filename or "review" in filename:
        return False

    if "(review)" in filename:
        return False

    if "_Data(oliveyoung)_" in filename:
        return True

    if "(info)" in filename:
        return True

    return False


def has_korean(text):
    return bool(re.search(r"[가-힣]", str(text)))


def split_outside_parentheses(text):
    result = []
    current = ""
    depth = 0

    for char in str(text):
        if char == "(":
            depth += 1
            current += char
            continue

        if char == ")":
            depth = max(0, depth - 1)
            current += char
            continue

        if char == "," and depth == 0:
            item = current.strip()

            if item:
                result.append(item)

            current = ""
            continue

        current += char

    last = current.strip()

    if last:
        result.append(last)

    return result


def get_representative_name(item):
    item = str(item).strip()

    if "(" in item:
        return item.split("(", 1)[0].strip()

    return item.strip()


def should_clear_main_ingredients(value):
    value = str(value).strip()

    if value == "":
        return False

    items = split_outside_parentheses(value)

    for item in items:
        rep_name = get_representative_name(item)

        if has_korean(rep_name):
            return True

    return False


def main():
    if not os.path.exists(DATA_DIR):
        print("[중단] Data 폴더가 없습니다.")
        return

    total_files = 0
    total_rows = 0

    for filename in os.listdir(DATA_DIR):
        if not is_product_csv(filename):
            continue

        path = os.path.join(DATA_DIR, filename)
        df = read_csv_safely(path)

        if "main_ingredients" not in df.columns:
            continue

        changed = 0

        for index, row in df.iterrows():
            value = row.get("main_ingredients", "")

            if should_clear_main_ingredients(value):
                df.loc[index, "main_ingredients"] = ""
                changed += 1

        if changed > 0:
            df.to_csv(path, index=False, encoding="utf-8-sig")
            total_files += 1
            total_rows += changed
            print(f"[초기화] {filename} / {changed}개")

    print("=" * 70)
    print("[완료]")
    print(f"수정 파일 수: {total_files}")
    print(f"초기화 row 수: {total_rows}")


if __name__ == "__main__":
    main()