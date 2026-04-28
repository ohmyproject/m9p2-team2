"""쿠키 저장 / 로드"""
import pickle, os, time
import undetected_chromedriver as uc

COOKIE_FILE = "naver_cookies.pkl"

def save_cookies(cookie_file: str = COOKIE_FILE):
    """브라우저 열어서 로그인 후 쿠키 저장"""
    options = uc.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=ko-KR")
    driver = uc.Chrome(options=options, use_subprocess=True,version_main=147)
    driver.get("https://www.naver.com")
    print("브라우저에서 네이버에 로그인하세요.")
    input("로그인 완료 후 Enter 키를 누르세요...")
    with open(cookie_file, "wb") as f:
        pickle.dump(driver.get_cookies(), f)
    driver.quit()
    print(f"쿠키 저장 완료 → {cookie_file}")

def load_cookies(driver, cookie_file: str = COOKIE_FILE):
    """저장된 쿠키를 드라이버에 로드"""
    if not os.path.exists(cookie_file):
        print(f"[경고] 쿠키 파일 없음: {cookie_file}")
        return False
    driver.get("https://www.naver.com")
    time.sleep(2)
    with open(cookie_file, "rb") as f:
        for c in pickle.load(f):
            try:
                driver.add_cookie(c)
            except Exception:
                pass
    driver.refresh()
    time.sleep(2)
    print("쿠키 로드 완료")
    return True
