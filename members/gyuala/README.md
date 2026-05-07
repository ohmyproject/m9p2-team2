# Cosmetic Ingredient Signal Dashboard

이 프로젝트는 올리브영, 다이소몰, 네이버쇼핑 같은 리테일 채널의 제품 데이터를 `시장 노출도`로 해석하고, 네이버 DataLab 검색량을 `소비자 관심도 / 수요 신호`로 해석해서 성분별 변화를 자동 선발하는 대시보드입니다.

## 핵심 해석 원칙

- `제품수`는 실제 공급량이 아닙니다.
  주요 리테일 채널에서 얼마나 많이 노출되고 있는지를 보는 `시장 노출도`입니다.
- `검색량`은 실제 판매량이 아닙니다.
  소비자 관심도와 수요 신호를 보는 `Demand Signal`입니다.
- 모든 성분을 한 번에 그리지 않습니다.
  변화가 유의미한 성분만 자동 선발해서 메인 화면을 구성합니다.

## 왜 모든 성분을 보여주지 않는가

성분을 전부 시계열로 올리면 차트가 복잡해지고, 실제로 해석이 필요한 성분이 묻힙니다. 그래서 아래 두 방향에서 상위 후보군만 먼저 추립니다.

1. `제품수 변화 Top N`
2. `검색량 변화 Top N`

이 두 리스트를 합친 뒤 canonical ingredient 기준으로 중복 제거해서 `candidate_pool`을 만들고, 여기서만 상태 분류를 수행합니다.

## 왜 제품수 변화 Top N과 검색량 변화 Top N을 합치는가

검색량만 보면 아직 제품화가 안 된 성분을 놓칠 수 있고, 제품수만 보면 소비자 관심이 따라오지 않는 과잉 노출 성분을 놓칠 수 있습니다. 두 방향을 같이 봐야 다음 네 가지 상태를 더 잘 구분할 수 있습니다.

- `성장 성분`
- `기회 성분`
- `공급 과잉 주의 성분`
- `쇠퇴 성분`

추가로 초기 단계 신호는 `신상품 Watchlist`로 따로 봅니다.

## canonical ingredient 기준

내부 계산, 랭킹, 상태 분류는 모두 `canonical_id` 기준으로 수행합니다. 표기 variant는 검색어 생성과 표시용으로만 사용합니다.

예:

- `PDRN` -> `pdrn`
- `pdrn` -> `pdrn`
- `피디알엔` -> `pdrn`
- `비타민C` -> `vitamin_c`
- `비타C` -> `vitamin_c`
- `살리실산` -> `bha`

이 규칙이 없으면 같은 성분의 시그널이 여러 표기로 쪼개져서 실제 변화가 흐려집니다.

## 검색어 생성 원칙

네이버 DataLab 키워드는 bare ingredient를 금지합니다. 즉 아래 같은 단독 키워드는 쓰지 않습니다.

- `PDRN`
- `비타민C`
- `레티놀`

대신 각 stem에 대해 아래 템플릿만 사용합니다.

1. `{stem} 세럼`
2. `{stem} 앰플`
3. `{stem} 에센스`
4. `{stem} 세럼 추천`
5. `{stem} 앰플 추천`
6. `{stem} {func1}`
7. `{stem} {func2}`

예를 들어 `PDRN`은 다음처럼 생성됩니다.

- `PDRN 세럼`
- `PDRN 앰플`
- `PDRN 에센스`
- `PDRN 세럼 추천`
- `PDRN 앰플 추천`
- `PDRN 탄력`
- `PDRN 재생`
- `피디알엔 세럼`
- `피디알엔 앰플`
- `피디알엔 에센스`

optional stem은 DataLab 20개 제한에서 항상 후순위입니다.

## anchor-normalized relative index란 무엇인가

네이버 DataLab은 요청 배치 기준 상대지수라서 배치가 달라지면 raw ratio 비교가 불안정할 수 있습니다. 현재 주요 성분 5개처럼 한 요청에 모두 들어가는 경우에는 같은 batch의 raw ratio를 사용하고, 후보가 5개를 넘어 batch가 나뉘면 anchor group을 같이 넣어 보정합니다.

- `세럼 추천`
- `앰플 추천`
- `에센스 추천`

그리고 아래처럼 정규화합니다.

`normalized_index = ingredient_ratio / max(anchor_ratio, epsilon)`

