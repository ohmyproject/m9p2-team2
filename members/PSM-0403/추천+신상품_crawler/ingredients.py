"""전성분 크롤링 (직접 API → 브라우저 인터셉터 → 본문 텍스트 → winocr 폴백)"""
import asyncio, requests, threading, time
from io import BytesIO
from urllib.parse import urlparse
from PIL import Image
from selenium.webdriver.common.by import By
import winocr

EMPTY_VALS = {"", "상품상세참조", "상품 상세 참조", "상세페이지참조", "상세 페이지 참조"}

INGR_TITLE_KEYS = [
    "｢화장품법｣에 따라 기재 표시하여야 하는 모든 성분",
    "화장품법에 따라 기재 표시하여야 하는 모든성분",
    "화장품법에 따라 기재해야 하는 모든 성분",
    "화장품법에 따라 기재ㆍ표시하여야 하는 모든 성분",
    "화장품법에 따라 기재·표시하여야 하는 모든 성분",
    "전성분", "제품 전성분", "모든 성분",
    "Q.전성분 알려주세요"
]
INGR_END_KEYS = [
    "｢화장품법｣에 따른 기능성", "사용할 때의 주의사항",
    "품질보증기준", "사용방법", "주의사항", "보관방법",
    "소비자 상담", "소비자상담", "배송", "교환", "반품",
    "용도 및 종류", "기능성 여부", "제조사이름", "판매사이름", "판매사",
    "제조일자", "내용량", "가격", "문의",
]

_INTERCEPTOR_JS = """
window.__productNotice = null;
const _origFetch = window.fetch;
window.fetch = async function(...args) {
    const r = await _origFetch.apply(this, args);
    try {
        const clone = r.clone();
        clone.json().then(data => {
            if (data && data.productInfoProvidedNoticeView !== undefined)
                window.__productNotice = data;
        }).catch(() => {});
    } catch(e) {}
    return r;
};
const _origSend = XMLHttpRequest.prototype.send;
XMLHttpRequest.prototype.send = function(...args) {
    this.addEventListener('load', function() {
        try {
            const data = this.responseType === 'json'
                ? this.response
                : JSON.parse(this.responseText);
            if (data && data.productInfoProvidedNoticeView !== undefined)
                window.__productNotice = data;
        } catch(e) {}
    });
    return _origSend.apply(this, args);
};
"""


def setup_interceptor(driver):
    """드라이버 생성 직후 1회 호출 → 이후 모든 페이지에 인터셉터 자동 삽입"""
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": _INTERCEPTOR_JS})


# ── Notice 추출 ──────────────────────────────────────────────────────────────

def _extract_notice_values_deep(data) -> str:
    """JSON 전체를 재귀 탐색해 전성분 값 추출.

    참고 코드(ingredient_extractor.py)의 walk 방식을 적용:
    basic dict만 보던 것을 전체 JSON 구조로 확장해 누락 케이스를 줄인다.
    """
    empty = {v.replace(" ", "") for v in EMPTY_VALS}
    found = []

    def _check(key, value):
        if found or not key or not value:
            return
        key_s = str(key).strip()
        val_s = str(value).strip()
        if len(val_s) < 15 or val_s.replace(" ", "") in empty:
            return
        if (any(k in key_s for k in INGR_TITLE_KEYS) or
                "전성분" in key_s or "모든 성분" in key_s or "모든성분" in key_s):
            found.append(val_s)

    def _walk(node, parent_key=""):
        if found:
            return
        if isinstance(node, dict):
            label = (node.get("key") or node.get("name") or node.get("title") or
                     node.get("label") or node.get("noticeItemName") or
                     node.get("attributeName") or parent_key)
            value = (node.get("value") or node.get("content") or node.get("text") or
                     node.get("noticeItemValue") or node.get("attributeValue"))
            _check(label, value)
            for k, v in node.items():
                _check(k, v)
                _walk(v, str(k))
        elif isinstance(node, list):
            for item in node:
                _walk(item, parent_key)

    _walk(data)
    return found[0] if found else ""


