from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


# ============================================================
# 1. 프로젝트 경로 설정
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[1]

# 크롤링 결과 CSV 저장 폴더
DEFAULT_OUTPUT_DIR = ROOT_DIR / "Data"


# ============================================================
# 2. 다이소몰 API / URL 상수
# ============================================================

# 상품 상세 설명 이미지를 가져오는 API
DETAIL_DESC_API = "https://fapi.daisomall.co.kr/pd/pdr/pdDtl/selPdDtlDesc"

# 기본 카테고리 URL (정렬 파라미터 제외)
# 현재: 스킨케어 > 기초스킨 카테고리
DEFAULT_CATEGORY_URL = (
    "https://www.daisomall.co.kr/ds/exhCtgr/C208"
    "/CTGR_01050/CTGR_01051/CTGR_01065"
)

# requests 공통 헤더
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.daisomall.co.kr/",
    "Origin": "https://www.daisomall.co.kr",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
}


# ============================================================
# 3. 정렬 코드 매핑
# ============================================================
# sort_key -> (url_srt_param, button_text, label)
#
# url_srt_param : 카테고리 URL의 ?srt= 파라미터 값
# button_text   : 페이지 내 정렬 버튼의 텍스트 (span.name)
# label         : CSV 파일명에 사용할 한글 이름
# ============================================================

SORT_MAP: dict[str, tuple[str, str, str]] = {
    "best": ("SALE_QTY_DESC", "판매량순",  "판매량순"),
    "new":  ("NEW_PRDT_DESC", "신상품순",  "신상품순"),
    "low":  ("LOW_PRICE_ASC", "낮은가격순", "낮은가격순"),
    "high": ("HIGH_PRICE_DESC", "높은가격순", "높은가격순"),
    "rate": ("RATE_DESC",     "평점순",    "평점순"),
}


# ============================================================
# 4. Tesseract 경로
# ============================================================

DEFAULT_TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


# ============================================================
# 5. 상품 수집 설정
# ============================================================

@dataclass(frozen=True)
class DaisoCrawlConfig:
    """
    상품 정보 수집에 필요한 설정값을 모아둔 클래스입니다.
    """

    # 정렬 기준 (쉼표로 여러 개 지정 가능: "best,new")
    sort: str = "new"

    # 수집 목표 상품 수
    target_count: int = 24

    # 카테고리 URL (정렬 파라미터 제외)
    category_url: str = DEFAULT_CATEGORY_URL

    # True면 브라우저 창 없이 실행
    headless: bool = False

    # CSV 저장 위치
    output_dir: Path = DEFAULT_OUTPUT_DIR

    # Tesseract 실행 파일 경로
    tesseract_cmd: str = DEFAULT_TESSERACT_CMD

    # OpenAI API 키 (GPT Vision 핵심 성분 추출용, 빈 문자열이면 건너뜀)
    openai_api_key: str = ""

    # 카테고리 페이지 로드 후 대기 (ms)
    page_delay_ms: int = 4000

    # 스크롤 후 대기 (ms)
    scroll_delay_ms: int = 1200

    # 상품 상세 페이지 로드 후 대기 (ms)
    detail_delay_ms: int = 2500


# ============================================================
# 6. 리뷰 수집 설정
# ============================================================

@dataclass(frozen=True)
class DaisoReviewCrawlConfig:
    """
    리뷰 수집에 필요한 설정값을 모아둔 클래스입니다.
    """

    # 정렬 기준
    sort: str = "new"

    # 수집할 상품 수
    target_product_count: int = 24

    # 상품 1개당 수집할 리뷰 수
    reviews_per_product: int = 10

    # 카테고리 URL
    category_url: str = DEFAULT_CATEGORY_URL

    # 브라우저 창 숨김 여부
    headless: bool = False

    # CSV 저장 위치
    output_dir: Path = DEFAULT_OUTPUT_DIR

    # 페이지 대기 (ms)
    page_delay_ms: int = 4000

    # 스크롤 대기 (ms)
    scroll_delay_ms: int = 1200

    # 상세 페이지 대기 (ms)
    detail_delay_ms: int = 3000
