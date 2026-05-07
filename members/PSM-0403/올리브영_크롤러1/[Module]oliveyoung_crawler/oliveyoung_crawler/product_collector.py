from __future__ import annotations

import base64
import json
import os
import tempfile
import time
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .browser import create_driver, safe_quit_driver, wait_for_oliveyoung_access
from .category import select_category
from .common import clean_text, make_output_path, now_iso, parse_sorts
from .config import ProductCrawlConfig, ROOT_DIR
from .product_parser import (
    build_detail_dict,
    extract_volume_from_text,
    parse_product_cards,
    with_page,
    with_sort,
)


# ============================================================
# product_collector.py
# ------------------------------------------------------------
# 역할:
# - 실제 상품 수집 실행
# - 카테고리 진입
# - 목록 페이지 수집
# - 상품 상세 페이지 수집
# - 상품 CSV 저장
#
# 기존 collect_products.py에서 한 파일에 있던 내용을
# 브라우저 / 카테고리 / 파서 / 수집 실행으로 나눈 구조입니다.
# ============================================================

PRODUCT_INFO_COLUMNS = [
    "date",
    "platform",
    "sort_type",
    "rank",
    "product_name",
    "brand",
    "volume_ml",
    "regular_price",
    "discount",
    "sales_price",
    "rating",
    "review_count",
    "main_ingredients",
    "ingredients",
    "ing_source",
    "url",
]

OPENAI_ENV_LOADED = False
OPENAI_KEY_WARNED = False
OPENAI_CALL_WARNED = False

EXTRACT_DETAIL_IMAGE_URLS_JS = """
const selectors = [
    '.contEditor img',
    '#tempHtml2 img',
    '#goodsDetailContent img',
    '#goodsDetailInfo img',
    '.goods_detail_box img',
    '.prd_detail_box img',
    '.prd_detail img',
    '.detail_info_area img',
    '[class*="GoodsDetail"] img',
    '[class*="Description"] img',
    '[class*="detail"] img',
    '.speedycat-container img',
];

// lazy 이미지 강제 로드
document.querySelectorAll('img[data-src], img[data-original]').forEach(img => {
    if (img.getAttribute('data-src')) img.src = img.getAttribute('data-src');
    if (img.getAttribute('data-original')) img.src = img.getAttribute('data-original');
});

const seen = new Set();
const urls = [];

for (const selector of selectors) {
    for (const img of document.querySelectorAll(selector)) {
        const url = img.currentSrc || img.src || img.getAttribute('data-src') || img.getAttribute('data-original') || '';
        if (url && !url.startsWith('data:') && url.includes('oliveyoung.co.kr') && !seen.has(url)) {
            seen.add(url);
            urls.push(url);
        }
    }
}

return urls;
"""

LOAD_DETAIL_IMAGES_JS = """
const clickable = Array.from(document.querySelectorAll('button,a,[role="button"]'));
const target = clickable.find(element => {
    const text = [
        element.innerText || '',
        element.textContent || '',
        element.getAttribute('aria-label') || '',
        element.getAttribute('title') || '',
    ].join(' ').replace(/\\s+/g, ' ').trim();
    if (!text) return false;
    if (/(리뷰|문의|배송|교환|반품)/.test(text)) return false;
    return /(상품.*더보기|상세.*더보기|설명.*더보기|더보기|펼치기)/.test(text);
});

if (!target) return false;
target.scrollIntoView({block: 'center'});
target.click();
return true;
"""


def ingredient_source(value) -> str:
    """
    전성분 출처를 기록합니다.

    현재 수집 방식은 상품정보 제공고시 HTML 텍스트 기반이며,
    OCR 경로는 별도로 쓰고 있지 않습니다.
    """
    if pd.isna(value):
        return ""

    text = clean_text(value)

    if not text:
        return ""

    if text == "3회 실패":
        return "failed"

    return "html"


def load_openai_env() -> None:
    """
    루트 또는 크롤러 폴더의 .env를 읽어 OPENAI_API_KEY를 환경변수에 올립니다.
    """
    global OPENAI_ENV_LOADED

    if OPENAI_ENV_LOADED:
        return

    OPENAI_ENV_LOADED = True

    try:
        from dotenv import load_dotenv
    except Exception:
        return

    candidates = [
        Path.cwd() / ".env",
        ROOT_DIR / ".env",
        ROOT_DIR.parent.parent / ".env",
    ]

    for env_path in candidates:
        if env_path.exists():
            load_dotenv(env_path, override=False)


