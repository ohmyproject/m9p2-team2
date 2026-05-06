from __future__ import annotations

import re
from io import BytesIO

import requests
from PIL import Image

from .common import clean_ingredients_advanced, clean_text
from .config import REQUEST_HEADERS


# ============================================================
# ocr.py
# ------------------------------------------------------------
# 역할:
# - Tesseract OCR로 이미지에서 텍스트 추출
# - OCR 결과에서 전성분 파트만 추출
# - 전성분 텍스트 정리
#
# 왜 따로 분리하는가?
# - OCR 로직은 상품 수집 흐름과 독립적입니다.
# - 추후 GPT Vision 등으로 교체하더라도 이 파일만 수정하면 됩니다.
# ============================================================


def setup_tesseract(cmd: str) -> None:
    """
    Tesseract 실행 파일 경로를 설정합니다.

    pytesseract가 설치되어 있지 않으면 조용히 무시합니다.
    """
    try:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = cmd
    except ImportError:
        pass


def extract_text_from_image(url: str) -> str:
    """
    이미지 URL에서 텍스트를 OCR로 추출합니다.

    이미지가 너무 길면 4000px 단위로 잘라서 처리합니다.
    너비가 1200px 미만이면 2배로 확대해 OCR 정확도를 높입니다.

    Returns
    -------
    추출된 텍스트 문자열, 실패 시 'OCR_FAIL: ...' 형식의 문자열
    """
    if not url:
        return ""

    try:
        import pytesseract
    except ImportError:
        return "OCR_FAIL: pytesseract not installed"

    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=30)
        response.raise_for_status()

        image = Image.open(BytesIO(response.content)).convert("RGB")
        width, height = image.size
        max_height = 4000
        texts: list[str] = []

        for y in range(0, height, max_height):
            crop = image.crop((0, y, width, min(y + max_height, height)))

            cw, ch = crop.size

            if cw < 1200:
                crop = crop.resize((cw * 2, ch * 2))

            crop = crop.convert("L")

            text = pytesseract.image_to_string(
                crop,
                lang="kor+eng",
                config="--psm 6",
            )

            texts.append(text)

        return clean_text("\n".join(texts))

    except Exception as e:
        return f"OCR_FAIL: {e}"


def extract_ingredients_only(text: str) -> str:
    """
    OCR 텍스트에서 전성분 파트만 추출합니다.

    탐색 순서:
    1. '전성분:' 또는 '전성분：' 이후 텍스트
    2. '모든 성분' 이후 텍스트
    3. '정제수,' 로 시작하는 텍스트 (전성분이 정제수부터 시작하는 경우)

    이후 주의사항/품질보증 등의 키워드를 만나면 잘라냅니다.
    """
    if not text:
        return ""

    if text.startswith("OCR_FAIL"):
        return text

    match = re.search(r"전성분[:：]?\s*(.+)", text)

    if not match:
        match = re.search(r"모든\s*성분\s*(.+)", text)

    if not match:
        match = re.search(r"(정제수\s*,.+)", text)

    if not match:
        return ""

    ingredients = match.group(1)

    ingredients = re.split(
        r"사용할\s*때|사용할때|사용시|사용 시|주의사항|품질\s*보증|품질보증"
        r"|소비자\s*상담|고객상담|제조국|화장품법|식품의약품안전처"
        r"|용법/용량|용법용량",
        ingredients,
    )[0]

    return clean_text(ingredients)


def extract_main_ingredients_gpt(desc_images: list[str], api_key: str) -> str:
    """
    상품 상세 이미지에서 GPT-4o Vision으로 강조된 핵심 성분을 추출합니다.

    이미지 앞쪽 최대 3장을 base64로 인코딩해 GPT에 전달합니다.
    시각적으로 강조(큰 글자·별도 박스·아이콘 등)된 성분 1~3개를
    한글로, 쉼표 구분 문자열로 반환합니다.

    Returns
    -------
    예: "나이아신아마이드, 히알루론산"  /  실패 시 빈 문자열
    """
    if not desc_images or not api_key:
        return ""

    try:
        import base64
        from openai import OpenAI

        client = OpenAI(api_key=api_key)

        image_contents = []
        for url in desc_images[:3]:
            try:
                resp = requests.get(url, headers=REQUEST_HEADERS, timeout=20)
                resp.raise_for_status()
                b64 = base64.b64encode(resp.content).decode()
                image_contents.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                })
            except Exception:
                continue

        if not image_contents:
            return ""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "화장품 상세 이미지입니다. "
                            "시각적으로 강조(큰 글자·별도 박스·아이콘 등)된 핵심 성분을 "
                            "한글로 1~3개만 추출하세요. "
                            "쉼표로 구분해서만 답하고, 없으면 빈 문자열로 답하세요."
                        ),
                    },
                    *image_contents,
                ],
            }],
            max_tokens=60,
        )

        result = response.choices[0].message.content.strip().strip("\"'.")
        return result

    except Exception as e:
        return f"GPT_FAIL: {e}"


def get_ingredients(desc_images: list[str]) -> tuple[str, str]:
    """
    상세 설명 이미지 목록에서 전성분을 추출합니다.

    전성분 이미지는 보통 상세 이미지의 마지막에 위치하므로
    마지막 이미지를 우선 사용합니다.

    Returns
    -------
    (ingredients, ing_source):
    - ingredients : 정리된 전성분 문자열
    - ing_source  : 'OCR' / 'OCR_EMPTY' / 'OCR_FAIL'
    """
    ingredient_img = desc_images[-1] if desc_images else ""

    ocr_text = extract_text_from_image(ingredient_img)
    ingredients_raw = extract_ingredients_only(ocr_text)
    ingredients_clean = clean_ingredients_advanced(ingredients_raw)

    if ocr_text.startswith("OCR_FAIL"):
        ing_source = "OCR_FAIL"
    elif ingredients_clean:
        ing_source = "OCR"
    else:
        ing_source = "OCR_EMPTY"

    return ingredients_clean, ing_source
