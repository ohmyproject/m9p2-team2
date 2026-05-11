import argparse
import glob
import os
import re
import time

import pandas as pd

from crawler.browser import create_driver
from crawler.review_detail import collect_reviews


def load_products_from_data_csv(data_file):
    """
    기존 Data CSV에서 리뷰 재수집에 필요한 상품 정보만 읽습니다.
    """
    df = pd.read_csv(data_file)

    required_cols = ["rank", "product_name", "review_count", "url"]

    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Data CSV에 '{col}' 컬럼이 없습니다: {data_file}")

    # sort_type 컬럼이 없으면 빈 값 생성
    if "sort_type" not in df.columns:
        df["sort_type"] = ""

    # main_ingredients 컬럼이 없으면 빈 값 생성
    if "main_ingredients" not in df.columns:
        df["main_ingredients"] = ""

    # date 컬럼이 없으면 파일명 날짜에서 생성
    if "date" not in df.columns:
        file_date = extract_date_from_data_file(data_file)
        df["date"] = file_date if file_date else ""

    df = df.dropna(subset=["url"])
    df = df.reset_index(drop=True)

    return df


def extract_datetime_prefix_from_data_file(data_file):
    """
    Data 파일명에서 날짜_시간 prefix를 추출합니다.

    예:
    2026-05-01_192305_Data(oliveyoung)_판매량순.csv
    → 2026-05-01_192305
    """
    basename = os.path.basename(data_file)

    match = re.match(
        r"(\d{4}-\d{2}-\d{2}_\d{6})_Data\(oliveyoung\)_.*\.csv",
        basename
    )

    if match:
        return match.group(1)

    match = re.search(r"(\d{4}-\d{2}-\d{2}_\d{6})", basename)

    if match:
        return match.group(1)

    return None


def extract_date_from_data_file(data_file):
    """
    Data 파일명에서 날짜만 추출합니다.

    예:
    2026-05-01_192305_Data(oliveyoung)_판매량순.csv
    → 2026-05-01
    """
    basename = os.path.basename(data_file)

    match = re.search(r"(\d{4}-\d{2}-\d{2})", basename)

    if match:
        return match.group(1)

    return ""


def guess_sort_type(data_file, products):
    """
    CSV 내부 sort_type이 없거나 비어 있으면 파일명에서 정렬명을 추정합니다.
    """
    sort_type = ""

    if len(products) > 0 and "sort_type" in products.columns:
        sort_type = str(products.iloc[0].get("sort_type", "")).strip()

    if sort_type:
        return sort_type

    basename = os.path.basename(data_file)

    if "판매량순" in basename:
        return "판매량순"
    if "판매순" in basename:
        return "판매순"
    if "신상품순" in basename:
        return "신상품순"
    if "인기순" in basename:
        return "인기순"
    if "낮은가격순" in basename or "낮은 가격순" in basename:
        return "낮은가격순"
    if "할인율순" in basename:
        return "할인율순"

    return "리뷰재수집"


def save_review_csv_by_data_file_date(
    review_rows,
    data_file,
    sort_type,
    output_dir="Data",
    overwrite=True,
):
    """
    실행 날짜가 아니라 Data 파일 날짜/시간을 기준으로 Review CSV를 저장합니다.

    예:
    2026-05-01_192305_Data(oliveyoung)_판매량순.csv
    → 2026-05-01_192305_Review(oliveyoung)_판매량순.csv
    """
    os.makedirs(output_dir, exist_ok=True)

    datetime_prefix = extract_datetime_prefix_from_data_file(data_file)

    if datetime_prefix:
        filename = f"{datetime_prefix}_Review(oliveyoung)_{sort_type}.csv"
    else:
        filename = f"Review(oliveyoung)_{sort_type}.csv"

    output_path = os.path.join(output_dir, filename)

    if not overwrite and os.path.exists(output_path):
        filename = filename.replace(".csv", "_recrawl.csv")
        output_path = os.path.join(output_dir, filename)

    df = pd.DataFrame(review_rows)

    # 리뷰가 0건이어도 컬럼 구조는 유지되게 처리
    expected_cols = [
        "date",
        "platform",
        "sort_type",
        "rank",
        "main_ingredients",
        "product_name",
        "review_count",
        "review_rating",
        "skin_type",
        "review_text",
        "url",
    ]

    for col in expected_cols:
        if col not in df.columns:
            df[col] = ""

    df = df[expected_cols]

    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    return output_path