def _try_notice_api_direct(driver, url: str) -> str:
    """URL에서 channel/product_id를 추출해 제품정보제공고시 API 직접 호출.

    브라우저 인터셉터를 기다리지 않고, 드라이버 쿠키를 재사용해 직접 요청한다.
    Smartstore·브랜드스토어 양쪽 URL 패턴을 모두 처리한다.
    """
    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]
    channel, product_id = "", ""
    for i, part in enumerate(parts):
        if part == "products" and i + 1 < len(parts):
            product_id = parts[i + 1]
            channel = parts[i - 1] if i > 0 else ""
            break
    if not product_id:
        return ""

    try:
        cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
        user_agent = driver.execute_script("return navigator.userAgent") or "Mozilla/5.0"
    except Exception:
        cookies, user_agent = {}, "Mozilla/5.0"

    headers = {"User-Agent": user_agent, "Referer": url, "Accept": "application/json,*/*"}
    api_urls = []
    if channel:
        api_urls.append(
            f"https://smartstore.naver.com/i/v2/channels/{channel}"
            f"/products/{product_id}/product-info-provided-notice"
        )
    api_urls += [
        f"https://smartstore.naver.com/i/v1/products/{product_id}/product-info-provided-notices",
        f"https://smartstore.naver.com/i/v2/products/{product_id}/product-info-provided-notice",
    ]

    for api_url in api_urls:
        try:
            r = requests.get(api_url, cookies=cookies, headers=headers, timeout=8)
            if r.status_code != 200:
                continue
            ing = _extract_notice_values_deep(r.json())
            if ing:
                return ing
        except Exception:
            continue
    return ""


# ── 텍스트 / OCR 추출 ─────────────────────────────────────────────────────────

def _extract_from_text(text: str) -> str:
    """본문 텍스트(innerText 또는 OCR 결과)에서 전성분 섹션 추출."""
    for k in INGR_TITLE_KEYS:
        idx = text.find(k)
        if idx == -1:
            continue
        raw = text[idx + len(k):idx + len(k) + 3000].lstrip(" :：\n").strip()

        for ek in INGR_END_KEYS:
            ei = raw.find(ek)
            if ei != -1:
                raw = raw[:ei]

        # 콤마 없는 줄이 10줄 연속이면 성분 목록 종료로 판단
        kept, streak = [], 0
        for line in raw.splitlines():
            if "," in line:
                streak = 0
                kept.append(line)
            elif line.strip() == "":
                kept.append(line)
            else:
                streak += 1
                if streak > 10:
                    break
                kept.append(line)
        raw = "\n".join(kept).strip()

        # 콤마 구분 또는 줄바꿈 구분(3줄 이상) 모두 허용
        lines = [l for l in raw.splitlines() if l.strip()]
        if len(raw) > 20 and ("," in raw or len(lines) >= 3):
            return raw
    return ""


_KNOWN_ING_TOKENS = [
    "정제수", "나이아신아마이드", "글리세린", "부틸렌글라이콜", "판테놀",
    "소듐하이알루로네이트", "프로판다이올", "다이프로필렌글라이콜", "에틸헥실글리세린",
    "카보머", "트로메타민", "알란토인", "향료", "아데노신",
]

def _extract_titleless(text: str) -> str:
    """타이틀 키 없이 성분 목록만 있는 이미지(OCR 결과) 처리.

    조건: 콤마 10개 이상 + 알려진 성분명 2개 이상 포함 시 그대로 추출.
    INGR_END_KEYS가 나오면 거기서 자른다.
    """
    clean = text.strip()
    if clean.count(",") < 10:
        return ""
    hits = sum(1 for t in _KNOWN_ING_TOKENS if t in clean)
    if hits < 2:
        return ""
    for ek in INGR_END_KEYS:
        ei = clean.find(ek)
        if ei != -1:
            clean = clean[:ei]
    return clean.strip()


