from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import requests
import uvicorn
from dotenv import load_dotenv
from fastapi import Body, FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles


BASE_DIR = Path(__file__).resolve().parent
NAVER_DATALAB_URL = "https://openapi.naver.com/v1/datalab/search"

load_dotenv(BASE_DIR / ".env")

app = FastAPI(title="BeautyMD Insight API")
app.mount("/assets", StaticFiles(directory=BASE_DIR / "assets"), name="assets")

ANCHOR_GROUP = {
    "key": "__anchor__",
    "label": "__anchor__",
    "keywords": ["세럼 추천", "앰플 추천", "에센스 추천"],
}

FUNCTION_SIGNAL_GROUPS = [
    {"key": "elasticity_wrinkle", "label": "탄력/주름 개선", "keywords": ["탄력 세럼", "탄력 앰플", "주름 개선 세럼", "주름 개선 앰플", "안티에이징 세럼", "안티에이징 앰플", "레티놀 탄력", "PDRN 탄력", "펩타이드 탄력", "아데노신 주름"]},
    {"key": "texture_pore", "label": "피부결/모공 개선", "keywords": ["피부결 세럼", "피부결 앰플", "결 개선 세럼", "모공 세럼", "모공 앰플", "모공 관리 세럼", "나이아신아마이드 피부결", "레티놀 피부결", "PHA 세럼", "AHA 세럼"]},
    {"key": "barrier", "label": "장벽 강화", "keywords": ["피부장벽 세럼", "피부장벽 앰플", "장벽 강화 세럼", "장벽 강화 앰플", "세라마이드 세럼", "세라마이드 앰플", "판테놀 장벽", "판테놀 앰플", "스쿠알란 세럼", "엑토인 세럼"]},
    {"key": "calming_redness", "label": "진정/붉은기 완화", "keywords": ["진정 세럼", "진정 앰플", "붉은기 진정", "붉은기 세럼", "시카 앰플", "시카 세럼", "병풀 앰플", "병풀 진정", "마데카소사이드 세럼", "어성초 앰플"]},
    {"key": "glow_tone", "label": "광채/톤 개선", "keywords": ["광채 세럼", "광채 앰플", "톤 개선 세럼", "톤업 앰플", "브라이트닝 세럼", "나이아신아마이드 톤", "비타민C 세럼", "글루타티온 세럼", "잡티 세럼", "미백 앰플"]},
    {"key": "moisture_hydration", "label": "보습/수분 충전", "keywords": ["수분 세럼", "수분 앰플", "보습 세럼", "보습 앰플", "히알루론산 세럼", "히알루론산 앰플", "속건조 세럼", "속건조 앰플", "스쿠알란 보습", "판테놀 보습"]},
    {"key": "trouble_acne", "label": "트러블/여드름 케어", "keywords": ["트러블 세럼", "트러블 앰플", "여드름 세럼", "여드름 앰플", "티트리 세럼", "티트리 앰플", "살리실산 세럼", "BHA 세럼", "어성초 세럼", "시카 트러블"]},
    {"key": "spot_pigmentation", "label": "잡티/색소침착 케어", "keywords": ["잡티 세럼", "잡티 앰플", "기미 세럼", "기미 앰플", "색소침착 세럼", "트라넥사믹애씨드 세럼", "비타민C 잡티", "나이아신아마이드 잡티", "글루타티온 잡티", "미백 세럼"]},
    {"key": "recovery_regeneration", "label": "회복/재생 케어", "keywords": ["재생 세럼", "재생 앰플", "피부 회복 세럼", "피부 회복 앰플", "PDRN 세럼", "PDRN 앰플", "피디알엔 앰플", "마데카소사이드 앰플", "시카 재생", "병풀 재생"]},
    {"key": "exfoliation_sebum", "label": "각질/피지 케어", "keywords": ["각질 세럼", "각질 앰플", "피지 세럼", "피지 조절 세럼", "AHA 세럼", "BHA 세럼", "PHA 세럼", "살리실산 세럼", "모공 피지 세럼", "피부결 각질"]},
    {"key": "sensitive_low_irritation", "label": "민감/저자극 케어", "keywords": ["저자극 세럼", "저자극 앰플", "민감성 세럼", "민감성 앰플", "민감 피부 진정", "시카 저자극", "판테놀 진정", "알란토인 세럼", "엑토인 앰플", "장벽 진정 세럼"]},
    {"key": "lifting_firming", "label": "리프팅/탄력 케어", "keywords": ["리프팅 세럼", "리프팅 앰플", "탄력 리프팅 세럼", "처진 피부 탄력", "펩타이드 세럼", "펩타이드 앰플", "콜라겐 세럼", "콜라겐 앰플", "레티놀 리프팅", "PDRN 리프팅"]},
]