def collect_reviews_only(
    data_file,
    reviews_per_product=10,
    start_rank=None,
    end_rank=None,
    driver=None,
    overwrite=True,
):
    """
    상품정보 CSV를 기준으로 리뷰만 다시 수집합니다.
    Data CSV의 date 컬럼을 읽어서 Review CSV의 date 컬럼에도 동일하게 넣습니다.
    """
    products = load_products_from_data_csv(data_file)

    if start_rank is not None:
        products = products[products["rank"] >= start_rank]

    if end_rank is not None:
        products = products[products["rank"] <= end_rank]

    if products.empty:
        print(f"[건너뜀] 수집할 상품이 없습니다: {data_file}")
        return None

    sort_type = guess_sort_type(data_file, products)

    print("=" * 70)
    print("[시작] 리뷰만 재수집")
    print(f"[Data 파일] {data_file}")
    print(f"[정렬] {sort_type}")
    print(f"[상품 수] {len(products)}")
    print(f"[상품당 리뷰 수] {reviews_per_product}")
    print("=" * 70)

    own_driver = False

    if driver is None:
        driver = create_driver()
        own_driver = True

    review_rows = []

    try:
        for _, product in products.iterrows():
            rank = int(product["rank"])
            product_name = str(product["product_name"])
            product_url = str(product["url"])

            review_count = product.get("review_count", "")
            main_ingredients = product.get("main_ingredients", "")

            # 핵심: 제품정보 Data CSV의 date 값을 그대로 사용
            product_date = product.get("date", "")

            if pd.isna(product_date) or str(product_date).strip() == "":
                product_date = extract_date_from_data_file(data_file)

            product_date = str(product_date).strip()

            print("-" * 70)
            print(f"[리뷰 재수집] rank={rank} / {product_name}")
            print(f"[제품정보 날짜] {product_date}")
            print(f"[URL] {product_url}")

            try:
                driver.get(product_url)
                time.sleep(2)

                reviews = collect_reviews(
                    driver=driver,
                    sort_type=sort_type,
                    rank=rank,
                    product_name=product_name,
                    review_count=review_count,
                    product_url=product_url,
                    limit=reviews_per_product,
                )

                for row in reviews:
                    # collect_reviews() 안에서 today()로 들어간 date를
                    # 제품정보 CSV의 date 값으로 덮어쓰기
                    row["date"] = product_date

                    # 제품정보의 main_ingredients도 그대로 유지
                    row["main_ingredients"] = main_ingredients

                    # 혹시 sort_type도 제품정보 기준으로 통일
                    row["sort_type"] = sort_type

                    # 상품명, 리뷰수, URL도 제품정보 기준으로 통일
                    row["rank"] = rank
                    row["product_name"] = product_name
                    row["review_count"] = review_count
                    row["url"] = product_url

                review_rows.extend(reviews)

                print(f"[성공] 리뷰 {len(reviews)}건 수집")

            except Exception as e:
                print(f"[오류] rank={rank} 리뷰 수집 실패: {e}")

    finally:
        if own_driver and driver:
            driver.quit()

    output_file = save_review_csv_by_data_file_date(
        review_rows=review_rows,
        data_file=data_file,
        sort_type=sort_type,
        output_dir="Data",
        overwrite=overwrite,
    )

    print("=" * 70)
    print(f"[완료] 리뷰 재수집 저장: {output_file}")
    print(f"[총 리뷰 행 수] {len(review_rows)}")
    print("=" * 70)

    return output_file