이 값을 `Demand Signal` 계산의 기본 입력으로 사용합니다.

## 상태 정의

### 성장 성분

검색 관심도와 시장 노출도가 함께 증가하는 성분입니다.

### 기회 성분

검색 관심은 증가하지만 제품 노출은 아직 낮거나 느린 성분입니다.

### 공급 과잉 주의 성분

제품 노출은 많거나 계속 늘지만 검색 관심은 정체 또는 하락하는 성분입니다.

### 쇠퇴 성분

검색 관심과 시장 노출이 함께 약해지는 성분입니다.

### 신상품 Watchlist

검색 관심과 제품 노출은 아직 낮지만 신상품순에서 새롭게 감지되는 초기 성분입니다. 메인 8개에는 넣지 않고 별도 섹션으로만 표시합니다.

## 왜 8개를 억지로 채우지 않는가

이 대시보드는 “무조건 8개를 보여주는 것”보다 “지금 의미 있는 성분만 보여주는 것”이 더 중요합니다. 그래서 각 카테고리는 최대 개수만 두고, 조건이 약하면 비워둡니다.

예:

- `뚜렷한 성장 성분 없음`
- `뚜렷한 기회 성분 없음`

## 제품 중복 제거와 listing 유지 원칙

같은 제품이 여러 채널에 동시에 노출될 수 있으므로 제품수 계산은 `canonical_product_id` 기준으로 중복 제거합니다.

- `제품수 계산`: 중복 제거
- `채널 listing / rank / url / 향후 리뷰 데이터`: 중복 유지

즉 제품 마스터와 채널 노출 이력을 분리해서 봅니다.

## 현재 데이터 구조

앱은 아래 스키마에 맞춰 DataFrame을 구성합니다.

1. `products`
2. `product_retailer_listings`
3. `product_ingredients`
4. `ingredient_search_timeseries`
5. `ingredient_supply_timeseries`
6. `ingredient_signals`

현재 저장소에 네이버쇼핑 파일이 없어도 adapter interface는 준비돼 있고, 올리브영/다이소 파일만으로 앱은 동작합니다.

## 현재 HTML 프로토타입 반영 범위

현재 HTML 대시보드는 `index.html`, `assets/app.js`, `assets/dashboard_data.js`, `assets/style.css`, `fastapi_app.py`를 중심으로 동작합니다.

### 1페이지: 성분 시장 스냅샷

- `기능(급상승 순위) TOP 5`는 네이버 DataLab 기반 후보 키워드 묶음 중 전주 대비 증가율이 높은 기능을 표시합니다.
- `성분 인기 순위 TOP 5`는 canonical ingredient 후보군 중 최근 검색 관심도 지수가 높은 성분을 표시합니다.
- 기능 TOP5의 막대는 증가율 기준으로, 성분 인기 TOP5의 막대는 검색 관심도 지수 기준으로 표시합니다.
- API 실패 시 `assets/dashboard_data.js`의 fallback 데이터를 유지합니다.

### 2페이지: 검색 트렌드 분석

2페이지는 아래 4개 영역으로 구성합니다.

1. `성분 검색 관심도 추이`: 네이버 DataLab ratio 기반 주요 성분 시계열
2. `성분별 시장 제품 수 현황`: 전처리 완료 전까지 임시 제품 수 mock 막대그래프
3. `연령대별 피부 고민 집중도`: 네이버 DataLab 키워드 그룹 기반 heatmap
4. `검색 트렌드 인사이트`: 검색 관심도, 제품 수, 피부 고민 맥락을 종합한 요약

히트맵 피부 고민 축은 아래 4개로 사용합니다.

- `주름/탄력`
- `잡티/톤`
- `트러블/진정`
- `건조/장벽`

`성분별 시장 제품 수 현황`은 현재 올리브영 크롤링 데이터 전처리 완료 전이므로 임시값입니다. 전처리 완료 후 `ingredient_key` 기준으로 실제 성분별 제품 수를 연결합니다.

## 상세 성분 검색량 수집 방식

상세 시계열에서 특정 성분을 선택했을 때 검색량 시계열이 메모리에 없더라도 바로 `검색량 데이터 없음`으로 처리하지 않습니다. 아래 순서로 다시 확인합니다.

1. local cache / `ingredient_search_timeseries` 조회
2. 없으면 canonical ingredient 기준으로 keyword group 생성
3. 네이버 DataLab API 호출
4. 결과를 cache에 저장
5. 상세 차트에 다시 반영

