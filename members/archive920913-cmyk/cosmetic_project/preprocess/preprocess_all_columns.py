import json
import re
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()
client = OpenAI()


DEFAULT_TRANSLATION_DICT = {
    "Peptide": "펩타이드",
    "Bakuchiol": "바쿠치올",
    "Collagen": "콜라겐",
    "Hyaluronic Acid": "히알루로닉산",
    "Niacinamide": "나이아신아마이드",
    "Adenosine": "아데노신",
    "Tocopherol": "토코페롤",
    "Retinol": "레티놀",
    "Vitamin C": "비타민 C",
    "Ceramide": "세라마이드",
    "Panthenol": "판테놀",
    "Centella Asiatica": "병풀",
    "Madecassoside": "마데카소사이드",
    "Propolis": "프로폴리스",
    "Squalane": "스쿠알란",
    "Cica": "시카",
    "Tea Tree": "티트리",
    "Green Tea": "녹차",
    "Salicylic Acid": "살리실릭애씨드",
    "PHA": "PHA",
    "AHA": "AHA",
    "BHA": "BHA",
    "PDRN": "피디알엔",
    "Tranexamic Acid": "트라넥사믹애씨드",
    "Arbutin": "알부틴",
    "Alpha-Arbutin": "알파-알부틴",
    "Glutathione": "글루타티온",
    "Zinc PCA": "징크피씨에이",
}


