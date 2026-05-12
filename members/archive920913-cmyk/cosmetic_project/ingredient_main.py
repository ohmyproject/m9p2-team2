import os

from crawler.config import DATA_DIR
from ingredients.b_ingredient_retry import (
    process_csv,
    build_main_ingredients_history,
    fill_main_ingredients_from_history,
)


def is_target_product_csv(filename):
    return (
        "_Data(oliveyoung)_" in filename
        and filename.endswith(".csv")
        and "_cleaned" not in filename
        and "_ingredients" not in filename
    )


def group_key(filename):
    return filename.replace("_retry", "").replace(".csv", "")


def score(filename):
    if "_retry" in filename:
        return 10

    return 0


def find_product_files():
    if not os.path.exists(DATA_DIR):
        return []

    grouped = {}

    for filename in os.listdir(DATA_DIR):
        if not is_target_product_csv(filename):
            continue

        key = group_key(filename)

        if key not in grouped:
            grouped[key] = filename
            continue

        if score(filename) > score(grouped[key]):
            grouped[key] = filename

    return [
        os.path.join(DATA_DIR, filename)
        for filename in sorted(grouped.values())
    ]


def ask_yes_no(message, default="y"):
    value = input(f"{message} [y/n, 기본값: {default}]: ").strip().lower()

    if value == "":
        value = default

    return value == "y"


def main():
    print("=" * 70)
    print("B방식 OpenAI OCR 주요성분 재수집")
    print("=" * 70)

    files = find_product_files()

    if not files:
        print("[중단] 처리할 상품 CSV가 없습니다.")
        return

    print("[대상 파일]")

    for path in files:
        print("-", os.path.basename(path))

    print("=" * 70)
    print("[안내]")
    print("원본 CSV와 _retry.csv가 둘 다 있으면 _retry.csv만 처리합니다.")
    print("main_ingredients가 비어 있는 상품만 처리합니다.")
    print("먼저 Data 폴더 전체에서 같은 goods_no의 기존 main_ingredients를 재사용합니다.")
    print("그래도 비어 있는 상품만 GPT OCR을 실행합니다.")
    print("저장 형식은 B방식: Representative(INCI Ingredient) 입니다.")

    run = ask_yes_no("진행할까요?", "y")

    if not run:
        print("[취소] 종료합니다.")
        return

    print("=" * 70)
    print("[1단계] 기존 main_ingredients 이력 수집")
    history = build_main_ingredients_history(DATA_DIR)
    print(f"[이력] goods_no 기준 기존 주요성분: {len(history)}개")

    print("=" * 70)
    print("[2단계] 기존 값 재사용")

    total_filled = 0

    for path in files:
        filled = fill_main_ingredients_from_history(path, history)
        total_filled += filled
        print(f"- {os.path.basename(path)}: {filled}개 복사")

    print(f"[재사용 완료] 총 {total_filled}개 복사")

    print("=" * 70)
    print("[3단계] 아직 빈 값만 GPT OCR 실행")

    for path in files:
        process_csv(path, recrawl_all=False)

    print("=" * 70)
    print("[완료] B방식 주요성분 재수집 종료")


if __name__ == "__main__":
    main()