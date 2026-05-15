"""
main_ingredients 컬럼을 화장품 성분 표준명 사전과 매칭해 standard_ingredients 컬럼을 추가합니다.

사용법:
  python standardize_ingredients.py

매칭 순서:
  1. 정규화 후 정확 일치 (공백·괄호·대소문자 무시)
  2. 부분 포함 (alias가 성분명에 포함되거나, 성분명이 alias에 포함)

동작 방식:
  1. TARGET_CSV 에서 main_ingredients 컬럼을 읽습니다.
  2. 쉼표로 구분된 각 성분을 사전에서 매칭합니다.
  3. 매칭된 표준명을 standard_ingredients 컬럼에 씁니다.
  4. 매칭되지 않은 성분은 비워둡니다.
  5. CSV를 덮어씁니다.
"""

import re
import sys
from pathlib import Path

# ============================================================
# 설정
# ============================================================

# None          → Data/ 폴더의 모든 (info) CSV 자동 선택
# 파일 1개      → Path("Data/oliveyoung_판매순(info)_260505.csv")
# 파일 여러 개  → [Path("Data/...csv"), Path("Data/...csv")]
TARGET_CSV = [Path("Data/oliveyoung_판매순(info)_260505.csv"),
              Path("Data/oliveyoung_판매순(info)_260504.csv"),
              Path("Data/oliveyoung_판매순(info)_260503.csv"),
              Path("Data/oliveyoung_판매순(info)_260502.csv"),
              Path("Data/oliveyoung_판매순(info)_260501.csv"),
              Path("Data/oliveyoung_신상품순(info)_260505.csv"),
              Path("Data/oliveyoung_신상품순(info)_260504.csv"),
              Path("Data/oliveyoung_신상품순(info)_260503.csv"),
              Path("Data/oliveyoung_신상품순(info)_260502.csv"),
              Path("Data/oliveyoung_신상품순(info)_260501.csv")]

# ============================================================

sys.path.insert(0, str(Path(__file__).parent))
import pandas as pd


