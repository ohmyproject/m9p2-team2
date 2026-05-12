from crawler.browser import create_driver
from crawler.naver_entry import enter_oliveyoung_from_naver
from crawler.category import move_to_category
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
    def __init__(
        self,
        sort_type="판매순",
        category_name="에센스/세럼/앰플",
        max_products=24,
        reviews_per_product=10,
    ):
        self.sort_type = sort_type
        self.category_name = category_name
        self.max_products = max_products
        self.reviews_per_product = reviews_per_product
        self.driver = None
        self.product_rows = []
        self.review_rows = []

    def run(self):
        try:
            print("=" * 70)
            print("[시작] 올리브영 크롤링")
            print(f"[카테고리] {self.category_name}")
            print(f"[정렬] {self.sort_type}")
            print(f"[제품 개수] {self.max_products}")
            print(f"[리뷰 개수] {self.reviews_per_product}")
            print("=" * 70)

            self.driver = create_driver()

            enter_oliveyoung_from_naver(self.driver)
            move_to_category(self.driver, self.category_name)
            apply_sort(self.driver, self.sort_type)

            wait_product_list(self.driver)

            product_count = get_product_count(self.driver)
            limit = min(product_count, self.max_products)
            list_url = self.driver.current_url

            print(f"[목록] 현재 페이지 상품 수: {product_count}")
            print(f"[수집] 실제 수집 상품 수: {limit}")

            for index in range(limit):
                self.collect_one_product(index, list_url)

            save_product_csv(self.product_rows, self.sort_type)
            save_review_csv(self.review_rows, self.sort_type)

            print("=" * 70)
            print("[완료] 크롤링 종료")
            print(f"[상품 저장 개수] {len(self.product_rows)}")
            print(f"[리뷰 저장 개수] {len(self.review_rows)}")
            print("=" * 70)

        except Exception as e:
            print("[전체 에러]", e)

    def collect_one_product(self, index, list_url):
        rank = index + 1

        print("-" * 70)
        print(f"[상품 {rank}] 수집 시작")

        try:
            summary = get_product_summary_by_index(self.driver, index)
            click_product_by_index(self.driver, index)

            detail = collect_product_detail(self.driver)
            product_row = self.make_product_row(rank, summary, detail)
            self.product_rows.append(product_row)

            reviews = collect_reviews(
                self.driver,
                product_row,
                limit=self.reviews_per_product,
            )

            self.review_rows.extend(reviews)

            print(f"[상품 {rank}] 상품 수집 완료")
            print(f"[상품 {rank}] 리뷰 수집 개수: {len(reviews)}")

        except Exception as e:
            print(f"[상품 {rank}] 수집 실패:", e)

        finally:
            go_back_to_list(self.driver, list_url)
            wait_product_list(self.driver)

    def make_product_row(self, rank, summary, detail):
        row = {}

        if summary:
            row.update(summary)

        if detail:
            row.update(detail)

        row["date"] = today()
        row["platform"] = "oliveyoung"
        row["sort_type"] = self.sort_type
        row["rank"] = rank

        return row