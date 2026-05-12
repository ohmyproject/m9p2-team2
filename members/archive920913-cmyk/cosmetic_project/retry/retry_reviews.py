import os
import re
import time
import random
import pandas as pd

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from crawler.browser import create_driver
from crawler.review_detail import collect_reviews
from crawler.config import REVIEW_COLUMNS


def read_csv_safely(path):
    try:
        return pd.read_csv(path, dtype=str, encoding="utf-8-sig").fillna("")
    except UnicodeDecodeError:
        return pd.read_csv(path, dtype=str, encoding="cp949").fillna("")
    except Exception:
        return pd.read_csv(path, dtype=str).fillna("")


def is_empty(value):
    if pd.isna(value):
        return True

    return str(value).strip() == ""


def to_int(value):
    try:
        text = str(value).replace(",", "").strip()
        return int(float(text)) if text else 0
    except Exception:
        return 0


def is_review_shaped_file(path):
    if not path or not os.path.exists(path):
        return False

    try:
        df = read_csv_safely(path)
    except Exception:
        return False

    return "review_text" in df.columns


def find_review_file(product_file, review_files):
    product_name = os.path.basename(product_file)
    product_dir = os.path.dirname(product_file)

    candidates = []

    name1 = product_name.replace("_Data(oliveyoung)_", "_Review(oliveyoung)_")
    name1 = name1.replace("_retry", "")
    candidates.append(os.path.join(product_dir, name1))

    name2 = product_name.replace("(info)", "(review)")
    name2 = name2.replace("_retry", "")
    candidates.append(os.path.join(product_dir, name2))

    name3 = product_name.replace("(info)", "(review)")
    name3 = name3.replace("_cleaned", "")
    name3 = name3.replace("_retry", "")
    candidates.append(os.path.join(product_dir, name3))

    for candidate in candidates:
        candidate_name = os.path.basename(candidate)

        if "(info)" in candidate_name:
            continue

        if candidate in review_files:
            return candidate

        if os.path.exists(candidate):
            return candidate

    sort_type = extract_sort_type(product_file)
    date_key = extract_date_key(product_file)

    for path in review_files:
        review_name = os.path.basename(path)

        if "(info)" in review_name:
            continue

        if "_Data(oliveyoung)_" in review_name:
            continue

        if sort_type and sort_type not in review_name:
            continue

        if date_key and date_key not in review_name:
            continue

        return path

    for path in review_files:
        review_name = os.path.basename(path)

        if "(info)" in review_name:
            continue

        if "_Data(oliveyoung)_" in review_name:
            continue

        if sort_type and sort_type in review_name:
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


def wait_product_page(driver, product_name="", max_wait=8):
    start_time = time.time()

    while time.time() - start_time < max_wait:
        wait_if_human_check(driver)

        if is_product_page_ready(driver, product_name):
            print("  [페이지 대기] 상품 상세 페이지 확인")
            return True

        time.sleep(0.5)

    print("  [페이지 대기] 자동 확인 실패")
    print("[수동 확인 필요] 상품 페이지가 보이면 Enter를 누르세요.")
    input("상품 페이지 확인 후 Enter: ")

    return True


def is_product_page_ready(driver, product_name=""):
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text
    except Exception:
        return False

    if not body_text or len(body_text.strip()) < 50:
        return False

    lower = body_text.lower()

    block_keywords = [
        "사람인지 확인",
        "사람입니다",
        "로봇이 아닙니다",
        "보안 확인",
        "자동입력 방지",
        "captcha",
        "verify",
        "verification",
    ]

    if any(keyword.lower() in lower for keyword in block_keywords):
        return False

    if product_name:
        for candidate in make_product_name_candidates(product_name):
            if candidate and candidate in body_text:
                return True

    page_keywords = [
        "리뷰",
        "상품정보 제공고시",
        "전성분",
        "장바구니",
        "구매하기",
        "바로구매",
    ]

    hit = 0

    for keyword in page_keywords:
        if keyword in body_text:
            hit += 1

    return hit >= 2


def make_product_name_candidates(product_name):
    text = str(product_name).strip()

    for word in [
        "[", "]", "(", ")", "+", "기획", "단독", "NEW", "new",
        "최저가", "런칭", "대용량", "증정", "더블",
    ]:
        text = text.replace(word, " ")

    text = " ".join(text.split())
    candidates = []

    if len(text) >= 10:
        candidates.append(text[:10])

    if len(text) >= 8:
        candidates.append(text[:8])

    if len(text) >= 6:
        candidates.append(text[:6])

    for word in text.split():
        if len(word) >= 4:
            candidates.append(word)

    return list(dict.fromkeys(candidates))


def wait_if_human_check(driver):
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text
    except Exception:
        return

    lower = body_text.lower()

    keywords = [
        "사람인지 확인",
        "사람입니다",
        "로봇이 아닙니다",
        "보안 확인",
        "자동입력 방지",
        "captcha",
        "verify",
        "verification",
    ]

    if not any(keyword.lower() in lower for keyword in keywords):
        return

    while True:
        print("=" * 70)
        print("[사람 확인 화면 감지]")
        print("브라우저에서 직접 체크하세요.")
        input("상품 상세 페이지가 보이면 Enter: ")

        time.sleep(2)

        try:
            after = driver.find_element(By.TAG_NAME, "body").text.lower()
        except Exception:
            return

        if not any(keyword.lower() in after for keyword in keywords):
            return


