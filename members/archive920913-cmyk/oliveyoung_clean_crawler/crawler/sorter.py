# 정렬 버튼 클릭입니다.

import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from crawler.config import WAIT_TIME, SORT_MAP


def apply_sort(driver, sort_type):
    """
    사용자가 입력한 정렬 기준을 화면에서 클릭합니다.
    """

    wait = WebDriverWait(driver, WAIT_TIME)
    target_text = SORT_MAP.get(sort_type)

    if not target_text:
        raise Exception(f"지원하지 않는 정렬명입니다: {sort_type}")

    print(f"[정렬] 목표 정렬: {target_text}")

    button = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, f"//*[contains(normalize-space(text()), '{target_text}')]")
        )
    )

    button.click()
    time.sleep(2)

    print("[정렬] 정렬 적용 완료")