def find_data_files(data_dir):
    """
    Data 폴더 안에서 제품정보 CSV만 찾습니다.
    Review CSV는 제외합니다.
    """
    pattern = os.path.join(data_dir, "*Data(oliveyoung)*.csv")
    files = glob.glob(pattern)

    data_files = []

    for file in files:
        basename = os.path.basename(file)

        if "Review(oliveyoung)" in basename:
            continue

        if "Data(oliveyoung)" not in basename:
            continue

        data_files.append(file)

    data_files.sort()

    return data_files


def collect_reviews_for_all_data_files(
    data_dir,
    reviews_per_product=10,
    start_rank=None,
    end_rank=None,
    overwrite=True,
):
    """
    Data 폴더 안의 모든 제품정보 CSV를 기준으로 리뷰만 재수집합니다.
    각각의 Review 파일명과 date 컬럼은 해당 Data 파일 기준으로 맞춥니다.
    """
    data_files = find_data_files(data_dir)

    if not data_files:
        print(f"[중단] Data 파일을 찾지 못했습니다: {data_dir}")
        return

    print("=" * 70)
    print("[전체 재수집 모드]")
    print(f"[Data 폴더] {data_dir}")
    print(f"[대상 파일 수] {len(data_files)}")
    print("=" * 70)

    for idx, file in enumerate(data_files, start=1):
        print(f"{idx}. {file}")

    driver = create_driver()

    output_files = []

    try:
        for idx, data_file in enumerate(data_files, start=1):
            print("\n" + "#" * 70)
            print(f"[전체 진행] {idx}/{len(data_files)}")
            print(f"[처리 파일] {data_file}")
            print("#" * 70)

            try:
                output_file = collect_reviews_only(
                    data_file=data_file,
                    reviews_per_product=reviews_per_product,
                    start_rank=start_rank,
                    end_rank=end_rank,
                    driver=driver,
                    overwrite=overwrite,
                )

                if output_file:
                    output_files.append(output_file)

            except Exception as e:
                print(f"[파일 처리 오류] {data_file}: {e}")

    finally:
        driver.quit()

    print("\n" + "=" * 70)
    print("[전체 재수집 완료]")
    print(f"[생성된 리뷰 파일 수] {len(output_files)}")

    for output_file in output_files:
        print(f"- {output_file}")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--data-file",
        default=None,
        help="기존 Data CSV 경로. 하나만 재수집할 때 사용"
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Data 폴더 안의 모든 Data CSV 기준으로 리뷰 재수집"
    )

    parser.add_argument(
        "--data-dir",
        default="Data",
        help="전체 재수집할 Data 폴더 경로. 기본값: Data"
    )

    parser.add_argument(
        "--reviews-per-product",
        type=int,
        default=10,
        help="상품별 다시 수집할 리뷰 수"
    )

    parser.add_argument(
        "--start-rank",
        type=int,
        default=None,
        help="재수집 시작 rank"
    )

    parser.add_argument(
        "--end-rank",
        type=int,
        default=None,
        help="재수집 종료 rank"
    )

    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="기존 Review 파일을 덮어쓰지 않고 _recrawl 파일로 저장"
    )

    args = parser.parse_args()

    overwrite = not args.no_overwrite

    if args.all:
        collect_reviews_for_all_data_files(
            data_dir=args.data_dir,
            reviews_per_product=args.reviews_per_product,
            start_rank=args.start_rank,
            end_rank=args.end_rank,
            overwrite=overwrite,
        )
        return

    if args.data_file:
        collect_reviews_only(
            data_file=args.data_file,
            reviews_per_product=args.reviews_per_product,
            start_rank=args.start_rank,
            end_rank=args.end_rank,
            overwrite=overwrite,
        )
        return

    print("[사용법]")
    print()
    print("1개 파일만 리뷰 재수집:")
    print('python review_only_main.py --data-file "Data/파일명.csv" --reviews-per-product 10')
    print()
    print("Data 폴더 전체 리뷰 재수집:")
    print("python review_only_main.py --all --reviews-per-product 10")
    print()
    print("기존 Review 파일 덮어쓰기 싫을 때:")
    print("python review_only_main.py --all --reviews-per-product 10 --no-overwrite")


if __name__ == "__main__":
    main()