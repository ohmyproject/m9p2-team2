import re
from datetime import datetime


def today():
    return datetime.now().strftime("%Y-%m-%d")


def now_stamp():
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


def clean_text(value):
    if value is None:
        return ""

    return re.sub(r"\s+", " ", str(value)).strip()


def clean_int(value):
    if value is None:
        return 0

    text = re.sub(r"[^0-9]", "", str(value))

    if text == "":
        return 0

    return int(text)


def extract_volume_ml(text):
    if not text:
        return ""

    pattern = r"(\d+(?:\.\d+)?)\s*(ml|mL|ML)"
    match = re.search(pattern, str(text))

    if not match:
        return ""

    return match.group(1)


def calc_discount(regular_price, sales_price):
    if regular_price <= 0 or sales_price <= 0:
        return 0

    if regular_price <= sales_price:
        return 0

    return round((regular_price - sales_price) / regular_price * 100)