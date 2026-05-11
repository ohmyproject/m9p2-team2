import json
import re
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI


# =========================================
# 0. OpenAI API 준비
# =========================================
# .env 파일 안에 OPENAI_API_KEY=본인키 형태로 저장되어 있어야 함
load_dotenv()
client = OpenAI()


# =========================================
# 1. 자주 나오는 성분 기본 번역 사전
# GPT 비용 줄이기용
# =========================================
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
}


# =========================================
# 2. CSV 안전하게 읽기
# =========================================
def read_csv_safely(file_path):
    """
    CSV가 utf-8-sig인지 cp949인지 모를 때 안전하게 읽기
    """

    try:
        return pd.read_csv(file_path, encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv(file_path, encoding="cp949")


# =========================================
# 3. URL에서 goodsNo 추출
# =========================================
def extract_goods_no(url):
    """
    예시 입력:
    https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=A000000255624&dispCatNo=...

    예시 출력:
    A000000255624
    """

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


# =========================================
# 4. goodsNo 컬럼을 platform 바로 뒤에 추가
# =========================================
def add_goods_no_column(df):
    if "url" not in df.columns:
        print("url 컬럼이 없어서 goodsNo 생성 건너뜀")
        return df

    if "platform" not in df.columns:
        print("platform 컬럼이 없어서 goodsNo 위치 삽입 건너뜀")
        return df

    # 이미 goodsNo 컬럼이 있으면 삭제 후 다시 생성
    # 이렇게 해야 중복 컬럼이 생기지 않고, 위치도 platform 바로 뒤로 고정됨
    if "goodsNo" in df.columns:
        df = df.drop(columns=["goodsNo"])

    goods_no_series = df["url"].apply(extract_goods_no)

    platform_index = df.columns.get_loc("platform")

    df.insert(
        loc=platform_index + 1,
        column="goodsNo",
        value=goods_no_series
    )

    return df


# =========================================
# 5. 상품명 전처리
# =========================================
def clean_product_name(product_name):
    """
    상품명에서 앞쪽 마케팅 태그, 뒤쪽 구성품 문구를 제거함

    예:
    [리뉴얼/속수분쏙] 리얼베리어 워터리 히알 세럼 50ml 기획 (+20ml)
    → 리얼베리어 워터리 히알 세럼 50ml

    [기미잡티세럼] 레이어랩 기미흔적 클리어 세럼 30ml
    → 레이어랩 기미흔적 클리어 세럼 30ml

    [글로벌 대란템/올영선런칭] 유세린 티아미돌 부스터 세럼 30ml
    → 유세린 티아미돌 부스터 세럼 30ml

    [5월올영픽/포켓몬 에디션] 닥터지 레드블레미쉬 클리어 히알 시카 수딩 세럼 50ml 기획 (리필50ml+꼬부기파우치)
    → 닥터지 레드블레미쉬 클리어 히알 시카 수딩 세럼 50ml
    """

    if pd.isna(product_name):
        return ""

    name = str(product_name).strip()

    if name == "":
        return ""

    # 양쪽 따옴표 제거
    name = name.strip('"').strip("'").strip()

    # 맨 앞의 [리뉴얼], [기미잡티세럼], [1+1 리필기획] 같은 태그 제거
    # 여러 개가 연속으로 있어도 제거됨
    name = re.sub(r"^\s*(?:\[[^\]]*\]\s*)+", "", name)

    # 괄호 안 구성품 제거
    # 예: (+20ml), (리필50ml+꼬부기파우치)
    name = re.sub(r"\([^)]*\)", "", name)

    # 대괄호가 중간이나 뒤에 남아있을 경우 제거
    name = re.sub(r"\[[^\]]*\]", "", name)

    # 맨 끝의 기획 제거
    # 예: 세럼 50ml 기획 → 세럼 50ml
    name = re.sub(r"\s*기획\s*$", "", name)

    # 맨 끝의 단품 제거
    name = re.sub(r"\s*단품\s*$", "", name)

    # 맨 끝의 세트 제거
    name = re.sub(r"\s*세트\s*$", "", name)

    # 공백 정리
    name = re.sub(r"\s+", " ", name).strip()

    return name


# =========================================
# 6. product_name_clean 컬럼 추가
# =========================================
def add_product_name_clean_column(df):
    if "product_name" not in df.columns:
        print("product_name 컬럼이 없어서 상품명 전처리 건너뜀")
        return df

    # 이미 있으면 삭제 후 다시 생성
    if "product_name_clean" in df.columns:
        df = df.drop(columns=["product_name_clean"])

    clean_series = df["product_name"].apply(clean_product_name)

    product_name_index = df.columns.get_loc("product_name")

    # product_name 바로 뒤에 product_name_clean 추가
    df.insert(
        loc=product_name_index + 1,
        column="product_name_clean",
        value=clean_series
    )

    return df


# =========================================
# 7. main_ingredients 괄호 제거 전처리
# =========================================
def simplify_main_ingredients(text):
    """
    예시 입력:
    Peptide(Copper Tripeptide-1, Dipeptide Diaminobutyroyl Benzylamide Diacetate),
    Bakuchiol(Bakuchiol),
    Collagen(Hydrolyzed Collagen)

    예시 출력:
    Peptide, Bakuchiol, Collagen

    핵심:
    괄호 안에도 쉼표가 있기 때문에 단순 split(",")를 쓰면 안 됨.
    """

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
            # 괄호 앞까지가 대표 성분명
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
            # 괄호 밖 쉼표는 성분 구분자
            current = ""

        else:
            # 괄호 밖 글자만 모음
            if bracket_depth == 0:
                current += char

    # 괄호 없이 끝난 값이 있으면 추가
    last = current.strip()

    if last:
        result.append(last)

    # 중복 제거
    unique_result = []

    for item in result:
        item = item.strip()

        if item and item not in unique_result:
            unique_result.append(item)

    return ", ".join(unique_result)


# =========================================
# 8. main_ingredients 컬럼 자체를 괄호 제거된 값으로 변경
# =========================================
def simplify_main_ingredients_column(df):
    if "main_ingredients" not in df.columns:
        print("main_ingredients 컬럼이 없어서 성분 괄호 제거 건너뜀")
        return df

    df["main_ingredients"] = df["main_ingredients"].apply(
        simplify_main_ingredients
    )

    return df


# =========================================
# 9. main_ingredients에서 고유 성분명 모으기
# =========================================
def collect_unique_ingredients(series):
    """
    예:
    Peptide, Bakuchiol
    Peptide, Collagen

    결과:
    ["Peptide", "Bakuchiol", "Collagen"]
    """

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


# =========================================
# 10. GPT로 사전에 없는 성분만 번역
# =========================================
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
        }
    )

    result_text = response.output_text

    try:
        translation_dict = json.loads(result_text)
    except json.JSONDecodeError:
        print("GPT 응답을 JSON으로 변환하지 못했습니다.")
        print(result_text)
        raise

    return translation_dict