상세 탭에서 사용자가 선택한 성분은 threshold와 무관하게 `always_fetch` 대상으로 취급합니다.

검색량 상태는 아래처럼 구분합니다.

- `collected`: 정상 수집됨
- `not_collected`: 아직 수집되지 않아 API 호출 시도 전 상태
- `keyword_generation_failed`: 키워드 그룹 생성 실패
- `api_failed`: API 호출 실패
- `zero_or_low_volume`: API 응답은 있으나 검색량이 전부 0 또는 매우 낮음
- `id_mismatch`: canonical ingredient ID 연결 실패

`zero_or_low_volume`도 cache에 저장합니다. 이렇게 해야 `미수집`과 `검색량이 낮은 성분`을 구분할 수 있습니다.

## 올리브영 스냅샷 비교 규칙

올리브영 스냅샷 파일명은 아래 규칙을 따릅니다.

- `oliveyoung_YYMMDD`
- 예: `oliveyoung_260421`, `oliveyoung_260422`

앱은 인식한 스냅샷을 날짜순으로 정렬한 뒤 가장 최근 2개를 자동 비교합니다.

- `previous = 직전 스냅샷`
- `current = 최신 스냅샷`

예:

- `oliveyoung_260421` -> `2026-04-21`
- `oliveyoung_260422` -> `2026-04-22`

스냅샷이 1개뿐이면 `supply_change_pct`는 `데이터 부족` 상태로 남고, 변화율 대신 현재 노출 수준만 보여줍니다.

추가로 스냅샷 품질 검사를 수행합니다.

- current snapshot row 수 / unique product 수
- product match rate
- ingredient match rate
- rank_type 분포
- retailer 분포

품질이 낮으면 `snapshot_quality_status = bad`로 표시하고, 공급 변화율은 참고값으로만 사용합니다.

## 제품수 변화율 공식

제품수 변화율은 절대 비율이 아니라 아래 공식을 씁니다.

`supply_change_pct = (current_product_count / previous_product_count - 1) * 100`

표시는 이렇게 나갑니다.

- `+12.4%`
- `-3.1%`
- `신규 등장`
- `데이터 없음`

## 신규 등장 / 이탈 제품 계산

각 성분별로 previous/current의 `canonical_product_id` 집합을 비교해서 아래를 계산합니다.

- `added_product_ids = current - previous`
- `removed_product_ids = previous - current`
- `retained_product_ids = current ∩ previous`

그리고 카드와 debug table에 아래 값이 들어갑니다.

- 신규 추가 제품수
- 이탈 제품수
- 유지 제품수
- churn rate
- retention rate

## 인기순 랭킹 가중 점수

단순 제품수만 보지 않고, 인기순 노출 위치도 같이 반영합니다.

- `rank_weight = 1 / log(rank + 1)`
- `ingredient_rank_weighted_score = 해당 성분이 포함된 제품들의 rank_weight 합`

변화율은 아래처럼 계산합니다.

`rank_weighted_change_pct = (current_rank_weighted_score / previous_rank_weighted_score - 1) * 100`

제품수 변화율이 0%여도 인기순 상위 노출이 좋아지면 공급 신호가 개선된 것으로 해석할 수 있습니다.

## 신상품순 데이터 해석

`rank_type = new` 데이터가 있는 경우 신상품 신호를 따로 계산합니다.

- `current_new_product_count`
- `previous_new_product_count`
- `new_product_change_pct`
- `added_new_product_ids`

신상품순은 메인 공급량 판단보다 `Early Watch / 신상품 Watchlist`에 더 강하게 반영합니다. 신상품순에서 보였다는 이유만으로 바로 `Growth`로 올리지 않습니다.

장기 하락 추세인데 최근 검색량만 잠깐 반등한 성분은 `Opportunity` 대신 `Rebound Watch`로 분리합니다.

## 실행 방법

1. `.env`에 네이버 API 키를 설정합니다.

```env
NAVER_CLIENT_ID=...
NAVER_CLIENT_SECRET=...
```

2. 대시보드 데이터 빌드:

```bash
cd "/Users/igyueun/Documents/New project"
source .venv/bin/activate
python build_dashboard_data.py
```

3. FastAPI 대시보드 실행:

```bash
cd "/Users/igyueun/Documents/New project"
source .venv/bin/activate
python fastapi_app.py
```

