# 브라우저 실행만 담당합니다.

from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def create_driver():
    """
    크롬 브라우저를 실행합니다.
    headless는 사용하지 않습니다.
    """

    options = Options()
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(options=options)
    driver.maximize_window()

    return driver