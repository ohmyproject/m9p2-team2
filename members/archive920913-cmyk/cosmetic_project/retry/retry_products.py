import os
import time
import pandas as pd

from selenium.webdriver.common.by import By

from crawler.browser import create_driver
from crawler.product_detail import collect_product_detail


def is_empty(value):
    if pd.isna(value):
        return True

    return str(value).strip() == ""


def to_int(value):
    try:
        text = str(value).replace(",", "").replace("원", "").strip()

        if text == "":
            return 0

        return int(float(text))

    except Exception:
        return 0


def safe_str(value):
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    return str(value)


def needs_product_retry(row):
    checks = [
        is_empty(row.get("volume_ml", "")),
        is_empty(row.get("ingredients", "")),
        to_int(row.get("rating", 0)) == 0,
        to_int(row.get("review_count", 0)) == 0,
        to_int(row.get("sales_price", 0)) == 0,
        to_int(row.get("regular_price", 0)) == 0,
    ]

    if is_empty(row.get("url", "")):
        return False

    return any(checks)


def wait_product_page(driver, product_name="", max_wait=8):
    """
    상품 상세 페이지가 실제로 뜰 때까지 확인한다.
    URL만 보고 성공 처리하지 않는다.
    """

    start_time = time.time()

    while time.time() - start_time < max_wait:
        wait_if_human_check(driver)

        if is_product_page_ready(driver, product_name):
            print("  [페이지 확인] 상품 상세 화면 확인 완료")
            return True

        time.sleep(0.5)

    print("  [페이지 확인] 자동 확인 실패")

    while True:
        print("=" * 70)
        print("[수동 확인 필요]")
        print("브라우저 화면을 확인하세요.")
        print("1. 사람입니다 화면이면 직접 체크하세요.")
        print("2. 상품 상세 페이지가 완전히 보일 때까지 기다리세요.")
        print("3. 상품명, 리뷰, 상품정보 제공고시, 장바구니 등이 보이면 Enter를 누르세요.")
        input("상품 페이지 확인 후 Enter: ")

        time.sleep(1)

        wait_if_human_check(driver)

        if is_product_page_ready(driver, product_name):
            print("  [페이지 확인] 수동 확인 후 상품 상세 화면 확인 완료")
            return True

        print("  [안내] 아직 상품 상세 화면으로 확인되지 않습니다.")
        retry = input("그래도 수집을 진행할까요? [y/n, 기본값: n]: ").strip().lower()

        if retry == "y":
            print("  [수동 진행] 사용자가 진행 선택")
            return True


def is_product_page_ready(driver, product_name=""):
    """
    실제 상품 상세 화면인지 확인한다.
    URL만으로는 성공 처리하지 않는다.
    """

    try:
        body = driver.find_element(By.TAG_NAME, "body")
        body_text = body.text
    except Exception:
        return False

    if not body_text or len(body_text.strip()) < 50:
        return False

    lower_text = body_text.lower()

    block_keywords = [
        "사람인지 확인",
        "사람입니다",
        "로봇이 아닙니다",
        "보안 확인",
        "자동입력 방지",
        "captcha",
        "verify",
        "verification",
        "checking your browser",
    ]

    if any(keyword.lower() in lower_text for keyword in block_keywords):
        return False

    if product_name:
        candidates = make_product_name_candidates(product_name)

        for candidate in candidates:
            if candidate and candidate in body_text:
                return True

    page_keywords = [
        "상품정보 제공고시",
        "전성분",
        "리뷰",
        "장바구니",
        "구매하기",
        "바로구매",
        "배송정보",
        "상품설명",
    ]

    hit_count = 0

    for keyword in page_keywords:
        if keyword in body_text:
            hit_count += 1

    if hit_count >= 2:
        return True

    return False


def make_product_name_candidates(product_name):
    text = str(product_name).strip()

    remove_words = [
        "[",
        "]",
        "(",
        ")",
        "+",
        "기획",
        "단독",
        "NEW",
        "new",
        "최저가",
        "런칭",
        "대용량",
        "증정",
        "더블",
    ]

    for word in remove_words:
        text = text.replace(word, " ")

    text = " ".join(text.split())

    candidates = []

    if len(text) >= 10:
        candidates.append(text[:10])

    if len(text) >= 8:
        candidates.append(text[:8])

    if len(text) >= 6:
        candidates.append(text[:6])

    words = text.split()

    for word in words:
        if len(word) >= 4:
            candidates.append(word)

    return list(dict.fromkeys(candidates))


