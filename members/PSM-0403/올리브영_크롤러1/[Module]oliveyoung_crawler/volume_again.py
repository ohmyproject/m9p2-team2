"""
volume_ml이 없는 상품들을 재크롤링해 용량을 채웁니다.

사용법:
  python volume_again.py

추출 우선순위:
  1. 상품명 (product_name) — 크롤링 없이 CSV에서 바로 시도
  2. 상품정보 제공고시 "내용물의 용량 또는 중량" — 상세 페이지 크롤링
  3. 상세 페이지 전체 텍스트 — 위 두 곳에서 못 찾은 경우

동작 방식:
  1. TARGET_CSV 에서 volume_ml이 비어 있는 행을 찾습니다.
  2. 먼저 상품명에서 정규식으로 용량을 추출합니다 (크롤링 없음).
  3. 그래도 비어 있으면 상세 페이지를 방문해 제공고시 → 전체 텍스트 순으로 시도합니다.
  4. URL이 같은 모든 행에 용량을 채우고 CSV를 덮어씁니다.
"""

import sys
import time
from pathlib import Path

# ============================================================
# 설정
# ============================================================

# 재수집할 info CSV 경로
# None          → Data/ 폴더에서 가장 최근 (info) CSV 자동 선택
# 파일 1개      → Path("Data/oliveyoung_판매순(info)_260505.csv")
# 파일 여러 개  → [Path("Data/...csv"), Path("Data/...csv")]
TARGET_CSV = [Path("Data/oliveyoung_신상품순(info)_260501.csv"),
              Path("Data/oliveyoung_신상품순(info)_260502.csv"),
              Path("Data/oliveyoung_신상품순(info)_260503.csv"),
              Path("Data/oliveyoung_신상품순(info)_260504.csv"),
              Path("Data/oliveyoung_신상품순(info)_260505.csv"),
              Path("Data/oliveyoung_판매순(info)_260501.csv"),
              Path("Data/oliveyoung_판매순(info)_260502.csv"),
              Path("Data/oliveyoung_판매순(info)_260503.csv"),
              Path("Data/oliveyoung_판매순(info)_260504.csv"),
              Path("Data/oliveyoung_판매순(info)_260505.csv")
]

# 크롬 설정
CHROME_VERSION = 147
HEADLESS = False

# ============================================================

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from oliveyoung_crawler.browser import create_driver, safe_quit_driver, wait_for_oliveyoung_access
from oliveyoung_crawler.product_parser import extract_notice_table, extract_volume_from_text


# ─── 상세 페이지 크롤링 ───────────────────────────────────────

def get_volume_from_detail(
    driver,
    url: str,
    product_name: str,
    detail_delay_seconds: float = 1.0,
) -> str:
    """
    상세 페이지를 열어 용량을 추출합니다.

    추출 순서:
    1. 상품명 (이미 크롤링 전에 시도했지만 한 번 더 확인)
    2. 제공고시 "내용물의 용량 또는 중량"
    3. 페이지 전체 텍스트
    """
    for attempt in range(3):
        try:
            driver.get(url)

            wait_for_oliveyoung_access(driver, context="용량 재수집")

            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
            )
            time.sleep(detail_delay_seconds)

            # 상품정보 제공고시 아코디언 펼치기
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "button.Accordion_accordion-btn__IYjKm")
                    )
                )
                buttons = driver.find_elements(
                    By.CSS_SELECTOR, "button.Accordion_accordion-btn__IYjKm"
                )
                for button in buttons:
                    if "상품정보 제공고시" in button.text:
                        driver.execute_script("arguments[0].scrollIntoView(true);", button)
                        time.sleep(0.3)
                        driver.execute_script("arguments[0].click();", button)
                        time.sleep(detail_delay_seconds)
                        break
            except Exception:
                pass

            soup = BeautifulSoup(driver.page_source, "html.parser")
            notice = extract_notice_table(soup)

            # 2순위: 제공고시 용량 필드
            volume = extract_volume_from_text(notice.get("용량", ""))
            if volume:
                print(f"  [제공고시] {volume}")
                return volume

            # 3순위: 페이지 전체 텍스트
            body_text = soup.get_text(" ", strip=True)
            volume = extract_volume_from_text(body_text)
            if volume:
                print(f"  [전체텍스트] {volume}")
                return volume

            print("  [미추출] 용량을 찾지 못했습니다.")
            return ""

        except Exception as error:
            print(f"  [시도 {attempt + 1}/3 실패] {str(error)[:100]}")
            time.sleep(2)

    return ""


