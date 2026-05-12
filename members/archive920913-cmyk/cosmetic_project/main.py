from crawler.collector import OliveYoungCollector


def ask_text(message, default_value):
    user_input = input(f"{message} [기본값: {default_value}]: ").strip()

    if user_input == "":
        return default_value

    return user_input


def ask_int(message, default_value):
    user_input = input(f"{message} [기본값: {default_value}]: ").strip()

    if user_input == "":
        return default_value

    try:
        return int(user_input)
    except ValueError:
        print(f"[입력 오류] 숫자만 입력해야 합니다. 기본값 {default_value}로 진행합니다.")
        return default_value


def main():
    print("=" * 70)
    print("올리브영 크롤러 실행 설정")
    print("=" * 70)

    category_name = ask_text(
        "수집할 세부 카테고리를 입력하세요",
        "에센스/세럼/앰플",
    )

    sort_input = ask_text(
        "수집할 정렬을 입력하세요. 여러 개면 쉼표로 구분하세요",
        "판매순,신상품순",
    )

    sort_types = [
        sort_type.strip()
        for sort_type in sort_input.split(",")
        if sort_type.strip()
    ]

    max_products = ask_int(
        "정렬별 수집할 제품 개수를 입력하세요",
        24,
    )

    reviews_per_product = ask_int(
        "상품당 수집할 리뷰 개수를 입력하세요",
        10,
    )

    print("=" * 70)
    print("[실행 설정 확인]")
    print(f"카테고리: {category_name}")
    print(f"정렬: {sort_types}")
    print(f"정렬별 제품 개수: {max_products}")
    print(f"상품당 리뷰 개수: {reviews_per_product}")
    print("=" * 70)

    for sort_type in sort_types:
        crawler = OliveYoungCollector(
            sort_type=sort_type,
            category_name=category_name,
            max_products=max_products,
            reviews_per_product=reviews_per_product,
        )

        crawler.run()


if __name__ == "__main__":
    main()