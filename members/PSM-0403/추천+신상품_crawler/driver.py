"""Chrome 드라이버 초기화"""
import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait

VERSION_MAIN = 147  # 로컬 Chrome 버전에 맞게 변경

def create_driver(version_main: int = VERSION_MAIN):
    options = uc.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=ko-KR")
    driver = uc.Chrome(options=options, use_subprocess=True, version_main=version_main)
    wait   = WebDriverWait(driver, 20)
    return driver, wait
