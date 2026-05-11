# 전체 흐름을 관리합니다.

import time

from crawler.browser import create_driver
from crawler.naver_entry import enter_oliveyoung_from_naver
from crawler.category import move_to_essence_category
from crawler.sorter import apply_sort
from crawler.product_list import (
    wait_product_list,
    get_product_count,
    get_product_summary_by_index,
    click_product_by_index,
    go_back_to_list,
)
from crawler.product_detail import collect_product_detail
from crawler.review_detail import collect_reviews
from crawler.writer import save_product_csv, save_review_csv
from crawler.utils import today


class OliveYoungCollector:
    """
    크롤러 전체 순서를 담당하는 관리자 클래스입니다.
    """

    def __init__(self, sort_type="판매순", max_products=3, reviews_per_product=3):
        self.sort_type = sort_type
        self.max_products = max_products
        self.reviews_per_product = reviews_per_product
        self.driver = None
        self.product_rows = []
        self.review_rows = []

    def run(self):
        try:
            print("=" * 70)
            print("[시작] 올리브영 클릭형 크롤러 시작")
            print("=" * 70)

            self.driver = create_driver()

            enter_oliveyoung_from_naver(self.driver)
            move_to_essence_category(self.driver)
            apply_sort(self.driver, self.sort_type)
            wait_product_list(self.driver)

            total = get_product_count(self.driver)
            count = min(self.max_products, total)

            print(f"[목록] 현재 상품 수: {total}")
            print(f"[수집] 실제 수집 상품 수: {count}")

            for index in range(count):
                self.collect_one_product(index)

            product_file = save_product_csv(self.product_rows, self.sort_type)
            review_file = save_review_csv(self.review_rows, self.sort_type)

            print(f"[완료] 상품정보 저장: {product_file}")
            print(f"[완료] 리뷰정보 저장: {review_file}")

        finally:
            # 확인용으로 브라우저는 닫지 않습니다.
            # 자동 종료하려면 아래 주석을 해제하세요.
            # if self.driver:
            #     self.driver.quit()
            pass

    def collect_one_product(self, index):
        print("-" * 70)
        print(f"[진행] {index + 1}번째 상품 처리 시작")

        # 상세페이지 들어가기 전 목록 URL 저장
        # 뒤로가기 실패 시 이 URL로 목록을 복구합니다.
        list_url = self.driver.current_url

        try:
            list_info = get_product_summary_by_index(self.driver, index)

            click_product_by_index(self.driver, index)

            detail = collect_product_detail(
                self.driver,
                sort_type=self.sort_type,
                rank=index + 1,
                list_info=list_info,
            )

            product = {**list_info, **detail}
            product["date"] = today()
            product["platform"] = "올리브영"
            product["sort_type"] = self.sort_type
            product["rank"] = index + 1

            self.product_rows.append(product)

            reviews = collect_reviews(
                self.driver,
                sort_type=self.sort_type,
                rank=index + 1,
                product_name=product["product_name"],
                review_count=product["review_count"],
                product_url=product["url"],
                limit=self.reviews_per_product,
            )

            self.review_rows.extend(reviews)

        except Exception as e:
            print(f"[오류] {index + 1}번째 상품 실패: {e}")

        finally:
            go_back_to_list(self.driver, list_url)
            time.sleep(1)