import os
import re
import json
import time
import base64
import tempfile

import pandas as pd
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from crawler.browser import create_driver


def clean_text(value):
    if value is None:
        return ""

    return re.sub(r"\s+", " ", str(value)).strip()


def is_empty(value):
    if pd.isna(value):
        return True

    return str(value).strip() == ""


def read_csv_auto(path):
    for enc in ("utf-8-sig", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, encoding=enc, dtype=str).fillna("")
        except UnicodeDecodeError:
            continue

    return pd.read_csv(path, dtype=str).fillna("")


def find_target_products(df, recrawl_all=False):
    if "main_ingredients" not in df.columns:
        df["main_ingredients"] = ""

    if recrawl_all:
        target_df = df
    else:
        target_df = df[df["main_ingredients"].astype(str).str.strip() == ""]

    products = []
    seen_urls = set()

    for index, row in target_df.iterrows():
        url = clean_text(row.get("url", ""))

        if not url or url in seen_urls:
            continue

        seen_urls.add(url)

        products.append(
            {
                "index": index,
                "url": url,
                "product_name": clean_text(row.get("product_name", "")),
                "ingredients": clean_text(row.get("ingredients", "")),
            }
        )

    return products


def get_detail(driver, url, product_name=""):
    for attempt in range(3):
        try:
            driver.get(url)

            wait_ocr_product_page(
                driver=driver,
                product_name=product_name,
                max_wait=10,
            )

            open_product_info_notice(driver)

            soup = BeautifulSoup(driver.page_source, "html.parser")

            ingredients = extract_ingredients(soup)
            image_urls = collect_detail_image_urls(driver)

            print(f"  [상세 성공] 이미지:{len(image_urls)}개 성분:{len(ingredients)}자")

            if len(image_urls) == 0 and len(ingredients) == 0:
                print("  [상세 확인 실패] 이미지와 성분이 모두 0개입니다.")
                print("  [수동 확인] 브라우저에서 상품 상세 페이지가 보이면 Enter를 누르세요.")
                input("상품 상세 확인 후 Enter: ")

                open_product_info_notice(driver)

                soup = BeautifulSoup(driver.page_source, "html.parser")
                ingredients = extract_ingredients(soup)
                image_urls = collect_detail_image_urls(driver)

                print(f"  [재확인] 이미지:{len(image_urls)}개 성분:{len(ingredients)}자")

            return {
                "ingredients": ingredients,
                "image_urls": image_urls,
            }

        except Exception as error:
            print(f"  [상세 시도 {attempt + 1}/3 실패] {str(error)[:120]}")
            time.sleep(2)

    return {
        "ingredients": "",
        "image_urls": [],
    }

def wait_ocr_product_page(driver, product_name="", max_wait=10):
    start_time = time.time()

    while time.time() - start_time < max_wait:
        wait_if_human_check_for_ocr(driver)

        if is_ocr_product_page_ready(driver, product_name):
            print("  [페이지 확인] OCR용 상품 상세 화면 확인 완료")
            return True

        time.sleep(0.5)

    print("  [페이지 확인] OCR용 상품 상세 자동 확인 실패")
    print("=" * 70)
    print("[수동 확인 필요]")
    print("브라우저 화면을 확인하세요.")
    print("1. 사람입니다 화면이면 직접 체크하세요.")
    print("2. 상품 상세 페이지가 완전히 보일 때까지 기다리세요.")
    print("3. 상품 이미지나 상품정보 제공고시가 보이면 Enter를 누르세요.")
    input("상품 페이지 확인 후 Enter: ")

    time.sleep(1)
    wait_if_human_check_for_ocr(driver)

    return True


def is_ocr_product_page_ready(driver, product_name=""):
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text
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
        candidates = make_ocr_product_name_candidates(product_name)

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
        "상품설명",
        "상세정보",
    ]

    hit_count = 0

    for keyword in page_keywords:
        if keyword in body_text:
            hit_count += 1

    if hit_count >= 2:
        return True

    try:
        images = driver.find_elements(By.TAG_NAME, "img")
        olive_images = 0

        for img in images:
            src = (
                img.get_attribute("src")
                or img.get_attribute("data-src")
                or img.get_attribute("data-original")
                or ""
            )

            if "oliveyoung.co.kr" in src:
                olive_images += 1

        if olive_images >= 3:
            return True

    except Exception:
        pass

    return False


def make_ocr_product_name_candidates(product_name):
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
        "올영픽",
        "5월",
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

    for word in text.split():
        if len(word) >= 4:
            candidates.append(word)

    return list(dict.fromkeys(candidates))


def wait_if_human_check_for_ocr(driver):
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


