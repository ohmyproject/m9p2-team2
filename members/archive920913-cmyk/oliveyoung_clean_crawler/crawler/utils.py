# 문자 정리, 날짜, 가격 정리 같은 공통 기능입니다.

# crawler/utils.py

import re
from datetime import datetime


def today():
    return datetime.now().strftime("%Y-%m-%d")


def now_time():
    return datetime.now().strftime("%H%M%S")


def clean_text(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def only_number(text):
    if not text:
        return ""
    return re.sub(r"[^0-9]", "", str(text))


def extract_volume(text):
    if not text:
        return ""

    text = clean_text(text)

    # 증정/리필 용량은 먼저 제거
    text = re.sub(r"\([^)]*(증정|리필|샘플|추가|\+)[^)]*\)", " ", text)
    text = re.sub(r"\[[^\]]*(증정|리필|샘플|추가|\+)[^\]]*\]", " ", text)

    match = re.search(r"(\d+(?:\.\d+)?)\s*(ml|mL|ML|g|G)", text)

    if not match:
        return ""

    num = match.group(1)
    unit = match.group(2).lower()

    return f"{num}{unit}"