# 실행 시작 파일입니다.

from crawler.collector import OliveYoungCollector


def main():
    sort_types = ["판매순", "신상품순"]

    for sort_type in sort_types:
        print("=" * 70)
        print(f"[정렬 수집 시작] {sort_type}")
        print("=" * 70)

        crawler = OliveYoungCollector(
            sort_type=sort_type,
            max_products=24,
            reviews_per_product=10,
        )

        crawler.run()


if __name__ == "__main__":
    main()