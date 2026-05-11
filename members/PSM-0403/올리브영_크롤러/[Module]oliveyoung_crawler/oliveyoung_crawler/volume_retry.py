from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .browser import create_driver, safe_quit_driver, wait_for_oliveyoung_access
from .product_parser import extract_notice_table, extract_volume_from_text


def _get_volume_from_detail(
    driver,
    url: str,
    product_name: str,
    detail_delay_seconds: float = 1.0,
) -> str:
    for attempt in range(3):
        try:
            driver.get(url)
            wait_for_oliveyoung_access(driver, context="용량 재수집")
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
            )
            time.sleep(detail_delay_seconds)

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

            volume = extract_volume_from_text(notice.get("용량", ""))
            if volume:
                print(f"  [제공고시] {volume}")
                return volume

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


def _find_latest_info_csv(data_dir: Path) -> Path | None:
    candidates = sorted(
        data_dir.glob("*(info)*.csv"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _resolve_csv_paths(target_csv, data_dir: Path) -> list[Path]:
    if target_csv is None:
        latest = _find_latest_info_csv(data_dir)
        return [latest] if latest else []
    if isinstance(target_csv, list):
        return [Path(p) for p in target_csv]
    return [Path(target_csv)]


def _is_volume_missing(value) -> bool:
    return pd.isna(value) or str(value).strip() == ""


def _all_products(df: pd.DataFrame) -> list[dict]:
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


def _process_csv(
    csv_path: Path,
    *,
    chrome_version: int,
    headless: bool,
) -> None:
    print(f"\n{'=' * 60}")
    print(f"[대상 CSV] {csv_path}")

    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    print(f"[전체 행] {len(df)}개")

    if "volume_ml" not in df.columns:
        print("[건너뜀] volume_ml 컬럼이 없습니다.")
        return

    products = _all_products(df)
    print(f"[대상 상품] {len(products)}개 (전체 재수집)")

    name_filled = 0
    for idx in df.index:
        volume = extract_volume_from_text(str(df.at[idx, "product_name"]))
        if volume:
            df.at[idx, "volume_ml"] = volume
            name_filled += 1
        else:
            df.at[idx, "volume_ml"] = ""

    print(f"[상품명 추출] {name_filled}개")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    crawl_targets = [
        p for p in products
        if _is_volume_missing(
            df.loc[df["url"].astype(str).str.strip() == p["url"], "volume_ml"].iat[0]
        )
    ]

    if not crawl_targets:
        print("[완료] 상품명 정규식으로 모두 채워졌습니다.")
        return

    print(f"\n[크롤링 대상] {len(crawl_targets)}개 상품")
    for p in crawl_targets:
        print(f"  - {p['product_name']}")

    driver = create_driver(chrome_version=chrome_version, headless=headless)

    try:
        for i, product in enumerate(crawl_targets, 1):
            product_name = product["product_name"]
            product_url = product["url"]

            print(f"\n[{i}/{len(crawl_targets)}] {product_name}")

            volume = _get_volume_from_detail(driver, product_url, product_name)

            url_mask = df["url"].astype(str).str.strip() == product_url
            df.loc[url_mask, "volume_ml"] = volume
            print(f"  [결과] {volume!r}  ({url_mask.sum()}행 업데이트)")

            df.to_csv(csv_path, index=False, encoding="utf-8-sig")
            print(f"  [중간 저장] {csv_path.name}")

    finally:
        safe_quit_driver(driver)

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"\n[저장 완료] {csv_path} ({len(df)}행)")


def run_retry(
    *,
    target_csv=None,
    chrome_version: int = 147,
    headless: bool = False,
    data_dir: Path | None = None,
) -> None:
    """
    volume_ml이 없는 상품들을 재크롤링해 용량을 채웁니다.

    Args:
        target_csv: 재수집할 info CSV 경로.
                    None → Data/ 폴더에서 가장 최근 (info) CSV 자동 선택.
                    Path 1개 또는 list[Path] 가능.
        chrome_version: 크롬 버전.
        headless: True면 브라우저 창 없이 실행.
        data_dir: Data 폴더 경로. None이면 이 파일 기준 자동 결정.
    """
    if data_dir is None:
        data_dir = Path(__file__).parent.parent / "Data"

    csv_paths = _resolve_csv_paths(target_csv, data_dir)

    if not csv_paths:
        print("[오류] info CSV 파일을 찾을 수 없습니다.")
        return

    for csv_path in csv_paths:
        if not csv_path.exists():
            print(f"[건너뜀] 파일 없음: {csv_path}")
            continue
        _process_csv(csv_path, chrome_version=chrome_version, headless=headless)