def count_existing_reviews(review_df, product_name):
    if review_df is None or len(review_df) == 0:
        return 0

    if "product_name" not in review_df.columns or "review_text" not in review_df.columns:
        return 0

    matched = review_df[
        (review_df["product_name"].astype(str) == str(product_name))
        & (~review_df["review_text"].apply(is_empty))
    ]

    return len(matched)


def needs_review_retry(product_row, review_df, target_reviews):
    url = product_row.get("url", "")
    product_name = product_row.get("product_name", "")
    review_count = to_int(product_row.get("review_count", 0))

    if is_empty(url):
        return False

    if is_empty(product_name):
        return False

    if review_count == 0:
        return False

    current_count = count_existing_reviews(review_df, product_name)

    return current_count < target_reviews


def retry_review_file(product_file, review_file, target_reviews=10):
    product_df = read_csv_safely(product_file)

    if review_file and os.path.exists(review_file) and is_review_shaped_file(review_file):
        review_df = read_csv_safely(review_file)
    else:
        review_file = None
        review_df = pd.DataFrame(columns=REVIEW_COLUMNS)

    targets = product_df[
        product_df.apply(
            lambda row: needs_review_retry(row, review_df, target_reviews),
            axis=1,
        )
    ]

    print("=" * 70)
    print("[리뷰 재수집]")
    print(os.path.basename(product_file))
    print(f"리뷰 파일: {os.path.basename(review_file) if review_file else '없음 - 새로 생성'}")
    print(f"총 상품 수: {len(product_df)}")
    print(f"리뷰 재수집 대상 상품 수: {len(targets)}")

    if len(targets) == 0:
        print("[리뷰 재수집] 대상 없음")
        return review_file

    driver = create_driver()
    new_rows = []
    success = 0
    fail = 0

    try:
        for _, row in targets.iterrows():
            product_name = str(row.get("product_name", "")).strip()
            url = str(row.get("url", "")).strip()

            print("-" * 70)
            print(f"[리뷰 재수집] {product_name}")

            try:
                print("  [이동] 상품 상세 페이지 접속")
                driver.get(url)

                wait_product_page(driver, product_name, max_wait=8)

                print("  [리뷰 수집 시작]")
                rows = collect_reviews(
                    driver,
                    row.to_dict(),
                    limit=target_reviews,
                )

                if rows:
                    new_rows.extend(rows)
                    success += 1
                    print(f"[성공] 리뷰 {len(rows)}개")
                else:
                    fail += 1
                    print("[실패] 리뷰 0개")

                polite_sleep(2.0, 4.0)

            except Exception as e:
                fail += 1
                print("[실패]", e)
                polite_sleep(3.0, 5.0)

    finally:
        try:
            driver.quit()
        except Exception:
            pass

    updated_df = replace_reviews(review_df, targets, new_rows)
    output_path = make_review_retry_path(product_file, review_file)
    updated_df = ensure_review_columns(updated_df)
    updated_df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print("=" * 70)
    print("[리뷰 재수집 결과]")
    print(f"시도 상품: {len(targets)}")
    print(f"성공 상품: {success}")
    print(f"실패 상품: {fail}")
    print(f"저장: {output_path}")

    return output_path


def polite_sleep(min_sec=2.0, max_sec=4.0):
    sec = random.uniform(min_sec, max_sec)
    print(f"  [대기] {sec:.1f}초")
    time.sleep(sec)


def replace_reviews(review_df, targets, new_rows):
    if "product_name" not in targets.columns:
        return review_df

    target_names = set(targets["product_name"].astype(str).tolist())

    if "product_name" in review_df.columns:
        review_df = review_df[
            ~review_df["product_name"].astype(str).isin(target_names)
        ]

    new_df = pd.DataFrame(new_rows)

    return pd.concat([review_df, new_df], ignore_index=True)


def ensure_review_columns(df):
    for col in REVIEW_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    return df.reindex(columns=REVIEW_COLUMNS)


def make_review_retry_path(product_file, review_file):
    product_dir = os.path.dirname(product_file)

    # review_file이 있어도 이름에 (info)가 들어가면 잘못 매칭된 것이므로 무시
    if review_file:
        review_name = os.path.basename(review_file)

        if "(info)" not in review_name and "_Data(oliveyoung)_" not in review_name:
            base, ext = os.path.splitext(review_file)

            if base.endswith("_retry"):
                return review_file

            return f"{base}_retry{ext}"

    # 여기부터는 product_file 기준으로 반드시 리뷰 파일명 생성
    name = os.path.basename(product_file)

    base, ext = os.path.splitext(name)

    if base.endswith("_retry"):
        base = base[:-6]

    # cosmetic_project 방식
    if "_Data(oliveyoung)_" in base:
        base = base.replace("_Data(oliveyoung)_", "_Review(oliveyoung)_")
        return os.path.join(product_dir, f"{base}_retry{ext}")

    # A 방식
    if "(info)" in base:
        base = base.replace("(info)", "(review)")
        return os.path.join(product_dir, f"{base}_retry{ext}")

    return os.path.join(product_dir, f"{base}_review_retry{ext}")