def clean_main_ingredients_response(value) -> str:
    """
    GPT JSON 응답을 CSV에 넣기 좋은 1줄 성분 요약으로 정리합니다.

    형식: "Cica(Centella Asiatica Extract, Madecassoside), Hyaluronic Acid(Sodium Hyaluronate)"
    JSON 파싱 실패 시 원문 텍스트를 그대로 반환합니다.
    """
    text = clean_text(value)

    if not text:
        return ""

    text = text.strip("`\"' ")

    # 마크다운 코드블록 제거
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        data = json.loads(text)
        items = data.get("representative_ingredients", [])
        parts = []
        for item in items:
            name = item.get("대표성분명", "").strip()
            inci_list = [i.strip() for i in item.get("INCI_성분", []) if i.strip()]
            if not name:
                continue
            if inci_list:
                parts.append(f"{name}({', '.join(inci_list)})")
            else:
                parts.append(name)
        return ", ".join(parts)
    except Exception:
        if text in {"없음", "확인불가", "확인 불가", "N/A", "n/a"}:
            return ""
        return text


def parse_detail_image_urls(value) -> list[str]:
    """
    상세 이미지 URL JSON 문자열을 리스트로 변환합니다.
    """
    if isinstance(value, list):
        return [clean_text(item) for item in value if clean_text(item)]

    text = clean_text(value)

    if not text:
        return []

    try:
        parsed = json.loads(text)
    except Exception:
        return [text]

    if not isinstance(parsed, list):
        return []

    return [clean_text(item) for item in parsed if clean_text(item)]


def extract_main_ingredients_with_gpt_ocr(
    *,
    product_name: str,
    image_urls: list[str],
    ingredients_text: str,
) -> str:
    """
    상품설명 이미지를 GPT Vision/OCR API에 보내 주요 성분 1~3개를 추출합니다.

    OPENAI_API_KEY가 없거나 호출 실패 시 크롤링을 중단하지 않고 빈 값을 반환합니다.
    """
    global OPENAI_KEY_WARNED, OPENAI_CALL_WARNED

    image_urls = [clean_text(url) for url in image_urls if clean_text(url)]
    image_urls = [url.split("?")[0] if "oliveyoung.co.kr" in url else url for url in image_urls]

    if not image_urls:
        return ""

    load_openai_env()

    if not os.getenv("OPENAI_API_KEY"):
        if not OPENAI_KEY_WARNED:
            print("[GPT OCR 생략] OPENAI_API_KEY가 없어 main_ingredients를 비워둡니다.")
            OPENAI_KEY_WARNED = True
        return ""

    try:
        from openai import OpenAI
    except Exception as error:
        if not OPENAI_CALL_WARNED:
            print(f"[GPT OCR 생략] openai 패키지를 불러오지 못했습니다: {str(error)[:80]}")
            OPENAI_CALL_WARNED = True
        return ""

    import requests

    prompt = (
        "너는 화장품 성분 분석 전문가이다.\n\n"
        "목표:\n"
        "화장품 홍보 이미지에서 제품이 강조하는 \"대표 성분명\"을 찾고,\n"
        "그 대표 성분을 구성하는 실제 화장품 성분을 전성분 목록에서 찾아 INCI 명칭으로 정리한다.\n\n"
        "작업 절차:\n"
        "1. 홍보 이미지의 문구에서 제품이 강조하는 성분 표현을 찾는다.\n"
        "   - 예: 시카, 병풀, 히알루론산, 저분자 히알루론산, 세라마이드, PDRN, 엑소좀, 레티놀,\n"
        "         바쿠치올, 나이아신아마이드, 펩타이드, 콜라겐, 비타민C, PHA, AHA, BHA 등\n"
        "2. 이 표현을 업계에서 흔히 쓰는 대표 성분명으로 정리한다.\n"
        "   - 예: 병풀 → Cica / 히알루론산 → Hyaluronic Acid / 세라마이드 → Ceramide\n"
        "3. 아래 제공된 전성분 목록에서 해당 대표 성분을 구성하는 실제 성분만 찾는다.\n"
        "4. 찾은 성분은 반드시 INCI 명칭으로 작성한다.\n"
        "5. 전성분 목록에 없는 성분은 추측해서 넣지 않는다.\n"
        "6. 홍보 이미지에 강조되어 있지 않은 성분은 전성분에 있더라도 대표 성분으로 뽑지 않는다.\n"
        "7. 성분 개수를 억지로 채우지 않는다.\n"
        "8. OCR 오류가 의심되는 경우, 전성분 문맥상 확실히 보정 가능한 경우에만 보정한다.\n"
        "9. 확실하지 않으면 not_found_or_uncertain에 기록한다.\n\n"
        "중요 규칙:\n"
        "- 대표 성분명은 소비자와 업계에서 통용되는 마케팅 명칭으로 작성한다.\n"
        "- INCI 명칭은 전성분에서 확인 가능한 실제 성분명만 작성한다.\n"
        "- \"시카 콤플렉스\", \"수분 콤플렉스\", \"탄력 콤플렉스\"처럼 복합 명칭이 있는 경우,\n"
        "  전성분에서 그 복합 성분을 구성할 가능성이 높은 INCI 성분만 분리한다.\n"
        "- Water, Glycerin, Butylene Glycol, Dipropylene Glycol 등 단순 보습제·용매는\n"
        "  홍보 이미지에서 명확히 강조된 경우가 아니면 제외한다.\n\n"
        "출력 형식: 마크다운 없이 아래 JSON만 출력한다.\n\n"
        "{\n"
        "  \"representative_ingredients\": [\n"
        "    {\n"
        "      \"대표성분명\": \"\",\n"
        "      \"업계표현\": \"\",\n"
        "      \"INCI_성분\": [],\n"
        "      \"선정근거\": \"\",\n"
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
        f"전성분:\n{ingredients_text}"
    )

    try:
        client = OpenAI()
        content = [{"type": "text", "text": prompt}]

        with tempfile.TemporaryDirectory() as tmp_dir:
            for i, url in enumerate(image_urls):
                if ".gif" in url.lower():
                    continue

                try:
                    res = requests.get(
                        url,
                        headers={"User-Agent": "Mozilla/5.0"},
                        timeout=20,
                    )
                    res.raise_for_status()

                    img_path = os.path.join(tmp_dir, f"img_{i}.jpg")
                    with open(img_path, "wb") as f:
                        f.write(res.content)

                    b64 = base64.b64encode(res.content).decode("utf-8")
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                    })

                except Exception as dl_err:
                    print(f"  [이미지 다운로드 실패] {url[:80]} {str(dl_err)[:60]}")

        if len(content) == 1:
            return ""

        response = client.chat.completions.create(
            model=os.getenv("OPENAI_OCR_MODEL", "gpt-5.4"),
            messages=[{"role": "user", "content": content}],
            max_completion_tokens=2000,
        )

        return clean_main_ingredients_response(response.choices[0].message.content)

    except Exception as error:
        print(f"[GPT OCR 실패] {str(error)[:200]}")
        return ""