def open_product_info_notice(driver):
    try:
        buttons = driver.find_elements(By.TAG_NAME, "button")

        for button in buttons:
            text = clean_text(button.text)

            if "상품정보 제공고시" in text:
                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});",
                    button,
                )
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", button)
                time.sleep(1)
                return

    except Exception:
        pass


def extract_ingredients(soup):
    rows = soup.find_all("tr")

    labels = [
        "화장품법에 따라 기재해야 하는 모든 성분",
        "전성분",
        "모든 성분",
    ]

    for row in rows:
        th = row.find("th")
        td = row.find("td")

        if not th or not td:
            continue

        label = clean_text(th.get_text(" ", strip=True))
        value = clean_text(td.get_text(" ", strip=True))

        if any(key in label for key in labels):
            return value

    return ""


def collect_detail_image_urls(driver):
    urls = []
    seen = set()

    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(0.5)

    last_height = 0

    for _ in range(8):
        images = driver.find_elements(By.TAG_NAME, "img")

        for img in images:
            src = (
                img.get_attribute("src")
                or img.get_attribute("data-src")
                or img.get_attribute("data-original")
                or ""
            )

            src = clean_text(src)

            if not src:
                continue

            if "oliveyoung.co.kr" not in src:
                continue

            lower = src.lower()

            if any(skip in lower for skip in ["logo", "icon", "blank"]):
                continue

            if src in seen:
                continue

            seen.add(src)
            urls.append(src)

        driver.execute_script("window.scrollBy(0, 900);")
        time.sleep(0.5)

        height = driver.execute_script("return document.body.scrollHeight")

        if height == last_height:
            break

        last_height = height

    return urls


def extract_main_ingredients_with_gpt_ocr(product_name, image_urls, ingredients_text):
    load_dotenv()

    if not os.getenv("OPENAI_API_KEY"):
        print("  [GPT OCR 생략] OPENAI_API_KEY가 없습니다.")
        return ""

    image_urls = [clean_text(url) for url in image_urls if clean_text(url)]

    if not image_urls:
        print("  [GPT OCR 생략] 상세 이미지가 없습니다.")
        return ""

    client = OpenAI()

    prompt = (
        "You are a cosmetic ingredient analysis expert.\n\n"
        "Goal:\n"
        "Find key representative ingredients emphasized in the product detail images, "
        "then match them with actual cosmetic INCI ingredients.\n\n"
        "Very important rules:\n"
        "1. 대표성분명 must be English only.\n"
        "2. INCI_성분 must be English INCI-style names only.\n"
        "3. Do not write Korean in 대표성분명.\n"
        "4. Do not write Korean in INCI_성분.\n"
        "5. 업계표현 may be Korean if it appears in the image.\n"
        "6. Do not invent ingredients.\n"
        "7. If full ingredient text is provided, only include INCI ingredients supported by it.\n"
        "8. If full ingredient text is missing, use the detail images carefully and set confidence to medium or low.\n"
        "9. Do not force the number of ingredients.\n"
        "10. Exclude Water, Glycerin, Butylene Glycol, Dipropylene Glycol, Fragrance, "
        "colorants, simple preservatives, and pH adjusters unless clearly emphasized.\n\n"
        "Correct examples:\n"
        "- Niacinamide(Niacinamide)\n"
        "- Cica(Centella Asiatica Extract, Madecassoside)\n"
        "- Hyaluronic Acid(Sodium Hyaluronate, Hyaluronic Acid)\n"
        "- Ceramide(Ceramide NP)\n"
        "- Panthenol(Panthenol)\n"
        "- PDRN(Sodium DNA)\n\n"
        "Wrong examples:\n"
        "- 나이아신아마이드(Niacinamide)\n"
        "- 병풀(Centella Asiatica Extract)\n"
        "- 히알루론산(Sodium Hyaluronate)\n\n"
        "Return JSON only. Do not use markdown.\n\n"
        "{\n"
        "  \"representative_ingredients\": [\n"
        "    {\n"
        "      \"대표성분명\": \"English representative ingredient name only\",\n"
        "      \"업계표현\": \"marketing expression found in image\",\n"
        "      \"INCI_성분\": [\"English INCI ingredient name only\"],\n"
        "      \"선정근거\": \"short Korean reason\",\n"
        "      \"신뢰도\": \"high | medium | low\"\n"
        "    }\n"
        "  ],\n"
        "  \"not_found_or_uncertain\": [\n"
        "    {\n"
        "      \"홍보문구_성분명\": \"\",\n"
        "      \"사유\": \"\"\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        f"Product name:\n{product_name}\n\n"
        f"Full ingredients:\n{ingredients_text}"
    )

    try:
        content = [{"type": "text", "text": prompt}]

        with tempfile.TemporaryDirectory():
            added_count = 0

            for url in image_urls:
                image_data = download_image_for_openai(url)

                if not image_data:
                    continue

                mime_type, b64 = image_data

                content.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{b64}"
                        },
                    }
                )

                added_count += 1

        print(f"  [GPT 전송 이미지] {len(content) - 1}개")

        if len(content) == 1:
            print("  [GPT OCR 생략] 전송 가능한 이미지가 없습니다.")
            return ""

        response = client.chat.completions.create(
            model=os.getenv("OPENAI_OCR_MODEL", "gpt-4o-mini"),
            messages=[
                {
                    "role": "user",
                    "content": content,
                }
            ],
            temperature=0.1,
            max_tokens=2000,
        )

        return clean_main_ingredients_response(response.choices[0].message.content)

    except Exception as error:
        print(f"  [GPT OCR 실패] {str(error)[:200]}")
        return ""