INGREDIENT_SIGNAL_GROUPS = [
    {"key": "retinol", "label": "레티놀", "stems": ["레티놀", "Retinol"], "funcs": ["탄력", "주름", "피부결", "안티에이징"]},
    {"key": "retinal", "label": "레티날", "stems": ["레티날", "Retinal"], "funcs": ["탄력", "주름", "안티에이징"]},
    {"key": "pdrn", "label": "PDRN", "stems": ["PDRN", "피디알엔"], "funcs": ["탄력", "재생", "회복", "광채"]},
    {"key": "niacinamide", "label": "나이아신아마이드", "stems": ["나이아신아마이드", "Niacinamide"], "funcs": ["미백", "톤", "잡티", "피부결"]},
    {"key": "hyaluronic_acid", "label": "히알루론산", "stems": ["히알루론산", "히알루로닉", "Hyaluronic Acid"], "funcs": ["수분", "보습", "속건조"]},
    {"key": "centella", "label": "병풀/시카", "stems": ["병풀", "시카", "Cica", "Centella"], "funcs": ["진정", "붉은기", "트러블", "장벽"]},
    {"key": "ceramide", "label": "세라마이드", "stems": ["세라마이드", "Ceramide"], "funcs": ["장벽", "보습", "속건조"]},
    {"key": "panthenol", "label": "판테놀", "stems": ["판테놀", "Panthenol"], "funcs": ["장벽", "보습", "진정"]},
    {"key": "adenosine", "label": "아데노신", "stems": ["아데노신", "Adenosine"], "funcs": ["주름", "탄력", "안티에이징"]},
    {"key": "peptide", "label": "펩타이드", "stems": ["펩타이드", "Peptide"], "funcs": ["탄력", "리프팅", "주름"]},
    {"key": "vitamin_c", "label": "비타민C", "stems": ["비타민C", "비타C", "Vitamin C"], "funcs": ["잡티", "미백", "광채", "톤"]},
    {"key": "glutathione", "label": "글루타티온", "stems": ["글루타티온", "Glutathione"], "funcs": ["미백", "광채", "톤"]},
    {"key": "tranexamic_acid", "label": "트라넥사믹애씨드", "stems": ["트라넥사믹애씨드", "트라넥삼산", "Tranexamic Acid"], "funcs": ["잡티", "기미", "미백"]},
    {"key": "bakuchiol", "label": "바쿠치올", "stems": ["바쿠치올", "Bakuchiol"], "funcs": ["탄력", "주름", "저자극"]},
    {"key": "madecassoside", "label": "마데카소사이드", "stems": ["마데카소사이드", "Madecassoside"], "funcs": ["진정", "장벽", "재생"]},
    {"key": "heartleaf", "label": "어성초", "stems": ["어성초", "Heartleaf"], "funcs": ["진정", "트러블", "피지"]},
    {"key": "tea_tree", "label": "티트리", "stems": ["티트리", "Tea Tree"], "funcs": ["트러블", "피지", "진정"]},
    {"key": "bha", "label": "살리실산/BHA", "stems": ["살리실산", "BHA"], "funcs": ["각질", "피지", "모공", "트러블"]},
    {"key": "aha", "label": "AHA", "stems": ["AHA", "아하"], "funcs": ["각질", "피부결", "모공"]},
    {"key": "pha", "label": "PHA", "stems": ["PHA", "파하"], "funcs": ["각질", "피부결", "저자극"]},
    {"key": "azelaic_acid", "label": "아젤라익애씨드", "stems": ["아젤라익애씨드", "아젤라익산", "Azelaic Acid"], "funcs": ["트러블", "붉은기", "잡티"]},
    {"key": "squalane", "label": "스쿠알란", "stems": ["스쿠알란", "Squalane"], "funcs": ["보습", "장벽", "속건조"]},
    {"key": "allantoin", "label": "알란토인", "stems": ["알란토인", "Allantoin"], "funcs": ["진정", "저자극", "장벽"]},
    {"key": "ectoin", "label": "엑토인", "stems": ["엑토인", "Ectoin"], "funcs": ["장벽", "보습", "진정"]},
    {"key": "collagen", "label": "콜라겐", "stems": ["콜라겐", "Collagen"], "funcs": ["탄력", "보습", "리프팅"]},
    {"key": "propolis", "label": "프로폴리스", "stems": ["프로폴리스", "Propolis"], "funcs": ["보습", "진정", "광채"]},
]