def wait_if_human_check(driver):
    """
    사람 확인 / 보안 확인 화면이면 자동 진행하지 않고 멈춘다.
    """

    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text
    except Exception:
        return

    lower_text = body_text.lower()

    keywords = [
        "사람인지 확인",
        "사람입니다",
        "로봇이 아닙니다",
        "보안 확인",
        "자동입력 방지",
        "captcha",
        "verify",
        "verification",
        "checking your browser",
    ]

    detected = any(keyword.lower() in lower_text for keyword in keywords)

    if not detected:
        return

    while True:
        print("=" * 70)
        print("[사람 확인 화면 감지]")
        print("브라우저에서 직접 '사람입니다' 체크를 완료하세요.")
        print("상품 상세 페이지가 정상적으로 보이면 Enter를 누르세요.")
        input("완료 후 Enter: ")

        time.sleep(2)

        try:
            after_text = driver.find_element(By.TAG_NAME, "body").text
        except Exception:
            return

        lower_after = after_text.lower()
        still_detected = any(keyword.lower() in lower_after for keyword in keywords)

        if not still_detected:
            print("[확인] 사람 확인 화면 통과")
            return

        print("[안내] 아직 사람 확인 화면으로 보입니다. 다시 확인해주세요.")


def normalize_detail(detail):
    if not isinstance(detail, dict):
        return {}

    result = {}

    for key, value in detail.items():
        result[key] = safe_str(value)

    return result


def update_product_row(df, index, detail):
    for key, value in detail.items():
        if key not in df.columns:
            df[key] = ""

        value = safe_str(value)
        old_value = safe_str(df.at[index, key])

        if is_empty(old_value):
            df.at[index, key] = value
            continue

        if key in [
            "rating",
            "review_count",
            "regular_price",
            "sales_price",
            "discount",
        ]:
            if to_int(old_value) == 0 and not is_empty(value):
                df.at[index, key] = value

    return df


def make_retry_path(path):
    base, ext = os.path.splitext(path)

    if base.endswith("_retry"):
        return path

    return f"{base}_retry{ext}"


def retry_product_file(path):
    df = pd.read_csv(path, dtype=str).fillna("")

    targets = df[df.apply(needs_product_retry, axis=1)]

    print("=" * 70)
    print("[상품 재수집]")
    print(os.path.basename(path))
    print(f"총 상품 수: {len(df)}")
    print(f"재수집 대상: {len(targets)}")

    if len(targets) == 0:
        print("[상품 재수집] 대상 없음")
        return path

    driver = create_driver()

    success = 0
    fail = 0
    output_path = make_retry_path(path)

    try:
        for index, row in targets.iterrows():
            product_name = str(row.get("product_name", "")).strip()
            url = str(row.get("url", "")).strip()

            print("-" * 70)
            print(f"[상품 재수집] {index + 1} / {product_name}")

            try:
                print("  [이동] 상품 상세 페이지 접속")
                driver.get(url)

                wait_product_page(
                    driver=driver,
                    product_name=product_name,
                    max_wait=8,
                )

                print("  [상품 정보 수집 시작]")
                detail = collect_product_detail(driver)
                detail = normalize_detail(detail)

                df = update_product_row(df, index, detail)

                success += 1
                print("[성공] 상품 정보 업데이트")

                df = df.astype(str)
                df.to_csv(output_path, index=False, encoding="utf-8-sig")
                print(f"  [중간 저장] {os.path.basename(output_path)}")

                time.sleep(1)

            except Exception as e:
                fail += 1
                print("[실패]", e)

                df = df.astype(str)
                df.to_csv(output_path, index=False, encoding="utf-8-sig")
                print(f"  [실패 후 중간 저장] {os.path.basename(output_path)}")

                time.sleep(2)

    finally:
        try:
            driver.quit()
        except Exception:
            pass

    df = df.astype(str)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print("=" * 70)
    print("[상품 재수집 결과]")
    print(f"성공: {success}")
    print(f"실패: {fail}")
    print(f"저장: {output_path}")

    return output_path