def download_image_for_openai(url):
    try:
        if ".gif" in url.lower():
            print("  [이미지 제외] GIF URL 제외")
            return None

        response = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            },
            timeout=20,
        )

        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "").lower()

        if not content_type.startswith("image/"):
            print(f"  [이미지 제외] 이미지 응답 아님: {content_type}")
            return None

        if "gif" in content_type:
            print("  [이미지 제외] GIF 제외")
            return None

        if "svg" in content_type:
            print("  [이미지 제외] SVG 제외")
            return None

        if "webp" in content_type:
            mime_type = "image/webp"
        elif "png" in content_type:
            mime_type = "image/png"
        elif "jpeg" in content_type or "jpg" in content_type:
            mime_type = "image/jpeg"
        else:
            print(f"  [이미지 제외] 지원하지 않는 이미지 형식: {content_type}")
            return None

        if len(response.content) < 1024:
            print("  [이미지 제외] 이미지 크기가 너무 작음")
            return None

        b64 = base64.b64encode(response.content).decode("utf-8")

        if not b64:
            print("  [이미지 제외] base64 변환 실패")
            return None

        return mime_type, b64

    except Exception as error:
        print(f"  [이미지 다운로드 실패] {url[:80]} {str(error)[:80]}")
        return None


def clean_main_ingredients_response(value):
    text = clean_text(value)

    if not text:
        return ""

    text = text.replace("```json", "")
    text = text.replace("```", "")
    text = text.strip()

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]

    try:
        data = json.loads(text)
    except Exception as error:
        print(f"  [JSON 파싱 실패] {str(error)[:120]}")
        return ""

    items = data.get("representative_ingredients", [])
    results = []

    for item in items:
        rep_name = clean_text(item.get("대표성분명", ""))
        inci_list = item.get("INCI_성분", [])

        if not rep_name:
            continue

        rep_name = normalize_representative_name(rep_name)

        if isinstance(inci_list, list):
            inci_values = [
                normalize_inci_name(value)
                for value in inci_list
                if clean_text(value)
            ]
        else:
            inci_values = [normalize_inci_name(inci_list)]

        inci_values = [value for value in inci_values if value]

        if inci_values:
            results.append(f"{rep_name}({', '.join(inci_values)})")
        else:
            results.append(rep_name)

    return ", ".join(results)


def normalize_representative_name(value):
    text = clean_text(value)

    mapping = {
        "나이아신아마이드": "Niacinamide",
        "병풀": "Cica",
        "시카": "Cica",
        "히알루론산": "Hyaluronic Acid",
        "하이알루론산": "Hyaluronic Acid",
        "세라마이드": "Ceramide",
        "판테놀": "Panthenol",
        "레티놀": "Retinol",
        "바쿠치올": "Bakuchiol",
        "펩타이드": "Peptide",
        "콜라겐": "Collagen",
        "비타민C": "Vitamin C",
        "비타민 C": "Vitamin C",
        "피디알엔": "PDRN",
        "PDRN": "PDRN",
        "트라넥사믹애씨드": "Tranexamic Acid",
        "알부틴": "Arbutin",
        "징크": "Zinc PCA",
    }

    return mapping.get(text, text)


def normalize_inci_name(value):
    text = clean_text(value)

    mapping = {
        "나이아신아마이드": "Niacinamide",
        "병풀추출물": "Centella Asiatica Extract",
        "센텔라아시아티카추출물": "Centella Asiatica Extract",
        "마데카소사이드": "Madecassoside",
        "아시아티코사이드": "Asiaticoside",
        "마데카식애씨드": "Madecassic Acid",
        "아시아틱애씨드": "Asiatic Acid",
        "소듐하이알루로네이트": "Sodium Hyaluronate",
        "하이알루로닉애씨드": "Hyaluronic Acid",
        "하이드롤라이즈드하이알루로닉애씨드": "Hydrolyzed Hyaluronic Acid",
        "세라마이드엔피": "Ceramide NP",
        "판테놀": "Panthenol",
        "레티놀": "Retinol",
        "바쿠치올": "Bakuchiol",
        "아데노신": "Adenosine",
        "글루타티온": "Glutathione",
        "알부틴": "Arbutin",
        "알파-알부틴": "Alpha-Arbutin",
        "트라넥사믹애씨드": "Tranexamic Acid",
        "징크피씨에이": "Zinc PCA",
        "소듐디엔에이": "Sodium DNA",
        "하이드롤라이즈드콜라겐": "Hydrolyzed Collagen",
    }

    return mapping.get(text, text)