# ─── CSV 처리 ─────────────────────────────────────────────────

def find_latest_info_csv(data_dir: Path) -> Path | None:
    candidates = sorted(
        data_dir.glob("*(info)*.csv"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def resolve_csv_paths(data_dir: Path) -> list[Path]:
    if TARGET_CSV is None:
        latest = find_latest_info_csv(data_dir)
        return [latest] if latest else []
    if isinstance(TARGET_CSV, list):
        return [Path(p) for p in TARGET_CSV]
    return [Path(TARGET_CSV)]


def is_volume_missing(value) -> bool:
    return pd.isna(value) or str(value).strip() == ""


def all_products(df: pd.DataFrame) -> list[dict]:
    """전체 행을 URL 기준으로 중복 제거해 반환합니다."""
    seen: set[str] = set()
    products: list[dict] = []

    for _, row in df.iterrows():
        url = str(row.get("url", "")).strip()
        if not url or url == "nan" or url in seen:
            continue
        seen.add(url)
        products.append({
            "url": url,
            "product_name": str(row.get("product_name", "")),
        })

    return products


def process_csv(csv_path: Path) -> None:
    print(f"\n{'=' * 60}")
    print(f"[대상 CSV] {csv_path}")

    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    print(f"[전체 행] {len(df)}개")

    if "volume_ml" not in df.columns:
        print("[건너뜀] volume_ml 컬럼이 없습니다.")
        return

    products = all_products(df)
    print(f"[대상 상품] {len(products)}개 (전체 재수집)")

    # ── 1순위: 상품명 정규식 (크롤링 없이 전체 적용) ───────────
    name_filled = 0
    for idx in df.index:
        volume = extract_volume_from_text(str(df.at[idx, "product_name"]))
        if volume:
            df.at[idx, "volume_ml"] = volume
            name_filled += 1
        else:
            df.at[idx, "volume_ml"] = ""  # 크롤링 전 초기화

    print(f"[상품명 추출] {name_filled}개")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    # ── 2·3순위: 상품명에서 못 뽑힌 것들 크롤링 ────────────────
    crawl_targets = [
        p for p in products
        if is_volume_missing(
            df.loc[df["url"].astype(str).str.strip() == p["url"], "volume_ml"].iat[0]
        )
    ]

    if not crawl_targets:
        print("[완료] 상품명 정규식으로 모두 채워졌습니다.")
        return

    print(f"\n[크롤링 대상] {len(crawl_targets)}개 상품")
    for p in crawl_targets:
        print(f"  - {p['product_name']}")

    driver = create_driver(chrome_version=CHROME_VERSION, headless=HEADLESS)

    try:
        for i, product in enumerate(crawl_targets, 1):
            product_name = product["product_name"]
            product_url = product["url"]

            print(f"\n[{i}/{len(crawl_targets)}] {product_name}")

            volume = get_volume_from_detail(driver, product_url, product_name)

            url_mask = df["url"].astype(str).str.strip() == product_url
            df.loc[url_mask, "volume_ml"] = volume
            print(f"  [결과] {volume!r}  ({url_mask.sum()}행 업데이트)")

            df.to_csv(csv_path, index=False, encoding="utf-8-sig")
            print(f"  [중간 저장] {csv_path.name}")

    finally:
        safe_quit_driver(driver)

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"\n[저장 완료] {csv_path} ({len(df)}행)")


def main() -> None:
    data_dir = Path(__file__).parent / "Data"
    csv_paths = resolve_csv_paths(data_dir)

    if not csv_paths:
        print("[오류] info CSV 파일을 찾을 수 없습니다.")
        return

    for csv_path in csv_paths:
        if not csv_path.exists():
            print(f"[건너뜀] 파일 없음: {csv_path}")
            continue
        process_csv(csv_path)


if __name__ == "__main__":
    main()