# =========================================
# 11. 한 행의 main_ingredients를 한글로 바꾸기
# =========================================
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


# =========================================
# 12. main_ingredients_kor 컬럼 추가
# =========================================
def add_main_ingredients_kor_column(df):
    if "main_ingredients" not in df.columns:
        print("main_ingredients 컬럼이 없어서 한글 성분 컬럼 생성 건너뜀")
        return df

    # 이미 있으면 삭제 후 다시 생성
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

    # main_ingredients 바로 뒤에 main_ingredients_kor 추가
    main_ing_index = df.columns.get_loc("main_ingredients")

    df.insert(
        loc=main_ing_index + 1,
        column="main_ingredients_kor",
        value=kor_series
    )

    return df


# =========================================
# 13. CSV 파일 하나 전체 전처리
# =========================================
def preprocess_one_csv(input_path, overwrite_file=False):
    input_path = Path(input_path)

    df = read_csv_safely(input_path)

    print(f"처리 중: {input_path.name}")

    # 1. goodsNo 추가
    df = add_goods_no_column(df)

    # 2. 상품명 정리 컬럼 추가
    df = add_product_name_clean_column(df)

    # 3. main_ingredients 괄호 제거
    df = simplify_main_ingredients_column(df)

    # 4. 한글 성분 컬럼 추가
    df = add_main_ingredients_kor_column(df)

    # 저장 경로
    if overwrite_file:
        output_path = input_path
    else:
        output_path = input_path.with_name(input_path.stem + "_cleaned.csv")

    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"저장 완료: {output_path}")
    print()


# =========================================
# 14. Data 폴더 전체 CSV 처리
# =========================================
if __name__ == "__main__":

    data_dir = Path("Data")

    csv_files = [
        file for file in data_dir.glob("*.csv")
        if "_cleaned" not in file.stem
        and "_goodsNo" not in file.stem
        and "_kor" not in file.stem
        and "_preprocessed" not in file.stem
    ]

    if not csv_files:
        print("처리할 CSV 파일이 없습니다.")

    for csv_file in csv_files:
        print("=" * 80)

        preprocess_one_csv(
            input_path=csv_file,
            overwrite_file=False
        )