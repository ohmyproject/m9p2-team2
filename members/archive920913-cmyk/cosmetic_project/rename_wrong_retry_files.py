from pathlib import Path
import pandas as pd


DATA_DIR = Path("Data")


def is_review_file(path):
    try:
        df = pd.read_csv(path, dtype=str, encoding="utf-8-sig", nrows=1)
    except UnicodeDecodeError:
        df = pd.read_csv(path, dtype=str, encoding="cp949", nrows=1)
    except Exception as e:
        print(f"[읽기 실패] {path.name}: {e}")
        return False

    columns = set(df.columns)

    return "review_text" in columns or "skin_type" in columns or "review_rating" in columns


def main():
    targets = list(DATA_DIR.glob("*(info)*_retry.csv"))

    if not targets:
        print("[완료] 변경 대상 파일 없음")
        return

    for path in targets:
        if not is_review_file(path):
            print(f"[건너뜀] 상품 파일로 보임: {path.name}")
            continue

        new_name = path.name.replace("(info)", "(review)")
        new_path = path.with_name(new_name)

        if new_path.exists():
            print(f"[이미 존재] {new_name}")
            continue

        path.rename(new_path)
        print(f"[변경] {path.name} -> {new_name}")

    print("[완료] 파일명 정리 끝")


if __name__ == "__main__":
    main()