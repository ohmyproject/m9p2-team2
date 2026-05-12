from validate.validator import run_validation, find_csv_files
from retry.reuse_existing import prefill_from_existing
from retry.retry_products import retry_product_file
from retry.retry_reviews import find_review_file, retry_review_file


def ask_int(message, default):
    value = input(f"{message} [기본값: {default}]: ").strip()

    if value == "":
        return default

    try:
        return int(value)
    except Exception:
        return default


def ask_yes_no(message, default="y"):
    value = input(f"{message} [y/n, 기본값: {default}]: ").strip().lower()

    if value == "":
        value = default

    return value == "y"


def main():
    print("=" * 70)
    print("누락 데이터 검증 및 재수집")
    print("=" * 70)

    target_reviews = ask_int("상품당 목표 리뷰 수", 10)

    print("=" * 70)
    print("[1단계] 재수집 전 검증")
    run_validation(target_reviews)

    product_files, review_files = find_csv_files()

    print("=" * 70)
    use_existing = ask_yes_no("기존 CSV 데이터로 먼저 누락값을 채울까요?", "y")

    if use_existing:
        prefill_from_existing(
            product_files=product_files,
            review_files=review_files,
            target_reviews=target_reviews,
        )

    print("=" * 70)
    print("[2단계] 기존 데이터 복사 후 재검증")
    run_validation(target_reviews)

    product_files, review_files = find_csv_files()

    run_product_retry = ask_yes_no("그래도 부족한 상품정보를 사이트에서 재수집할까요?", "y")

    if run_product_retry:
        print("=" * 70)
        print("[3단계] 상품정보 사이트 재수집")

        for path in product_files:
            retry_product_file(path)
    else:
        print("[건너뜀] 상품정보 사이트 재수집 생략")

    product_files, review_files = find_csv_files()

    run_review_retry = ask_yes_no("그래도 부족한 리뷰를 사이트에서 재수집할까요?", "y")

    if run_review_retry:
        print("=" * 70)
        print("[4단계] 리뷰 사이트 재수집")

        for product_file in product_files:
            review_file = find_review_file(product_file, review_files)

            retry_review_file(
                product_file=product_file,
                review_file=review_file,
                target_reviews=target_reviews,
            )
    else:
        print("[건너뜀] 리뷰 사이트 재수집 생략")

    print("=" * 70)
    print("[5단계] 최종 검증")
    run_validation(target_reviews)

    print("=" * 70)
    print("[완료] 누락 데이터 검증 및 재수집 종료")


if __name__ == "__main__":
    main()