CONCERN_SIGNAL_GROUPS = [
    {"key": "wrinkleElasticity", "label": "주름/탄력", "keywords": ["주름 개선 세럼", "주름 개선 앰플", "탄력 세럼", "탄력 앰플", "안티에이징 세럼", "안티에이징 앰플", "레티놀 탄력", "PDRN 탄력", "펩타이드 탄력", "리프팅 세럼"]},
    {"key": "toneSpot", "label": "잡티/톤", "keywords": ["잡티 세럼", "잡티 앰플", "톤 개선 세럼", "톤업 앰플", "광채 세럼", "광채 앰플", "나이아신아마이드 톤", "비타민C 잡티", "글루타티온 세럼", "미백 세럼"]},
    {"key": "troubleCalming", "label": "트러블/진정", "keywords": ["트러블 세럼", "트러블 앰플", "여드름 세럼", "진정 세럼", "진정 앰플", "시카 앰플", "병풀 진정", "어성초 트러블", "티트리 세럼", "붉은기 진정"]},
    {"key": "drynessBarrier", "label": "건조/장벽", "keywords": ["속건조 세럼", "속건조 앰플", "수분 세럼", "보습 앰플", "피부장벽 세럼", "장벽 강화 앰플", "히알루론산 보습", "세라마이드 장벽", "판테놀 보습", "스쿠알란 보습"]},
]

AGE_GROUPS = [
    # Naver DataLab age codes: 3=19~24, 4=25~29, 5=30~34, 6=35~39, 7=40~44, 8=45~49, 9=50~54, 10=55~59, 11=60+.
    {"label": "20대", "ages": ["3", "4"]},
    {"label": "30대", "ages": ["5", "6"]},
    {"label": "40대", "ages": ["7", "8"]},
    {"label": "50대+", "ages": ["9", "10", "11"]},
]

PERIOD_OPTIONS = {
    "1m": {"day_count": 30, "time_unit": "date"},
    "6m": {"day_count": 180, "time_unit": "week"},
    "1y": {"day_count": 365, "time_unit": "week"},
    "3y": {"day_count": 1095, "time_unit": "month"},
}

INGREDIENT_COLORS = {
    "레티놀": "#3B66A6",
    "PDRN": "#2CA6A4",
    "나이아신아마이드": "#E6A23C",
    "히알루론산": "#8B7CC8",
    "병풀/시카": "#5AAA6E",
}


def date_range(day_count: int) -> tuple[str, str]:
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=day_count)
    return start.isoformat(), end.isoformat()


def average(values: list[float]) -> float:
    nums = [float(value) for value in values if isinstance(value, (int, float))]
    return sum(nums) / len(nums) if nums else 0.0


