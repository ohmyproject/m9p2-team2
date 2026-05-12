import time

from selenium.webdriver.common.by import By

from crawler.config import SORT_MAP


def apply_sort(driver, sort_type):
    target_text = SORT_MAP.get(sort_type, sort_type)

    print(f"[정렬] {target_text}")

    for attempt in range(5):
        try:
            candidates = driver.find_elements(
                By.XPATH,
                f"//*[contains(normalize-space(text()), '{target_text}')]",
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
                    time.sleep(2)

                    print(f"[정렬 완료] {target_text}")
                    return

                except Exception:
                    continue

        except Exception:
            pass

        time.sleep(1)

    raise Exception(f"정렬 버튼을 찾지 못했습니다: {target_text}")