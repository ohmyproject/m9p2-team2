import undetected_chromedriver as uc


def create_driver():
    options = uc.ChromeOptions()

    options.add_argument("--start-maximized")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-notifications")
    options.add_argument("--lang=ko-KR")

    # headless=False 필수 — Cloudflare는 headless 즉시 탐지
    driver = uc.Chrome(options=options, headless=False)
    driver.set_page_load_timeout(40)

    return driver