def _ocr_image_url(img_url: str) -> str:
    try:
        r = requests.get(img_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code != 200:
            return ""
        img = Image.open(BytesIO(r.content))

        holder: list = [None]

        def _run():
            loop = asyncio.new_event_loop()
            try:
                holder[0] = loop.run_until_complete(winocr.recognize_pil(img, "ko"))
            finally:
                loop.close()

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        t.join(timeout=30)
        result = holder[0]
        return result.text if result else ""
    except Exception as e:
        print(f"    [OCR 오류] {e}")
        return ""


def _click_expand_btn(driver) -> bool:
    """상세정보 펼쳐보기 버튼을 찾아 클릭한다. 성공 시 True.

    셀렉터 우선순위:
      1. data-shp-area='detailitm.more'  — 사용자가 확인한 주 셀렉터, 텍스트 무관
      2. data-shp-area-id='more'         — 일부 페이지의 대체 속성, 텍스트 무관
      3. data-resize-on-click / aria-expanded  — 범용 속성, 텍스트 검증 필수
      4. XPath 텍스트 매칭               — 최후 수단
    각 후보마다 is_displayed()를 확인해 숨겨진 버튼은 건너뜀.
    """
    # (셀렉터, 텍스트 힌트 목록)  힌트가 None이면 텍스트 검증 생략
    # 버튼 텍스트는 항상 "상세정보 펼쳐보기"로 고정
    CSS_SELECTORS = [
        ("button[data-shp-area='detailitm.more']",  None),                    # 확인된 주 셀렉터
        ("button.o97Gq32ql5",                        ["상세정보 펼쳐보기"]),   # 클래스 + 텍스트
        ("button[data-shp-area-id='more']",          ["상세정보 펼쳐보기"]),   # area-id + 텍스트
        ("button[data-resize-on-click='false']",     ["상세정보 펼쳐보기"]),   # 속성 + 텍스트
        ("button[aria-expanded='false']",            ["상세정보 펼쳐보기"]),   # aria + 텍스트
    ]
    XPATH_FALLBACKS = [
        "//button[.//span[contains(text(),'상세정보 펼쳐보기')]]",
        "//button[contains(.,'상세정보 펼쳐보기')]",
    ]

    def _do_click(btn) -> bool:
        if not btn.is_displayed():
            return False
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
        time.sleep(0.4)
        driver.execute_script("arguments[0].click();", btn)
        return True

    def _try_once() -> bool:
        for selector, hints in CSS_SELECTORS:
            try:
                for btn in driver.find_elements(By.CSS_SELECTOR, selector):
                    if hints and not any(h in btn.text for h in hints):
                        continue
                    if _do_click(btn):
                        print(f"    [A] 펼쳐보기 클릭 ({selector})")
                        return True
            except Exception:
                continue

        for xpath in XPATH_FALLBACKS:
            try:
                for btn in driver.find_elements(By.XPATH, xpath):
                    if _do_click(btn):
                        print(f"    [A] 펼쳐보기 클릭 (XPath: {xpath})")
                        return True
            except Exception:
                continue

        return False

    if _try_once():
        return True

    # 실패 시 2.0초 간격으로 최대 3회 재시도
    for attempt in range(1, 4):
        time.sleep(2.0)
        print(f"    [A] 재시도 {attempt}/3 ...")
        if _try_once():
            return True

    return False


def _back_to_product_info(driver) -> None:
    """리뷰 수집 후 스크롤 위치를 최상단으로 되돌린다."""
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(0.5)


def _extract_via_winocr(driver) -> str:
    # 리뷰 수집 후 리뷰 탭에 머물러 있을 수 있으므로 상품정보 탭으로 먼저 복귀
    _back_to_product_info(driver)

    # A. 펼쳐보기 버튼 클릭
    #    한 번에 내리면 DOM 렌더링 전에 탐색해서 못 찾으므로 300px씩 단계적으로 스크롤
    mid_h = driver.execute_script("return document.body.scrollHeight") // 2
    for pos in range(0, mid_h, 300):
        driver.execute_script(f"window.scrollTo(0, {pos});")
        time.sleep(0.15)
    time.sleep(1.0)

    if _click_expand_btn(driver):
        time.sleep(2.5)
    else:
        print("    [A] 펼쳐보기 버튼 없음 (생략)")

    # B. 6회 스크롤로 lazy-load 트리거
    for _ in range(6):
        curr_h = driver.execute_script("return document.body.scrollHeight")
        for sy in range(0, curr_h, 600):
            driver.execute_script(f"window.scrollTo(0, {sy});")
            time.sleep(0.12)
        time.sleep(0.5)
    print(f"    [B] 스크롤 완료 ({curr_h}px)")

    # C. 이미지 URL 수집
    #    - img 태그: src base URL + naturalHeight/Width
    #    - a[data-linkdata]: originalHeight/Width(실제 원본 크기) 포함 → 표시 크기에 무관하게 정확
    #    - review-phinf / profile-phinf / shopping-phinf 노이즈 제거
    raw_data = driver.execute_script("""
        const r = [];
        const seen = new Set();

        function isNoise(src) {
            return src.includes('review-phinf') || src.includes('profile-phinf') ||
                   src.includes('shopping-phinf') || src.includes('/checkout/');
        }

        function collectImgs(doc) {
            // img 태그
            doc.querySelectorAll('img').forEach(img => {
                const rawSrc = img.getAttribute('src') || img.getAttribute('data-src') || '';
                const base  = rawSrc.split('?')[0];
                if (!base || !base.includes('shop-phinf') || isNoise(base) || seen.has(base)) return;
                const h = img.naturalHeight || parseInt(img.getAttribute('height') || 0);
                const w = img.naturalWidth  || parseInt(img.getAttribute('width')  || 0);
                seen.add(base);
                r.push({src: base, h, w});
            });

            // a[data-linkdata] — originalHeight/Width로 실제 이미지 크기 확인
            doc.querySelectorAll('a[data-linkdata]').forEach(a => {
                try {
                    const d   = JSON.parse(a.getAttribute('data-linkdata'));
                    const src = (d.src || '').split('?')[0];
                    if (!src || !src.includes('shop-phinf') || isNoise(src) || seen.has(src)) return;
                    if (d.linkUse === 'true' || d.linkUse === true) return;
                    const h = parseInt(d.originalHeight || 0);
                    const w = parseInt(d.originalWidth  || 0);
                    seen.add(src);
                    r.push({src, h, w});
                } catch(e) {}
            });
        }

        collectImgs(document);
        document.querySelectorAll('iframe').forEach(iframe => {
            try { collectImgs(iframe.contentDocument || iframe.contentWindow.document); }
            catch(e) {}
        });

        return r;
    """)
    img_urls = []
    for item in (raw_data or []):
        src = item.get("src", "")
        h   = item.get("h", 0)
        w   = item.get("w", 0)
        if not src:
            continue
        if 0 < h < 200:   # 200px 미만 소형 이미지 제외
            continue
        if w > 0 and h > 0 and w / h > 5:   # 극단적 가로 배너 제외
            continue
        img_urls.append(src)
    print(f"    [C] 이미지 {len(img_urls)}개 수집")

    # D. 뒤에서부터 OCR
    for i, img_url in enumerate(reversed(img_urls), 1):
        fname = img_url.split("/")[-1]
        print(f"    [D-{i}/{len(img_urls)}] {fname}")
        text = _ocr_image_url(img_url)
        if not text:
            print("         → OCR 실패")
            continue
        ing = _extract_from_text(text) or _extract_titleless(text)
        if ing:
            print(f"         → 전성분 발견 ({len(ing)}자)")
            return ing
        print(f"         → 미매칭 | {text[:60].strip()!r}")
    return ""


# ── 메인 진입점 ──────────────────────────────────────────────────────────────

def get_ingredients(driver, url: str) -> tuple[str, str]:
    """
    (ingredients, source) 반환. source: 'api' | 'text' | 'ocr' | 'none'

    1. 직접 HTTP API 호출 (브라우저 쿠키 재사용, 페이지 로드 불필요)
    2. 브라우저 인터셉터 notice (이미 로드된 페이지면 재탐색 생략)
    3. 본문 텍스트(innerText) 추출
    4. winocr 이미지 OCR 폴백
    """
    # 1. 직접 API
    ing = _try_notice_api_direct(driver, url)
    if ing:
        print(f"    [직접API] 전성분 {len(ing)}자")
        return ing, "api"
    print("    ✗ 직접API: 없음")

    # 2. 브라우저 인터셉터 (main 루프에서 이미 페이지 로드 → 재탐색 생략)
    notice = driver.execute_script("return window.__productNotice;")
    if not notice:
        driver.execute_script("window.__productNotice = null;")
        driver.get(url)
        time.sleep(5)
        notice = driver.execute_script("return window.__productNotice;")
        if not notice:
            for _ in range(14):   # 추가 최대 7초
                time.sleep(0.5)
                notice = driver.execute_script("return window.__productNotice;")
                if notice:
                    break

    if notice:
        ing = _extract_notice_values_deep(notice)
        if ing:
            print(f"    [인터셉터] 전성분 {len(ing)}자")
            return ing, "api"
        print("    ✗ 인터셉터: 매칭 키 없음")
    else:
        print("    ✗ 인터셉터: API 응답 없음")

    # 3. 본문 텍스트 추출 (OCR보다 빠름)
    body = driver.execute_script("return document.body ? document.body.innerText : ''") or ""
    ing = _extract_from_text(body)
    if ing:
        print(f"    [본문텍스트] 전성분 {len(ing)}자")
        return ing, "text"
    print("    ✗ 본문텍스트: 없음 → winocr 폴백")

    # 4. winocr 이미지 OCR
    ing = _extract_via_winocr(driver)
    if ing:
        return ing, "ocr"
    return "전성분 미제공", "none"