# ─── 성분 표준명 사전 ──────────────────────────────────────────
# (표준명, [비표준·혼용 표기 + 영문명 리스트])
# 동일 alias가 여러 항목에 있으면 먼저 나오는 항목이 우선합니다.
_INGREDIENT_DICT: list[tuple[str, list[str]]] = [
    ("나이아신아마이드", [
        "니코틴아마이드", "비타민B3", "Niacinamide", "Nicotinamide", "Vitamin B3",
    ]),
    ("히알루론산", [
        "하이알루로닉애씨드", "하이드롤라이즈드하이알루로닉애씨드", "소듐하이알루로네이트",
        "저분자 히알루론산", "Hyaluronic Acid", "Sodium Hyaluronate",
        "Hydrolyzed Hyaluronic Acid", "히알루로닉",
    ]),
    ("PDRN (폴리디옥시리보뉴클레오타이드)", [
        "피디알엔", "PNDR", "피브이디알엔", "리쥬란", "소듐디엔에이", "하이드롤라이즈드디엔에이",
        "PDRN", "Polydeoxyribonucleotide", "Sodium DNA", "Hydrolyzed DNA",
        "폴리뉴클레오티드", "피토피드알엔",
    ]),
    ("NMN (니코틴아마이드모노뉴클레오타이드)", [
        "니코틴아마이드모노뉴클레오타이드", "NMN", "Nicotinamide Mononucleotide",
    ]),
    ("레티놀", [
        "레틴알", "비타티놀", "Retinol", "Retinal", "Retinaldehyde",
    ]),
    ("트라넥사믹애씨드", [
        "트라넥삼산", "히트라넥사믹애씨드", "Tranexamic Acid",
    ]),
    ("글루타치온", [
        "글루타치온C", "Glutathione",
    ]),
    ("비타민C (아스코르빅애씨드 계열)", [
        "아스코빌글루코사이드", "소듐아스코빌포스페이트",
        "비타민C", "비타민 C", "Vitamin C", "Ascorbic Acid",
        "Ascorbyl Glucoside", "Sodium Ascorbyl Phosphate",
    ]),
    ("티아미돌", [
        "Thiamidol",
    ]),
    ("마데카소사이드", [
        "Madecassoside",
    ]),
    ("아시아티코사이드", [
        "Asiaticoside",
    ]),
    ("마데카식애씨드", [
        "Madecassic Acid",
    ]),
    ("병풀추출물 (센텔라아시아티카)", [
        "센텔라아시아티카", "시카", "병풀잎수", "병풀잎추출물", "병풀추출물",
        "Centella Asiatica", "Centella", "Cica", "Tiger Grass Extract",
    ]),
    ("세라마이드", [
        "세라마이드엔피", "5종 세라마이드", "Ceramide", "Ceramide NP",
        "Ceramide AP", "Ceramide EOP",
    ]),
    ("판테놀 (비타민B5)", [
        "판테놀", "판토텐산", "Panthenol", "Vitamin B5", "Pantothenic Acid",
        "Dexpanthenol",
    ]),
    ("아데노신", [
        "Adenosine",
    ]),
    ("EGF (상피세포성장인자)", [
        "EGF", "에피디알지에프", "상피세포성장인자",
        "Epidermal Growth Factor", "sh-Oligopeptide-1",
    ]),
    ("카퍼트라이펩타이드-1", [
        "카퍼트라이펩타이드", "Copper Tripeptide-1", "Copper Peptide",
        "Copper Tripeptide",
    ]),
    ("아세틸헥사펩타이드-1", [
        "아세틸헥사펩타이드", "Acetyl Hexapeptide-1", "Acetyl Hexapeptide",
    ]),
    ("팔미토일트라이펩타이드-5", [
        "팔미토일트라이펩타이드", "Palmitoyl Tripeptide-5", "Palmitoyl Tripeptide",
    ]),
    ("아세틸다이펩타이드-1세틸에스터", [
        "Acetyl Dipeptide-1 Cetyl Ester",
    ]),
    ("펩타이드", [
        "블루 펩타이드", "리프팅 펩타이드", "13-펩타이드", "실크펩타이드",
        "Peptide", "Oligopeptide", "Polypeptide", "Silk Peptide",
    ]),
    ("바쿠치올", [
        "Bakuchiol",
    ]),
    ("스피큘 (하이드롤라이즈드해면)", [
        "스피큘", "하이드롤라이즈드해면", "해면", "Spicule", "Hydrolyzed Sponge",
        "Spongilla",
    ]),
    ("아텔로콜라겐", [
        "콜라겐", "하이드롤라이즈드콜라겐", "Collagen", "Hydrolyzed Collagen",
        "Atelocollagen",
    ]),
    ("폴리락틱애씨드 (PLA)", [
        "폴리락틱애씨드", "PHA 폴리락틱애씨드", "PLA", "Polylactic Acid",
    ]),
    ("AHA (알파하이드록시애씨드)", [
        "AHA", "Alpha Hydroxy Acid", "Glycolic Acid", "Lactic Acid",
        "Mandelic Acid",
    ]),
    ("BHA (살리실릭애씨드)", [
        "BHA", "살리실릭애씨드", "Salicylic Acid", "Beta Hydroxy Acid",
    ]),
    ("PHA (폴리하이드록시애씨드)", [
        "PHA", "Polyhydroxy Acid", "Gluconolactone", "Lactobionic Acid",
    ]),
    ("징크피씨에이", [
        "징크피씨에이", "징크 PCA", "징크", "Zinc PCA",
        "Zinc Pyrrolidone Carboxylic Acid",
    ]),
    ("비피다발효용해물", [
        "갈락토미세스", "락토바실러스발효용해물", "비피다",
        "Bifida Ferment Lysate", "Galactomyces", "Lactobacillus Ferment Lysate",
    ]),
    ("스쿠알란", [
        "Squalane", "Squalene",
    ]),
    ("티트리잎오일 (추출물)", [
        "티트리잎오일", "티트리추출물", "티트리",
        "Tea Tree Oil", "Tea Tree Leaf Oil", "Melaleuca Alternifolia",
    ]),
    ("감초뿌리추출물", [
        "감초 뿌리 추출물", "창과감초뿌리추출물", "감초뿌리추출물",
        "Licorice Root Extract", "Glycyrrhiza Uralensis Root Extract",
    ]),
    ("프로폴리스추출물", [
        "프로폴리스추출물", "Propolis Extract",
    ]),
    ("쑥잎수", [
        "어성초추출물", "Artemisia Leaf Water", "Mugwort",
        "Houttuynia Cordata Extract",
    ]),
    ("녹차추출물 (카멜리아시넨시스)", [
        "녹차추출물", "그린티", "그린티엔자임",
        "Green Tea Extract", "Camellia Sinensis Extract", "Green Tea",
    ]),
    ("베타글루칸", [
        "베타 글루칸", "Beta-Glucan", "Beta Glucan",
    ]),
    ("카르노신", [
        "Carnosine",
    ]),
    ("만노오스", [
        "Mannose",
    ]),
    ("장미꽃수 (로사다마세나)", [
        "프로방스장미꽃수", "장미꽃추출물",
        "Rose Flower Water", "Rosa Damascena Flower Water", "Rose Extract",
    ]),
    ("위치하젤 (버지니아풍년화수)", [
        "위치하젤", "버지니아풍년화수",
        "Witch Hazel", "Hamamelis Virginiana Water",
    ]),
    ("실크수", [
        "Silk Water", "Hydrolyzed Silk",
    ]),
    ("참마뿌리추출물", [
        "Dioscorea Japonica Root Extract", "Yam Root Extract",
    ]),
    ("인삼캘러스배양추출물", [
        "에스케이-인삼캘러스배양추출물",
        "Ginseng Callus Culture Extract", "Panax Ginseng Callus Culture Extract",
    ]),
    ("마카다미아씨오일", [
        "Macadamia Seed Oil", "Macadamia Ternifolia Seed Oil",
    ]),
    ("알로에베라잎추출물", [
        "알로에베라잎추출물", "알로에",
        "Aloe Vera", "Aloe Barbadensis Leaf Extract", "Aloe Extract",
    ]),
    ("카프릴릭/카프릭트라이글리세라이드", [
        "Caprylic/Capric Triglyceride", "MCT Oil",
    ]),
    ("마누카잎추출물", [
        "Manuka Leaf Extract", "Leptospermum Scoparium Leaf Extract",
    ]),
    ("효모추출물", [
        "효모추출물", "Yeast Extract", "Saccharomyces Ferment",
    ]),
    ("안티세범 P", [
        "안티세범P", "Antisebum P",
    ]),
    ("리들샷 성분군", [
        "리들샷", "피디알엔 리들샷", "Riddleshot",
    ]),
    ("비타민나무열매추출물", [
        "비타민나무추출물",
        "Sea Buckthorn Extract", "Hippophae Rhamnoides Fruit Extract",
    ]),
    ("엑소좀", [
        "세포외소포", "케리포리아 라케라타세포외소포", "청귤엑소좀", "식물엑소좀",
        "Exosome", "Extracellular Vesicle", "Plant Exosome",
    ]),
]


