from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import DEFAULT_OUTPUT_DIR, SORT_MAP

KST = ZoneInfo("Asia/Seoul")


# ============================================================
# 1. 시간 관련 함수
# ============================================================

def now_iso() -> str:
    """현재 시각을 ISO 형식 문자열로 반환합니다."""
    return datetime.now(KST).isoformat(timespec="seconds")


def today_ymd_suffix() -> str:
    """
    파일명에 붙일 한국 시간 기준 YYMMDD를 반환합니다.

    예: 2026-04-30 실행 → 260430
    """
    return datetime.now(KST).strftime("%y%m%d")


# ============================================================
# 2. 텍스트 정리 함수
# ============================================================

def clean_text(text) -> str:
    """
    크롤링한 텍스트에서 불필요한 공백, 줄바꿈, 탭을 제거합니다.

    예: '  제품명 \\n 설명  ' → '제품명 설명'
    """
    if not text:
        return ""
    text = str(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_img_url(src: str) -> str:
    """
    다이소몰 이미지 URL의 상대경로를 절대경로로 변환합니다.

    예:
    //cdn.daisomall.co.kr/... → https://cdn.daisomall.co.kr/...
    /images/...              → https://cdn.daisomall.co.kr/images/...
    """
    src = clean_text(src)
    if not src:
        return ""
    if src.startswith("//"):
        return "https:" + src
    if src.startswith("/"):
        return "https://cdn.daisomall.co.kr" + src
    return src


# ============================================================
# 3. 용량 추출 함수
# ============================================================

def extract_volume_ml(product_name: str) -> str:
    """
    상품명에서 단일 용량(ml)을 추출합니다.

    예: '본셉 비타씨 에센스 100 ml' → '100'
    소수점이 .0으로 끝나면 제거합니다.
    """
    if not product_name:
        return ""

    match = re.search(r"(\d+(?:\.\d+)?)\s*(ml|mL|ML|㎖)", product_name)

    if not match:
        return ""

    value = match.group(1)

    if value.endswith(".0"):
        value = value[:-2]

    return value


# ============================================================
# 4. 전성분 텍스트 정리 함수
# ============================================================

def clean_ingredients_advanced(text: str) -> str:
    """
    OCR로 추출한 전성분 텍스트를 정리합니다.

    - 특수문자 제거 (전성분 목록에 불필요한 문자)
    - 5자 이상 연속 대문자/숫자 패턴 제거 (OCR 오인식 노이즈)
    """
    if not text:
        return ""

    text = re.sub(r"[^\w가-힣,\-\(\)\s/%\.\*\[\]]", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\b[A-Z0-9\|]{5,}\b", "", text)

    return clean_text(text)


# ============================================================
# 5. 정렬 파싱 함수
# ============================================================

def parse_sorts(sorts: str) -> list[tuple[str, str, str]]:
    """
    사용자가 입력한 정렬 옵션을 SORT_MAP 기준으로 변환합니다.

    입력: 'best,new'
    출력: [('SALE_QTY_DESC', '판매량순', 'best'), ('NEW_PRDT_DESC', '신상품순', 'new')]

    반환값 구조:
    url_param  : 카테고리 URL ?srt= 에 들어가는 값
    button_text: 페이지 내 정렬 버튼 텍스트
    sort_key   : 파일명 등에 사용할 원본 키
    """
    result = []

    for raw_key in sorts.split(","):
        key = raw_key.strip()

        if not key:
            continue

        if key not in SORT_MAP:
            raise ValueError(f"지원하지 않는 정렬 키입니다: {key}")

        url_param, button_text, label = SORT_MAP[key]
        result.append((url_param, button_text, key))

    return result


def sort_label(sort_key: str) -> str:
    """
    정렬 키를 파일명에 들어갈 한글 레이블로 변환합니다.

    예: 'best' → '판매량순'
    """
    if sort_key in SORT_MAP:
        return SORT_MAP[sort_key][2]
    return sort_key


# ============================================================
# 6. 저장 경로 생성 함수
# ============================================================

def make_output_path(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    kind: str = "info",
    sort_key: str = "new",
    source: str = "daiso",
) -> Path:
    """
    CSV 저장 경로를 생성합니다.

    예:
    Data/daiso_신상품순(info)_260430.csv
    Data/daiso_판매량순(review)_260430.csv
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    today = today_ymd_suffix()
    label = sort_label(sort_key)
    file_name = f"{source}_{label}({kind})_{today}.csv"

    return output_dir / file_name