def get_series(df: pd.DataFrame, column: str) -> pd.Series:
    """
    컬럼이 없는 중간 저장 시점에도 같은 길이의 빈 Series를 반환합니다.
    """
    if column in df.columns:
        return df[column]

    return pd.Series([""] * len(df), index=df.index)


def to_product_info_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    내부 수집용 컬럼을 요청받은 제품 CSV 스키마로 변환합니다.
    """
    from datetime import date as _date

    today = _date.today().strftime("%Y-%m-%d")

    output = pd.DataFrame(
        {
            "date": today,
            "platform": "oliveyoung",
            "sort_type": get_series(df, "정렬"),
            "rank": get_series(df, "순위"),
            "product_name": get_series(df, "상품명"),
            "brand": get_series(df, "브랜드"),
            "volume_ml": get_series(df, "용량"),
            "regular_price": get_series(df, "정가"),
            "discount": get_series(df, "할인율"),
            "sales_price": get_series(df, "할인가"),
            "rating": get_series(df, "제품평점"),
            "review_count": get_series(df, "전체리뷰수"),
            "main_ingredients": get_series(df, "주요성분"),
            "ingredients": get_series(df, "전성분"),
            "ing_source": get_series(df, "전성분").map(ingredient_source),
            "url": get_series(df, "상품링크"),
        }
    )

    return output[PRODUCT_INFO_COLUMNS].fillna("")


def save_product_info_rows(df: pd.DataFrame, path: Path) -> None:
    """
    제품 데이터를 요청받은 컬럼 순서로 저장합니다.
    """
    info_df = to_product_info_df(df)
    path.parent.mkdir(parents=True, exist_ok=True)
    info_df.to_csv(path, index=False, encoding="utf-8-sig")


def collect_detail_image_urls(driver) -> list[str]:
    """
    상품설명 이미지 URL을 Selenium으로 직접 수집합니다.

    1. '상품설명 더보기' 버튼 클릭
    2. .speedycat-container img에서 data-src 또는 src 추출
    """
    time.sleep(2)

    try:
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            if "상품설명 더보기" in btn.text:
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(2)
                break
    except Exception:
        pass

    images = driver.find_elements(By.CSS_SELECTOR, ".speedycat-container img")

    seen: set[str] = set()
    urls: list[str] = []

    for img in images:
        src = img.get_attribute("src")
        data_src = img.get_attribute("data-src")
        url = data_src or src

        if not url or url == "null" or "base64" in url:
            continue

        if url not in seen:
            seen.add(url)
            urls.append(url)

    return urls


def get_detail(
    driver,
    url: str,
    *,
    detail_delay_seconds: float = 1.0,
    access_check_timeout_seconds: int = 180,
) -> dict[str, str]:
    """
    상품 상세 페이지에 들어가서 상세정보를 수집합니다.

    수집 대상:
    - 평점
    - 전체 리뷰수
    - 상세설명
    - 대표이미지
    - 상품정보 제공고시
    - 전성분
    - 용량
    """

    for attempt in range(3):
        try:
            driver.get(url)

            wait_for_oliveyoung_access(
                driver,
                timeout_seconds=access_check_timeout_seconds,
                context="상품 상세",
            )

            # 상세 페이지 body가 뜰 때까지 대기
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
            )

            time.sleep(detail_delay_seconds)

            # 상품정보 제공고시 아코디언 버튼이 있으면 펼칩니다.
            # 기존 코드에서 상품정보 제공고시 버튼을 눌러 전성분/용량을 확보하는 흐름을 유지합니다.
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "button.Accordion_accordion-btn__IYjKm")
                    )
                )

                buttons = driver.find_elements(
                    By.CSS_SELECTOR,
                    "button.Accordion_accordion-btn__IYjKm",
                )

                notice_button = None

                for button in buttons:
                    if "상품정보 제공고시" in button.text:
                        notice_button = button
                        break

                if notice_button:
                    driver.execute_script(
                        "arguments[0].scrollIntoView(true);",
                        notice_button,
                    )
                    time.sleep(0.5)

                    driver.execute_script("arguments[0].click();", notice_button)

                    time.sleep(detail_delay_seconds)

            except Exception as error:
                print(f"  [상세] 상품정보 제공고시 버튼 확인 실패: {str(error)[:80]}")

            soup = BeautifulSoup(driver.page_source, "html.parser")
            detail = build_detail_dict(soup)

            try:
                image_urls = collect_detail_image_urls(driver)
                detail["상세이미지_URLS"] = json.dumps(image_urls, ensure_ascii=False)
            except Exception as error:
                print(f"  [상세] 이미지 수집 실패: {str(error)[:80]}")

            ingredient_text = detail.get("전성분", "")

            print(
                f"  [상세 성공] 평점:{detail.get('제품평점', '')} "
                f"리뷰:{detail.get('전체리뷰수', '')} "
                f"용량:{detail.get('용량', '')} "
                f"성분:{len(ingredient_text)}자"
            )

            return detail

        except Exception as error:
            print(f"  [상세 시도 {attempt + 1}/3 실패] {str(error)[:120]}")
            time.sleep(2)

    return {
        "제품평점": "",
        "전체리뷰수": "",
        "상세설명": "",
        "대표이미지": "",
        "상세이미지_URLS": "[]",
        "용량": "",
        "제품주요사양": "",
        "사용기한": "",
        "사용방법": "",
        "제조판매업자": "",
        "제조국": "",
        "전성분": "3회 실패",
        "기능성화장품심사": "",
        "사용시주의사항": "",
        "품질보증기준": "",
        "소비자상담전화번호": "",
        "상세정보_JSON": "{}",
    }


def collect_sort_products(
    driver,
    base_url: str,
    *,
    sort_code: str,
    sort_name: str,
    suffix: str,
    config: ProductCrawlConfig,
) -> Path | None:
    """
    특정 정렬 기준 하나에 대해 상품 목록과 상세정보를 수집합니다.

    예:
    - 인기순 hot
    - 신상품순 new
    """

    print("=" * 60)
    print(f"▶ [{sort_name}] 상품 수집 시작")
    print("=" * 60)

    all_data: list[dict[str, str | int]] = []
    seen_product_keys: set[str] = set()

    # 1페이지 URL에 정렬 코드 적용
    sorted_base_url = with_sort(base_url.format(page=1), sort_code)

    for page in range(1, config.total_pages + 1):
        if config.max_products is not None and len(all_data) >= config.max_products:
            break

        print(f"[목록] {page}페이지 수집 중...")

        page_url = with_page(sorted_base_url, page)

        driver.get(page_url)

        time.sleep(config.page_delay_seconds)

        wait_for_oliveyoung_access(
            driver,
            timeout_seconds=config.access_check_timeout_seconds,
            context=f"{sort_name} {page}페이지",
        )

        # 첫 페이지에서는 정렬 버튼 클릭도 한 번 시도합니다.
        # URL prdSort만으로 충분한 경우도 있지만, 기존 흐름에 맞춰 버튼 클릭을 유지합니다.
        if page == 1:
            try:
                sort_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, f'//a[@data-prdsoting="{sort_code}"]')
                    )
                )
                driver.execute_script("arguments[0].click();", sort_button)
                time.sleep(config.page_delay_seconds)
            except Exception as error:
                print(f"  [정렬 버튼 클릭 생략] {str(error)[:80]}")

        rows = parse_product_cards(
            driver.page_source,
            page=page,
            sort_code=sort_code,
            sort_name=sort_name,
            suffix=suffix,
            major_category=config.major_category,
            middle_category=config.middle_category,
            start_rank=len(all_data) + 1,
            seen_product_keys=seen_product_keys,
        )

        print(f"  목록 상품 수: {len(rows)}")

        for row in rows:
            if config.max_products is not None and len(all_data) >= config.max_products:
                break

            all_data.append(row)

    if not all_data:
        print(f"[{sort_name}] 수집된 상품이 없습니다.")
        return None

    # 상품 목록 데이터프레임 생성
    df = pd.DataFrame(all_data)

    # 수집일시 추가
    df["수집일시"] = now_iso()

    save_path = make_output_path(config.output_dir, "Data", suffix)

    # 상세정보 수집
    print("=" * 60)
    print(f"▶ [{sort_name}] 상품 상세정보 수집 시작")
    print("=" * 60)

    for index, row in df.iterrows():
        product_name = row.get("상품명", "")
        product_url = row.get("상품링크", "")

        print(f"[상세] {index + 1}/{len(df)} {product_name}")

        detail = get_detail(
            driver,
            product_url,
            detail_delay_seconds=config.detail_delay_seconds,
            access_check_timeout_seconds=config.access_check_timeout_seconds,
        )

        # 상세 페이지에서 용량을 못 찾은 경우 상품명에서 재시도
        if not detail.get("용량", ""):
            detail["용량"] = extract_volume_from_text(product_name)

        detail["주요성분"] = extract_main_ingredients_with_gpt_ocr(
            product_name=product_name,
            image_urls=parse_detail_image_urls(detail.get("상세이미지_URLS", "[]")),
            ingredients_text=detail.get("전성분", ""),
        )

        for column, value in detail.items():
            df.at[index, column] = value

        processed_count = index + 1
        save_product_info_rows(df.iloc[:processed_count], save_path)
        print(f"[상품 CSV 저장] {processed_count}/{len(df)}개 → {save_path.name}")

    print(f"[상품 CSV 저장 완료] {save_path}")

    return save_path


def run(config: ProductCrawlConfig) -> list[Path]:
    """
    상품 수집 전체 실행 함수입니다.

    흐름:
    1. 브라우저 생성
    2. 카테고리 진입
    3. 정렬별 상품 수집
    4. CSV 저장
    5. 브라우저 종료
    """

    driver = create_driver(
        chrome_version=config.chrome_version,
        headless=config.headless,
    )

    saved_paths: list[Path] = []

    try:
        base_url = select_category(driver, config)

        for sort_code, sort_name, suffix in parse_sorts(config.sorts):
            path = collect_sort_products(
                driver,
                base_url,
                sort_code=sort_code,
                sort_name=sort_name,
                suffix=suffix,
                config=config,
            )

            if path:
                saved_paths.append(path)

            # 다음 정렬 수집 전 카테고리 첫 페이지로 복귀
            driver.get(base_url.format(page=1))
            time.sleep(config.page_delay_seconds)

            wait_for_oliveyoung_access(
                driver,
                timeout_seconds=config.access_check_timeout_seconds,
                context="카테고리 복귀",
            )

    finally:
        safe_quit_driver(driver)

    print("모든 정렬순서 상품 수집 완료!")

    return saved_paths