# ─── 룩업 테이블 빌드 ─────────────────────────────────────────

def _norm(text: str) -> str:
    """비교용 정규화: 공백·괄호·슬래시·하이픈 제거, 소문자 변환"""
    return re.sub(r'[\s·\-/()\[\]（）]', '', str(text)).lower()


# normalized_alias → 표준명 (동일 alias 충돌 시 먼저 나오는 항목 우선)
_LOOKUP: dict[str, str] = {}
for _standard, _aliases in _INGREDIENT_DICT:
    if _norm(_standard) not in _LOOKUP:
        _LOOKUP[_norm(_standard)] = _standard
    for _alias in _aliases:
        _key = _norm(_alias)
        if _key not in _LOOKUP:
            _LOOKUP[_key] = _standard

# 부분 매칭용: 길이 내림차순 정렬 (긴 alias 우선)
_PARTIAL_LIST: list[tuple[str, str]] = sorted(
    _LOOKUP.items(), key=lambda x: len(x[0]), reverse=True
)


# ─── 매칭 함수 ────────────────────────────────────────────────

def match_ingredient(ingredient: str) -> str:
    """
    성분 하나를 표준명으로 변환합니다.
    매칭 실패 시 빈 문자열을 반환합니다.
    """
    norm = _norm(ingredient)
    if not norm:
        return ""

    # 1순위: 정확 일치
    if norm in _LOOKUP:
        return _LOOKUP[norm]

    # 2순위: 부분 포함 (최소 길이 3 이상 alias만 사용)
    for key, standard in _PARTIAL_LIST:
        if len(key) < 3:
            continue
        if key in norm or norm in key:
            return standard

    return ""