def extract_goods_no_from_url(url):
    text = str(url)

    patterns = [
        r"goodsNo=([^&]+)",
        r"goods_no=([^&]+)",
        r"/goods/([^/?]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            return match.group(1).strip()

    return ""


def get_goods_no_from_row(row):
    for col in ["goodsNo", "goods_no", "goods_no"]:
        if col in row and clean_text(row.get(col, "")):
            return clean_text(row.get(col, ""))

    return extract_goods_no_from_url(row.get("url", ""))


def is_product_csv(filename):
    return (
        "_Data(oliveyoung)_" in filename
        and filename.endswith(".csv")
        and "_cleaned" not in filename
    )


def build_main_ingredients_history(data_dir):
    history = {}

    if not os.path.exists(data_dir):
        return history

    for filename in os.listdir(data_dir):
        if not is_product_csv(filename):
            continue

        path = os.path.join(data_dir, filename)

        try:
            df = read_csv_auto(path)
        except Exception:
            continue

        if "main_ingredients" not in df.columns:
            continue

        for _, row in df.iterrows():
            main_value = clean_text(row.get("main_ingredients", ""))

            if not main_value:
                continue

            goods_no = get_goods_no_from_row(row)

            if not goods_no:
                continue

            old_value = history.get(goods_no, "")

            if not old_value:
                history[goods_no] = main_value
                continue

            if len(main_value) > len(old_value):
                history[goods_no] = main_value

    return history

def fill_main_ingredients_from_history(path, history):
    if not history:
        return 0

    df = read_csv_auto(path)

    if "main_ingredients" not in df.columns:
        df["main_ingredients"] = ""

    filled_count = 0

    for index, row in df.iterrows():
        current_value = clean_text(row.get("main_ingredients", ""))

        if current_value:
            continue

        goods_no = get_goods_no_from_row(row)

        if not goods_no:
            continue

        history_value = history.get(goods_no, "")

        if not history_value:
            continue

        df.loc[index, "main_ingredients"] = history_value
        filled_count += 1

    if filled_count > 0:
        df.to_csv(path, index=False, encoding="utf-8-sig")

    return filled_count

def process_csv(path, recrawl_all=False):
    print("=" * 70)
    print(f"[대상 CSV] {path}")

    df = read_csv_auto(path)

    if "main_ingredients" not in df.columns:
        df["main_ingredients"] = ""

    if "ingredients" not in df.columns:
        df["ingredients"] = ""

    df["main_ingredients"] = df["main_ingredients"].astype("object")
    df["ingredients"] = df["ingredients"].astype("object")

    targets = find_target_products(df, recrawl_all=recrawl_all)

    mode = "전체 재수집" if recrawl_all else "main_ingredients 누락만 재수집"

    print(f"[전체 행] {len(df)}")
    print(f"[모드] {mode}")
    print(f"[대상 상품] {len(targets)}개")

    if not targets:
        print("[완료] 재수집 대상이 없습니다.")
        return path

    driver = create_driver()

    try:
        for i, product in enumerate(targets, 1):
            index = product["index"]
            url = product["url"]
            product_name = product["product_name"]
            ingredients_text = product["ingredients"]

            print("-" * 70)
            print(f"[{i}/{len(targets)}] {product_name}")

            detail = get_detail(driver, url, product_name=product_name)

            if not ingredients_text:
                ingredients_text = detail.get("ingredients", "")

            image_urls = detail.get("image_urls", [])

            print(f"  [이미지] {len(image_urls)}개")

            main_ingredients = extract_main_ingredients_with_gpt_ocr(
                product_name=product_name,
                image_urls=image_urls,
                ingredients_text=ingredients_text,
            )

            if main_ingredients:
                df.loc[index, "main_ingredients"] = main_ingredients
                print(f"  [주성분] {main_ingredients!r} (1행 업데이트)")
            else:
                print("  [주성분] 빈 값이라 업데이트하지 않습니다.")

            df.to_csv(path, index=False, encoding="utf-8-sig")
            print(f"  [중간 저장] {os.path.basename(path)}")

    finally:
        try:
            driver.quit()
        except Exception:
            pass

    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"[저장 완료] {path}")

    return path