def calculate_growth(values: list[float]) -> float:
    nums = [float(value) for value in values if isinstance(value, (int, float))]
    if len(nums) < 2:
        return 0.0
    midpoint = max(1, len(nums) // 2)
    previous_avg = average(nums[:midpoint])
    current_avg = average(nums[midpoint:])
    if previous_avg <= 0:
        return 100.0 if current_avg > 0 else 0.0
    return ((current_avg - previous_avg) / previous_avg) * 100


def build_ingredient_keywords(group: dict[str, Any]) -> list[str]:
    templates = ["{stem} 세럼", "{stem} 앰플", "{stem} 에센스", "{stem} 세럼 추천", "{stem} 앰플 추천"]
    keywords: list[str] = []
    for stem in group.get("stems", []):
        keywords.extend(template.replace("{stem}", stem) for template in templates)
        keywords.extend(f"{stem} {func}" for func in group.get("funcs", []))
    return list(dict.fromkeys(keywords))[:20]


def chunk_groups(groups: list[dict[str, Any]], size: int = 4, with_anchor: bool = True) -> list[list[dict[str, Any]]]:
    chunks = []
    for index in range(0, len(groups), size):
        chunk = groups[index : index + size]
        chunks.append([*chunk, ANCHOR_GROUP] if with_anchor else chunk)
    return chunks


def datalab_request(payload: dict[str, Any]) -> dict[str, Any]:
    client_id = os.getenv("NAVER_CLIENT_ID")
    client_secret = os.getenv("NAVER_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("NAVER_CLIENT_ID 또는 NAVER_CLIENT_SECRET 환경변수가 설정되지 않았습니다.")
    response = requests.post(
        NAVER_DATALAB_URL,
        headers={
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret,
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )
    try:
        body = response.json() if response.text else {}
    except ValueError:
        body = {"message": response.text or "네이버 데이터랩 응답을 JSON으로 파싱하지 못했습니다."}
    if not response.ok:
        raise RuntimeError(body.get("errorMessage") or body.get("message") or "네이버 데이터랩 API 요청에 실패했습니다.")
    return body


def to_keyword_payload(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "groupName": group.get("label") or group.get("groupName"),
            "keywords": group.get("keywords", [])[:20],
        }
        for group in groups
    ]


def build_search_payload(groups: list[dict[str, Any]], day_count: int = 14, time_unit: str = "date", ages: list[str] | None = None) -> dict[str, Any]:
    start_date, end_date = date_range(day_count)
    payload: dict[str, Any] = {
        "startDate": start_date,
        "endDate": end_date,
        "timeUnit": time_unit,
        "keywordGroups": to_keyword_payload(groups),
    }
    if ages:
        payload["ages"] = ages
    return payload


def rows_from_datalab_results(results: dict[str, Any], source_groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result_list = results.get("results", [])
    by_title = {item.get("title"): item for item in result_list}
    anchor = by_title.get("__anchor__")
    anchor_by_date = {
        point.get("period"): max(float(point.get("ratio", 0) or 0), 0.0001)
        for point in anchor.get("data", [])
    } if anchor else {}

    rows = []
    for group in source_groups:
        if group.get("key") == "__anchor__":
            continue
        result = by_title.get(group["label"])
        if not result:
            continue
        values = []
        for point in result.get("data", []):
            ratio = float(point.get("ratio", 0) or 0)
            anchor_value = anchor_by_date.get(point.get("period"), 1.0)
            values.append(ratio / anchor_value if anchor else ratio)
        current_index = average(values[len(values) // 2 :])
        rows.append({
            "key": group["key"],
            "label": group["label"],
            "rawIndex": current_index,
            "growth": round(calculate_growth(values), 1),
        })
    max_index = max([row["rawIndex"] for row in rows] or [1.0])
    return [
        {"label": row["label"], "growth": row["growth"], "searchIndex": round((row["rawIndex"] / max_index) * 100)}
        for row in rows
    ]


def build_function_risers() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for chunk in chunk_groups(FUNCTION_SIGNAL_GROUPS, 4, True):
        response = datalab_request(build_search_payload(chunk, day_count=14, time_unit="date"))
        rows.extend(rows_from_datalab_results(response, chunk))
    return sorted(rows, key=lambda row: row.get("growth", 0), reverse=True)[:5]


def build_ingredient_popularity() -> list[dict[str, Any]]:
    groups = [
        {"key": group["key"], "label": group["label"], "keywords": build_ingredient_keywords(group)}
        for group in INGREDIENT_SIGNAL_GROUPS
    ]
    rows: list[dict[str, Any]] = []
    for chunk in chunk_groups(groups, 4, True):
        response = datalab_request(build_search_payload(chunk, day_count=14, time_unit="date"))
        rows.extend(rows_from_datalab_results(response, chunk))
    return sorted(rows, key=lambda row: row.get("searchIndex", 0), reverse=True)[:5]


def build_concern_table() -> list[dict[str, Any]]:
    raw_rows = []
    max_value = 1.0
    for age_group in AGE_GROUPS:
        response = datalab_request(build_search_payload(CONCERN_SIGNAL_GROUPS, day_count=30, time_unit="date", ages=age_group["ages"]))
        by_title = {item.get("title"): item for item in response.get("results", [])}
        row: dict[str, Any] = {"age": age_group["label"]}
        for concern in CONCERN_SIGNAL_GROUPS:
            data = by_title.get(concern["label"], {}).get("data", [])
            value = average([float(point.get("ratio", 0) or 0) for point in data])
            row[concern["key"]] = value
            max_value = max(max_value, value)
        raw_rows.append(row)
    normalized = []
    for row in raw_rows:
        normalized_row = {"age": row["age"]}
        for concern in CONCERN_SIGNAL_GROUPS:
            normalized_row[concern["key"]] = round((float(row.get(concern["key"], 0)) / max_value) * 100)
        normalized.append(normalized_row)
    return normalized


def build_ingredient_trend(period_key: str) -> dict[str, Any]:
    option = PERIOD_OPTIONS.get(period_key, PERIOD_OPTIONS["6m"])
    groups = [
        {"key": group["key"], "label": group["label"], "keywords": build_ingredient_keywords(group)}
        for group in INGREDIENT_SIGNAL_GROUPS
        if group["key"] in {"niacinamide", "hyaluronic_acid", "centella", "pdrn", "retinol"}
    ]
    response = datalab_request(build_search_payload(groups, day_count=option["day_count"], time_unit=option["time_unit"]))
    results = response.get("results", [])
    dates = [point.get("period") for point in results[0].get("data", [])] if results else []
    series = []
    for item in results:
        label = item.get("title")
        series.append({
            "ingredient": label,
            "values": [round(float(point.get("ratio", 0) or 0), 2) for point in item.get("data", [])],
            "color": INGREDIENT_COLORS.get(label, "#6B7280"),
        })
    lead = series[0] if series else {"ingredient": "", "values": []}
    growth = calculate_growth(lead.get("values", [])) if lead else 0.0
    peak_date = ""
    if lead.get("values") and dates:
        peak_index = max(range(len(lead["values"])), key=lambda i: lead["values"][i])
        peak_date = dates[peak_index]
    return {
        "periodLabel": f"{dates[0]} ~ {dates[-1]}" if dates else "",
        "selectedIngredient": lead.get("ingredient", ""),
        "selectedSummary": {"growthRate": round(growth, 1), "peakDate": peak_date},
        "searchTrend": {"dates": dates, "series": series},
    }


@app.get("/")
@app.get("/index.html")
def read_index() -> FileResponse:
    return FileResponse(BASE_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/datalab/search")
def datalab_search(payload: dict[str, Any] = Body(default_factory=dict)) -> JSONResponse:
    try:
        return JSONResponse(content=datalab_request(payload or {}))
    except RuntimeError as error:
        return JSONResponse(status_code=500, content={"status": 500, "message": str(error)})
    except requests.RequestException as error:
        return JSONResponse(status_code=500, content={"status": 500, "message": str(error)})


@app.get("/api/datalab/dashboard-signals")
def datalab_dashboard_signals() -> JSONResponse:
    try:
        function_risers = build_function_risers()
        ingredient_popularity = build_ingredient_popularity()
        concern_table = build_concern_table()
        return JSONResponse(content={
            "page1": {
                "functionRisers": function_risers,
                "ingredientPopularity": ingredient_popularity,
            },
            "page2": {
                "concernTable": concern_table,
                "insights": [
                    "연령대별 피부 고민 집중도는 주름/탄력, 잡티/톤, 트러블/진정, 건조/장벽 키워드 그룹의 DataLab ratio를 정규화한 값입니다.",
                    "검색 관심도와 제품 수를 함께 보면서 기회 성분과 공급 과열 가능성을 비교해 볼 수 있습니다.",
                    "DataLab ratio는 실제 검색 건수가 아닌 상대 검색 관심도 지수이므로 후보군 내 비교 지표로 해석합니다.",
                ],
            },
        })
    except Exception as error:
        return JSONResponse(status_code=500, content={"status": 500, "message": str(error)})


@app.post("/api/datalab/ingredient-trend")
def datalab_ingredient_trend(payload: dict[str, Any] = Body(default_factory=dict)) -> JSONResponse:
    try:
        return JSONResponse(content=build_ingredient_trend(str(payload.get("periodKey") or "6m")))
    except Exception as error:
        return JSONResponse(status_code=500, content={"status": 500, "message": str(error)})


if __name__ == "__main__":
    uvicorn.run(
        "fastapi_app:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "3000")),
        reload=os.getenv("RELOAD", "").lower() in {"1", "true", "yes"},
    )