def standardize_row(main_ingredients) -> str:
    """
    쉼표 구분된 main_ingredients 값을 받아 표준명 목록을 반환합니다.
    중복 표준명은 제거합니다.
    """
    if pd.isna(main_ingredients) or not str(main_ingredients).strip():
        return ""

    parts = [p.strip() for p in str(main_ingredients).split(",") if p.strip()]
    seen: set[str] = set()
    result: list[str] = []

    for part in parts:
        matched = match_ingredient(part)
        if matched and matched not in seen:
            seen.add(matched)
            result.append(matched)

    return ", ".join(result)


# ─── CSV 처리 ─────────────────────────────────────────────────

def find_all_info_csvs(data_dir: Path) -> list[Path]:
    return sorted(data_dir.glob("*(info)*.csv"), key=lambda p: p.name)


def resolve_csv_paths(data_dir: Path) -> list[Path]:
    if TARGET_CSV is None:
        return find_all_info_csvs(data_dir)
    if isinstance(TARGET_CSV, list):
        return [Path(p) for p in TARGET_CSV]
    return [Path(TARGET_CSV)]


def process_csv(csv_path: Path) -> None:
    print(f"\n{'=' * 60}")
    print(f"[대상 CSV] {csv_path.name}")

    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    if "main_ingredients" not in df.columns:
        print("[건너뜀] main_ingredients 컬럼이 없습니다.")
        return

    df["standard_ingredients"] = df["main_ingredients"].map(standardize_row)

    total = len(df)
    matched = df["standard_ingredients"].ne("").sum()
    has_main = df["main_ingredients"].notna() & df["main_ingredients"].ne("").astype(bool)
    unmatched_rows = df[has_main & df["standard_ingredients"].eq("")]

    print(f"[처리 완료] 전체 {total}행 | 표준명 매칭 {matched}행")

    if not unmatched_rows.empty:
        unmatched_vals = (
            unmatched_rows["main_ingredients"]
            .dropna()
            .unique()
            .tolist()
        )
        print(f"[미매칭 {len(unmatched_vals)}종] {unmatched_vals[:10]}")

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"[저장 완료] {csv_path.name}")


def main() -> None:
    data_dir = Path(__file__).parent / "Data"
    csv_paths = resolve_csv_paths(data_dir)

    if not csv_paths:
        print("[오류] info CSV 파일을 찾을 수 없습니다.")
        return

    for csv_path in csv_paths:
        if not csv_path.exists():
            print(f"[건너뜀] 파일 없음: {csv_path}")
            continue
        process_csv(csv_path)


if __name__ == "__main__":
    main()
