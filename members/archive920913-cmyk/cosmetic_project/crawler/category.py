import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def move_to_essence_category(driver, category_name="에센스/세럼/앰플"):
    """
    올리브영 메인에서
    카테고리 메뉴 클릭 → 에센스/세럼/앰플 클릭 → 상품 목록 로딩 확인
    """

    wait = WebDriverWait(driver, 10)

    # 올리브영 메인 화면이 완전히 뜨기도 전에 카테고리를 누르면 실패함
    wait_oliveyoung_main_ready(driver, max_wait=10)

    print("[1] 카테고리 버튼 클릭")

    click_category_button(driver)

    time.sleep(1)

    print(f"[2] 세부 카테고리 클릭: {category_name}")

    click_detail_category(driver, category_name)

    # 제일 중요:
    # 세부 카테고리 클릭 후 상품목록/정렬 버튼이 뜰 때까지 기다림
    wait_after_category_click(driver, max_wait=5)

    check_human_page(driver)

    return True


def click_category_button(driver):
    """
    올리브영 상단의 카테고리 버튼 클릭.
    기존 방식처럼 텍스트 기준으로 찾고 클릭한다.
    """

    candidates = driver.find_elements(
        By.XPATH,
        "//*[contains(normalize-space(text()), '카테고리')]",
    )

    for el in candidates:
        try:
            if not el.is_displayed():
                continue

            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});",
                el,
            )
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", el)
            time.sleep(1)
            return True

        except Exception:
            continue

    # 텍스트로 못 찾으면 JS로 한 번 더 찾기
    result = driver.execute_script(
        """
        const els = Array.from(document.querySelectorAll('button,a,span,div'));
        const target = els.find(el => {
            const text = (el.innerText || el.textContent || '').trim();
            return text.includes('카테고리');
        });

        if (!target) return false;

        target.scrollIntoView({block: 'center'});
        target.click();
        return true;
        """
    )

    if not result:
        raise Exception("카테고리 버튼을 찾지 못했습니다.")

    time.sleep(1)
    return True


def click_detail_category(driver, category_name):
    """
    카테고리 메뉴 안에서 세부 카테고리 클릭.
    예: 에센스/세럼/앰플
    """

    candidates = driver.find_elements(
        By.XPATH,
        f"//*[contains(normalize-space(text()), '{category_name}')]",
    )

    for el in candidates:
        try:
            if not el.is_displayed():
                continue

            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});",
                el,
            )
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", el)
            time.sleep(1)
            return True

        except Exception:
            continue

    # XPath로 못 찾으면 JS로 다시 찾기
    result = driver.execute_script(
        """
        const categoryName = arguments[0];

        const els = Array.from(
            document.querySelectorAll('a,button,span,li,div')
        );

        const target = els.find(el => {
            const text = (el.innerText || el.textContent || '').trim();
            return text.includes(categoryName);
        });

        if (!target) return false;

        target.scrollIntoView({block: 'center'});
        target.click();
        return true;
        """,
        category_name,
    )

    if not result:
        raise Exception(f"세부 카테고리를 찾지 못했습니다: {category_name}")

    time.sleep(1)
    return True


def wait_oliveyoung_main_ready(driver, max_wait=10):
    """
    올리브영 메인 페이지가 실제로 뜰 때까지 기다림.
    URL만 바뀌었다고 바로 다음 단계로 넘어가지 않게 함.
    """

    print("[대기] 올리브영 메인 화면 확인")

    start_time = time.time()

    while time.time() - start_time < max_wait:
        try:
            ready_state = driver.execute_script("return document.readyState")
            body_text = driver.find_element(By.TAG_NAME, "body").text.strip()

            if ready_state == "complete" and len(body_text) > 100:
                keywords = [
                    "카테고리",
                    "오특",
                    "랭킹",
                    "검색",
                    "올리브영",
                    "장바구니",
                ]

                if any(keyword in body_text for keyword in keywords):
                    print("[대기 완료] 올리브영 메인 화면 확인")
                    return True

        except Exception:
            pass

        time.sleep(0.5)

    print("[주의] 올리브영 메인 화면 자동 확인 실패")
    print("브라우저에 올리브영 메인 화면이 보이면 Enter를 누르세요.")
    input("확인 후 Enter: ")

    return True


def wait_after_category_click(driver, max_wait=5):
    """
    세부 카테고리 클릭 후 상품 목록이 뜰 때까지 기다림.

    중요:
    - 무조건 5초 sleep 아님
    - 상품 목록/정렬 영역이 확인되면 바로 진행
    - 최대 5초까지만 자동 확인
    - 실패하면 사용자가 직접 화면 확인 후 Enter
    """

    print(f"[대기] 세부 카테고리 로딩 확인 최대 {max_wait}초")

    start_time = time.time()

    while time.time() - start_time < max_wait:
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text
        except Exception:
            body_text = ""

        if is_category_list_ready(driver, body_text):
            print("[대기 완료] 상품 목록/정렬 영역 확인")
            return True

        time.sleep(0.5)

    print("[주의] 5초 안에 상품 목록/정렬 영역을 자동 확인하지 못했습니다.")
    print("브라우저에서 에센스/세럼/앰플 상품 목록이 보이면 Enter를 누르세요.")
    input("상품 목록 확인 후 Enter: ")

    return True


def is_category_list_ready(driver, body_text):
    """
    카테고리 상품 목록 페이지가 실제로 떴는지 확인.
    """

    if not body_text:
        return False

    lower_text = body_text.lower()

    block_keywords = [
        "사람인지 확인",
        "로봇이 아닙니다",
        "보안 확인",
        "자동입력 방지",
        "captcha",
        "verify",
    ]

    for keyword in block_keywords:
        if keyword.lower() in lower_text:
            return False

    # 정렬 버튼이 보이면 상품 목록 페이지로 판단
    sort_keywords = [
        "판매순",
        "판매량순",
        "신상품순",
        "인기순",
        "낮은 가격순",
        "할인율순",
    ]

    for keyword in sort_keywords:
        if keyword in body_text:
            return True

    # 상품 상세 링크가 있으면 상품 목록 페이지로 판단
    try:
        product_link_count = driver.execute_script(
            """
            return Array.from(document.querySelectorAll('a[href]'))
                .filter(a => {
                    const href = a.href || '';
                    return href.includes('getGoodsDetail.do') || href.includes('goodsNo=');
                }).length;
            """
        )

        if product_link_count and int(product_link_count) > 0:
            return True

    except Exception:
        pass

    return False


def check_human_page(driver):
    """
    사람 확인 화면이 있으면 사용자가 직접 처리할 수 있게 멈춤.
    """

    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text
    except Exception:
        return

    lower_text = body_text.lower()

    keywords = [
        "사람인지 확인",
        "로봇이 아닙니다",
        "보안 확인",
        "자동입력 방지",
        "captcha",
        "verify",
    ]

    detected = any(keyword.lower() in lower_text for keyword in keywords)

    if not detected:
        print("[확인] 사람 확인 화면 없음")
        return

    print("=" * 70)
    print("[사람 확인 화면 감지]")
    print("브라우저에서 직접 사람 확인을 완료하세요.")
    input("완료 후 Enter: ")


def move_to_category(driver, category_name="에센스/세럼/앰플"):
    return move_to_essence_category(driver, category_name)