def read_csv_safely(file_path):
    try:
        return pd.read_csv(file_path, encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv(file_path, encoding="cp949")


def extract_goods_no(url):
    if pd.isna(url):
        return ""

    url = str(url).strip()

    if url == "":
        return ""

    try:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        goods_no_list = query_params.get("goodsNo", [])

        if goods_no_list:
            return goods_no_list[0]

        return ""

    except Exception:
        return ""


def add_goods_no_column(df):
    if "url" not in df.columns:
        print("url 컬럼이 없어서 goodsNo 생성 건너뜀")
        return df

    if "platform" not in df.columns:
        print("platform 컬럼이 없어서 goodsNo 위치 삽입 건너뜀")
        return df

    if "goodsNo" in df.columns:
        df = df.drop(columns=["goodsNo"])

    goods_no_series = df["url"].apply(extract_goods_no)
    platform_index = df.columns.get_loc("platform")

    df.insert(
        loc=platform_index + 1,
        column="goodsNo",
        value=goods_no_series,
    )

    return df


def clean_product_name(product_name):
    if pd.isna(product_name):
        return ""

    name = str(product_name).strip()

    if name == "":
        return ""

    name = name.strip('"').strip("'").strip()

    name = re.sub(r"^\s*(?:\[[^\]]*\]\s*)+", "", name)
    name = re.sub(r"\([^)]*\)", "", name)
    name = re.sub(r"\[[^\]]*\]", "", name)
    name = re.sub(r"\s*기획\s*$", "", name)
    name = re.sub(r"\s*단품\s*$", "", name)
    name = re.sub(r"\s*세트\s*$", "", name)
    name = re.sub(r"\s+", " ", name).strip()

    return name


def add_product_name_clean_column(df):
    if "product_name" not in df.columns:
        print("product_name 컬럼이 없어서 상품명 전처리 건너뜀")
        return df

    if "product_name_clean" in df.columns:
        df = df.drop(columns=["product_name_clean"])

    clean_series = df["product_name"].apply(clean_product_name)
    product_name_index = df.columns.get_loc("product_name")

    df.insert(
        loc=product_name_index + 1,
        column="product_name_clean",
        value=clean_series,
    )

    return df


def simplify_main_ingredients(text):
    if pd.isna(text):
        return ""

    text = str(text).strip()

    if text == "":
        return ""

    result = []
    current = ""
    bracket_depth = 0

    for char in text:
        if char == "(":
            ingredient_name = current.strip()

            if ingredient_name:
                result.append(ingredient_name)

            current = ""
            bracket_depth += 1

        elif char == ")":
            if bracket_depth > 0:
                bracket_depth -= 1

            current = ""

        elif char == "," and bracket_depth == 0:
            current = ""

        else:
            if bracket_depth == 0:
                current += char

    last = current.strip()

    if last:
        result.append(last)

    unique_result = []

    for item in result:
        item = item.strip()

        if item and item not in unique_result:
            unique_result.append(item)

    return ", ".join(unique_result)


def simplify_main_ingredients_column(df):
    if "main_ingredients" not in df.columns:
        print("main_ingredients 컬럼이 없어서 성분 괄호 제거 건너뜀")
        return df

    df["main_ingredients"] = df["main_ingredients"].apply(
        simplify_main_ingredients
    )

    return df


def collect_unique_ingredients(series):
    unique_ingredients = []

    for value in series.dropna():
        value = str(value).strip()

        if value == "":
            continue

        parts = value.split(",")

        for part in parts:
            ingredient = part.strip()

            if ingredient and ingredient not in unique_ingredients:
                unique_ingredients.append(ingredient)

    return unique_ingredients


def translate_unknown_ingredients_with_gpt(ingredients):
    if not ingredients:
        return {}

    prompt = f"""
너는 화장품 성분명을 한국어로 번역하는 도우미야.

아래 영어 성분명 리스트를 자연스러운 한국어 화장품 성분명으로 번역해줘.

규칙:
1. 반드시 JSON 객체만 반환해.
2. 설명 문장은 쓰지 마.
3. key는 입력된 영어 성분명을 그대로 유지해.
4. value는 한국어 번역명으로 작성해.
5. 화장품 업계에서 자주 쓰는 표현을 우선해.
6. 너무 의역하지 말고 성분명으로 자연스럽게 번역해.
7. 이미 한국어이거나 약어인 값은 그대로 유지해.

영어 성분명 리스트:
{json.dumps(ingredients, ensure_ascii=False)}
"""

    response = client.responses.create(
        model="gpt-4o-mini",
        input=prompt,
        text={
            "format": {
                "type": "json_object"
            }
        },
    )

    result_text = response.output_text

    try:
        translation_dict = json.loads(result_text)
    except json.JSONDecodeError:
        print("GPT 응답을 JSON으로 변환하지 못했습니다.")
        print(result_text)
        raise

    return translation_dict


def apply_korean_translation(main_ingredients_text, translation_dict):
    if pd.isna(main_ingredients_text):
        return ""

    main_ingredients_text = str(main_ingredients_text).strip()

    if main_ingredients_text == "":
        return ""

    kor_list = []

    for item in main_ingredients_text.split(","):
        ingredient = item.strip()

        if ingredient == "":
            continue

        kor_name = translation_dict.get(ingredient, ingredient)
        kor_list.append(kor_name)

    return ", ".join(kor_list)


def add_main_ingredients_kor_column(df):
    if "main_ingredients" not in df.columns:
        print("main_ingredients 컬럼이 없어서 한글 성분 컬럼 생성 건너뜀")
        return df

    if "main_ingredients_kor" in df.columns:
        df = df.drop(columns=["main_ingredients_kor"])

    unique_ingredients = collect_unique_ingredients(df["main_ingredients"])

    unknown_ingredients = []

    for ingredient in unique_ingredients:
        if ingredient not in DEFAULT_TRANSLATION_DICT:
            unknown_ingredients.append(ingredient)

    print(f"전체 고유 성분 수: {len(unique_ingredients)}")
    print(f"GPT 번역 필요 성분 수: {len(unknown_ingredients)}")

    final_translation_dict = DEFAULT_TRANSLATION_DICT.copy()

    if unknown_ingredients:
        gpt_translation_dict = translate_unknown_ingredients_with_gpt(
            unknown_ingredients
        )
        final_translation_dict.update(gpt_translation_dict)

    kor_series = df["main_ingredients"].apply(
        lambda x: apply_korean_translation(x, final_translation_dict)
    )

    main_ing_index = df.columns.get_loc("main_ingredients")

    df.insert(
        loc=main_ing_index + 1,
        column="main_ingredients_kor",
        value=kor_series,
    )

    return df


def preprocess_one_csv(input_path, overwrite_file=False):
    input_path = Path(input_path)

    df = read_csv_safely(input_path)

    print(f"처리 중: {input_path.name}")

    df = add_goods_no_column(df)
    df = add_product_name_clean_column(df)
    df = simplify_main_ingredients_column(df)
    df = add_main_ingredients_kor_column(df)

    if overwrite_file:
        output_path = input_path
    else:
        output_path = input_path.with_name(input_path.stem + "_cleaned.csv")

    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"저장 완료: {output_path}")
    print()

    return output_path


def preprocess_product_file(path):
    return preprocess_one_csv(path, overwrite_file=False)


def preprocess_review_file(path):
    return preprocess_one_csv(path, overwrite_file=False)