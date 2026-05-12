from database.supabase_importer import import_all_cleaned


def ask_yes_no(message, default="n"):
    value = input(f"{message} [y/n, 기본값: {default}]: ").strip().lower()

    if value == "":
        value = default

    return value == "y"


def main():
    print("=" * 70)
    print("cleaned CSV Supabase 적재")
    print("=" * 70)
    print("[방식] A 원본 Supabase 스키마 기준으로 적재합니다.")
    print("[테이블] products, product_snapshots, product_rankings,")
    print("        product_main_ingredients, product_full_ingredients, product_reviews")

    reset = ask_yes_no("Supabase 기존 A 테이블을 삭제하고 새로 적재할까요?", "n")

    import_all_cleaned(reset=reset)


if __name__ == "__main__":
    main()