또는 `package.json`의 script를 사용하는 경우 아래처럼 실행할 수 있습니다.

```bash
npm start
```

브라우저에서 `http://127.0.0.1:3000/`을 열면 됩니다. 정적 파일은 FastAPI가 제공하고, 네이버 DataLab 요청은 서버 환경변수의 API 키를 붙여 처리합니다.

현재 HTML 프로토타입에서 사용하는 주요 endpoint는 다음과 같습니다.

- `POST /api/datalab/search`: 네이버 DataLab Search API 프록시
- `GET /api/datalab/dashboard-signals`: 1페이지 기능/성분 TOP5와 2페이지 피부 고민 heatmap 집계
- `POST /api/datalab/ingredient-trend`: 2페이지 기간별 성분 검색 관심도 시계열 조회

네이버 API 키가 없거나 API 요청이 실패하면 화면은 `assets/dashboard_data.js`의 mock/fallback 데이터를 유지합니다.

4. 테스트 실행:

```bash
cd "/Users/igyueun/Documents/New project"
source .venv/bin/activate
pytest -q
```


## 환경변수 및 Git 관리

`.env`에는 실제 네이버 API 키가 들어가므로 절대 Git에 올리지 않습니다.

```env
NAVER_CLIENT_ID=...
NAVER_CLIENT_SECRET=...
```

Git에 올리는 것을 권장하는 파일:

- `index.html`
- `assets/app.js`
- `assets/dashboard_data.js`
- `assets/style.css`
- `fastapi_app.py`
- `README.md`
- `package.json` (`npm start`로 FastAPI를 실행하는 script를 유지할 경우)

상황에 따라 올리는 파일:

- `.env.example`: 새로 만들었거나 `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET` 안내가 들어 있다면 올립니다.
- `.gitignore`: `.env`, `node_modules/`, `.DS_Store` 규칙을 새로 추가했거나 수정했다면 올립니다.

올리면 안 되는 파일:

- `.env`
- `node_modules/`
- `.DS_Store`
- 임시 preview HTML
- zip 패치 파일
- 로컬 스크린샷

## 주요 모듈

- `config/ingredient_config.yaml`: canonical ingredient 정의, alias, cluster, ambiguity penalty
- `config/dashboard_config.yaml`: Top N, 상태 분류 threshold, score weight, 시각화 메시지/색상
- `ingredient_registry.py`: retailer adapter, canonical ingredient 추출, canonical product matching, DB형 schema 생성
- `keyword_builder.py`: bare keyword 없는 DataLab 검색어 생성
- `naver_datalab_client.py`: anchor 포함 배치 호출, normalized index 계산
- `supply_engine.py`: ingredient_supply_timeseries와 supply feature 계산
- `signal_engine.py`: demand feature 계산과 demand/supply signal merge
- `selector.py`: candidate pool 생성, 상태 분류, 메인 8개/Watchlist 선발
- `build_dashboard_data.py`: 실제 데이터를 HTML 프로토타입용 payload로 변환
- `index.html`: 현재 메인 프로토타입 진입점
- `fastapi_app.py`: 정적 대시보드 서빙, 네이버 DataLab API 프록시, 검색 관심도 집계 endpoint를 담당하는 FastAPI 엔트리포인트
- `assets/app.js`, `assets/style.css`: HTML 대시보드 렌더링 및 스타일
- `visualization.py`: Streamlit/Plotly 공용 시각화 로직
- `app.py`: 기존 Streamlit 엔트리포인트

## 현재 한계

- 현재 저장소에는 채널별 인기순/신상품순 파일이 완전히 분리돼 있지 않아서 일부 `prev/current` 공급 지표는 보수적 proxy를 사용합니다.
- 2페이지 `성분별 시장 제품 수 현황`은 올리브영 크롤링 데이터 전처리 완료 전까지 임시 mock 값을 사용합니다.
- 리뷰 감정분석은 아직 연결되지 않았고, 현재는 `리뷰 데이터 없음` 또는 mock 데이터로 처리합니다.
- 네이버 DataLab은 상대지수 기반이라 query 설계, keyword group 구성, batch 분할, anchor normalization의 영향을 받습니다.
- 네이버 DataLab API 실패, 키 누락, zero/low volume 상황에서는 HTML 프로토타입의 fallback 데이터를 유지합니다.
