const dashboardMeta = {
  dataRange: "2025.04.30 ~ 2025.05.05",
  lastUpdated: "2025.05.05 23:59",
  comparisonLabel: "전주 대비",
};

const page1Summary = {
  analyzedProducts: 3842,
  analyzedIngredients: 126,
  totalSearchGrowthRate: 18.4,
  risingIngredientCount: 12,
  supplyShortageIngredientCount: 7,
};

window.DASHBOARD_DATA = {
  meta: dashboardMeta,
  page1Summary,
  page1: {
    functionRisers: [
      { label: "탄력/주름 개선", growth: 31.2, searchIndex: 96 },
      { label: "피부결 개선", growth: 26.8, searchIndex: 89 },
      { label: "장벽 강화", growth: 22.4, searchIndex: 83 },
      { label: "진정/붉은기 완화", growth: 19.7, searchIndex: 78 },
      { label: "광채/톤 개선", growth: 15.9, searchIndex: 72 },
    ],
    ingredientPopularity: [
      { label: "나이아신아마이드", growth: 17.6, searchIndex: 100 },
      { label: "히알루론산", growth: 12.4, searchIndex: 89 },
      { label: "병풀/시카", growth: 9.8, searchIndex: 83 },
      { label: "PDRN", growth: 21.1, searchIndex: 78 },
      { label: "레티놀", growth: 24.8, searchIndex: 72 },
    ],
    priceDistribution: [
      { ingredient: "레티놀", prices: [19800, 22900, 27800, 31900, 34900, 39800, 45900, 52000, 61000] },
      { ingredient: "PDRN", prices: [24900, 29900, 33800, 38900, 43500, 48900, 56000, 64800, 72000] },
      { ingredient: "나이아신아마이드", prices: [12900, 15800, 18900, 22900, 26800, 30900, 34900, 39800] },
      { ingredient: "세라마이드", prices: [16900, 21000, 24800, 29900, 34800, 39200, 45500, 51000] },
      { ingredient: "판테놀", prices: [11900, 14800, 17900, 21900, 24900, 28000, 32900, 36500] },
    ],
    demandSupplyMatrix: [
      { ingredient: "레티놀", demand: 92, supply: 61, growth: 24.8, size: 44, status: "growth" },
      { ingredient: "PDRN", demand: 86, supply: 42, growth: 21.1, size: 38, status: "opportunity" },
      { ingredient: "나이아신아마이드", demand: 78, supply: 73, growth: 17.6, size: 42, status: "growth" },
      { ingredient: "세라마이드", demand: 74, supply: 45, growth: 13.9, size: 35, status: "opportunity" },
      { ingredient: "판테놀", demand: 69, supply: 39, growth: 11.4, size: 30, status: "opportunity" },
      { ingredient: "아데노신", demand: 46, supply: 79, growth: -4.2, size: 26, status: "oversupply" },
      { ingredient: "글루타티온", demand: 41, supply: 37, growth: -6.8, size: 22, status: "stable" },
      { ingredient: "트라넥사믹애씨드", demand: 39, supply: 29, growth: -8.3, size: 20, status: "stable" },
    ],
    insights: [
      "레티놀은 탄력/주름 개선 기능 검색과 함께 동반 상승해 5월 첫째 주 핵심 성장 성분으로 분류됩니다.",
      "PDRN과 세라마이드는 수요 대비 공급 노출이 낮아 신제품 테스트와 콘텐츠 선점 여지가 큽니다.",
      "아데노신은 제품 노출은 높지만 검색 관심이 약해 전주 대비 프로모션 효율 점검이 필요합니다.",
    ],
  },
  page2: {
    periodLabel: "2025.04.30 ~ 2025.05.05",
    selectedIngredient: "나이아신아마이드",
    selectedSummary: {
      weeklySearchVolume: 98400,
      growthRate: 17.6,
      peakDate: "2025.05.05",
      leadingConcern: "광채/톤 개선",
    },
    searchTrend: {
      dates: ["2025.04.30", "2025.05.01", "2025.05.02", "2025.05.03", "2025.05.04", "2025.05.05"],
      series: [
        { ingredient: "나이아신아마이드", values: [64, 68, 72, 78, 82, 86], color: "#E6A23C" },
        { ingredient: "히알루론산", values: [58, 61, 66, 70, 73, 77], color: "#8B7CC8" },
        { ingredient: "병풀/시카", values: [52, 56, 59, 63, 67, 71], color: "#5AAA6E" },
        { ingredient: "PDRN", values: [68, 72, 76, 84, 88, 91], color: "#2CA6A4" },
        { ingredient: "레티놀", values: [72, 79, 88, 100, 94, 97], color: "#3B66A6" },
      ],
    },
    marketProducts: [
      // 전처리 완료 데이터 반영 전 임시값입니다. TODO: 전처리 완료 제품 수 데이터 연결 후 교체
      { ingredient_key: "niacinamide", ingredient_label: "나이아신아마이드", product_count: 128, unique_product_count: 118, brand_count: 43, crawl_start: "2025-05-01", crawl_end: "2025-05-07", source: "oliveyoung", is_mock: true },
      { ingredient_key: "hyaluronic_acid", ingredient_label: "히알루론산", product_count: 96, unique_product_count: 89, brand_count: 36, crawl_start: "2025-05-01", crawl_end: "2025-05-07", source: "oliveyoung", is_mock: true },
      { ingredient_key: "centella", ingredient_label: "병풀/시카", product_count: 74, unique_product_count: 69, brand_count: 30, crawl_start: "2025-05-01", crawl_end: "2025-05-07", source: "oliveyoung", is_mock: true },
      { ingredient_key: "retinol", ingredient_label: "레티놀", product_count: 49, unique_product_count: 45, brand_count: 21, crawl_start: "2025-05-01", crawl_end: "2025-05-07", source: "oliveyoung", is_mock: true },
      { ingredient_key: "pdrn", ingredient_label: "PDRN", product_count: 27, unique_product_count: 25, brand_count: 13, crawl_start: "2025-05-01", crawl_end: "2025-05-07", source: "oliveyoung", is_mock: true },
    ],
    concernTable: [
      { age: "20대", wrinkleElasticity: 52, toneSpot: 76, troubleCalming: 84, drynessBarrier: 61 },
      { age: "30대", wrinkleElasticity: 78, toneSpot: 82, troubleCalming: 58, drynessBarrier: 68 },
      { age: "40대", wrinkleElasticity: 100, toneSpot: 74, troubleCalming: 42, drynessBarrier: 63 },
      { age: "50대+", wrinkleElasticity: 88, toneSpot: 56, troubleCalming: 31, drynessBarrier: 72 },
    ],
    ageTopIngredients: [
      { age: "20대", top: ["나이아신아마이드", "판테놀", "레티놀"] },
      { age: "30대", top: ["레티놀", "PDRN", "세라마이드"] },
      { age: "40대", top: ["레티놀", "아데노신", "PDRN"] },
      { age: "50대+", top: ["레티놀", "펩타이드", "세라마이드"] },
    ],
    insights: [
      "나이아신아마이드는 mock 기준 성분 검색 관심도 지수 상위권이며, API 연결 성공 시 DataLab ratio 기반 값으로 교체됩니다.",
      "30~40대의 주름/탄력 집중도가 높아 레티놀·PDRN 중심의 안티에이징 메시지와 궁합이 좋습니다.",
      "PDRN은 임시 제품 수 대비 검색 관심도 변화가 커서 비교 콘텐츠 테스트 후보입니다.",
    ],
  },
  page3: {
    ingredient: "레티놀",
    functionChips: ["탄력/주름 개선", "피부결 개선", "안티에이징"],
    sentiment: { positive: 72, neutral: 18, negative: 10 },
    keywords: [
      { label: "탄력", score: 92, tone: "positive" },
      { label: "피부결", score: 88, tone: "positive" },
      { label: "자극", score: 64, tone: "negative" },
      { label: "건조함", score: 57, tone: "negative" },
      { label: "흡수력", score: 52, tone: "positive" },
      { label: "초보자", score: 48, tone: "neutral" },
    ],
    positiveKeywords: [
      { label: "촉촉해요", score: 24.1 },
      { label: "흡수 잘돼요", score: 18.7 },
      { label: "피부결 개선", score: 15.2 },
      { label: "탄력 느껴져요", score: 13.6 },
      { label: "자극 없어요", score: 12.4 },
    ],
    negativeKeywords: [
      { label: "비싸요", score: 28.3 },
      { label: "자극 있어요", score: 22.1 },
      { label: "효과 없어요", score: 16.5 },
      { label: "끈적거려요", score: 14.2 },
      { label: "트러블 올라와요", score: 11.7 },
    ],
    brandProducts: [
      { rank: 1, brand: "아이오페", product: "레티놀 슈퍼 바운스 세럼", reviewCount: 12842, rating: 4.8, sentiment: 78, issue: "자극 완화 메시지 강점" },
      { rank: 2, brand: "이니스프리", product: "레티놀 시카 흔적 앰플", reviewCount: 9615, rating: 4.7, sentiment: 74, issue: "탄력 체감 리뷰 다수" },
      { rank: 3, brand: "라운드랩", product: "레티놀 탄력 세럼", reviewCount: 6208, rating: 4.6, sentiment: 69, issue: "입문자 사용법 문의 증가" },
    ],
    skinTypeSentiment: [
      { type: "건성", positive: 68, neutral: 19, negative: 13, issue: "초기 건조감, 보습 레이어링 필요" },
      { type: "복합성", positive: 76, neutral: 16, negative: 8, issue: "피부결 개선 체감이 빠름" },
      { type: "지성", positive: 73, neutral: 18, negative: 9, issue: "끈적임 적은 제형 선호" },
      { type: "민감성", positive: 61, neutral: 23, negative: 16, issue: "저농도/격일 사용 가이드 필요" },
    ],
    opportunities: [
      "건성 타겟에는 레티놀 단독보다 세라마이드/판테놀 보습 조합을 함께 제안하는 메시지가 유리합니다.",
      "민감성 리뷰에서 자극 우려가 반복되므로 입문 루틴, 낮은 농도, 사용 주기 안내가 전환 장벽을 낮춥니다.",
      "탄력 체감 키워드가 긍정 리뷰의 중심이므로 전후 비교형 상세 콘텐츠를 우선 테스트할 만합니다.",
    ],
  },
  page4: {
    summary: {
      spikeCount: 2,
      oversupplyCount: 1,
      negativeReviewCount: 2,
    },
    alerts: [
      {
        id: "retinol-spike",
        type: "급등",
        title: "레티놀 검색량 급등",
        description: "탄력/주름 개선 검색과 함께 레티놀 관심도가 전주 대비 빠르게 상승했습니다.",
        time: "2025.05.05 21:40",
        metric: "+31.2%",
        severity: "높음",
        reasons: [
          "레티놀 검색 지수가 주간 후반 3일 연속 상승했습니다.",
          "탄력/주름 개선 기능 검색량이 동반 증가했습니다.",
          "30~40대 검색 비중이 전주 대비 확대되었습니다.",
        ],
        actions: [
          "레티놀 관련 검색 광고와 상세페이지 노출을 우선 점검하세요.",
          "건성/민감성 타겟에는 저자극 사용 가이드를 함께 노출하세요.",
          "주간 캠페인 카피에 탄력/주름 개선 메시지를 반영하세요.",
        ],
        metrics: {
          "검색량": "+31.2%",
          "관심 성분 순위": "1위",
          "주요 타깃": "30~40대",
        },
      },
      {
        id: "pdrn-rebound",
        type: "급등",
        title: "PDRN 관심도 재상승",
        description: "앰플 카테고리에서 PDRN 검색 지수가 2025.05.04 이후 다시 상승했습니다.",
        time: "2025.05.04 18:20",
        metric: "+21.1%",
        severity: "중간",
        reasons: [
          "PDRN 검색 지수가 주간 평균 대비 높은 수준으로 회복했습니다.",
          "회복/광채 관련 키워드와 함께 언급량이 증가했습니다.",
        ],
        actions: [
          "레티놀 대비 회복/광채 포지션의 비교 콘텐츠를 테스트하세요.",
          "공급 노출이 낮은 SKU의 리뷰와 가격 경쟁력을 점검하세요.",
        ],
        metrics: {
          "검색량": "+21.1%",
          "수요지수": "86",
          "공급지수": "42",
        },
      },
      {
        id: "adenosine-oversupply",
        type: "공급 과열",
        title: "아데노신 노출 과다",
        description: "검색 수요 대비 제품 노출이 높아 신규 발주보다 차별화 메시지 점검이 필요합니다.",
        time: "2025.05.03 11:10",
        metric: "공급 79",
        severity: "중간",
        reasons: [
          "공급지수 79로 카테고리 평균보다 높게 노출되고 있습니다.",
          "검색 수요지수는 46에 머물러 수요-공급 간 간극이 있습니다.",
        ],
        actions: [
          "신규 발주 확대보다 기존 SKU의 차별화 메시지를 우선 점검하세요.",
          "프로모션 효율과 리뷰 키워드 반응을 함께 확인하세요.",
        ],
        metrics: {
          "공급지수": "79",
          "수요지수": "46",
          "전주 대비": "-4.2%",
        },
      },
      {
        id: "retinol-dry-review",
        type: "부정 리뷰 증가",
        title: "레티놀 건성 리뷰 건조감 증가",
        description: "건성 피부 리뷰에서 건조감과 따가움 키워드가 증가했습니다.",
        time: "2025.05.02 15:35",
        metric: "+9.4%p",
        severity: "높음",
        reasons: [
          "건성 리뷰에서 건조감 언급 비율이 가장 높게 나타났습니다.",
          "자극/따가움 키워드가 부정 리뷰의 주요 원인으로 반복됩니다.",
          "초기 사용법 안내 니즈가 함께 증가했습니다.",
        ],
        actions: [
          "상세페이지 상단에 보습 레이어링과 사용 주기 안내를 추가하세요.",
          "세라마이드/판테놀 결합 메시지를 배너 카피에 반영하세요.",
          "저자극 샘플링 또는 입문 루틴 콘텐츠를 테스트하세요.",
        ],
        metrics: {
          "부정비율": "+9.4%p",
          "주요 피부타입": "건성",
          "주요 키워드": "건조감",
        },
      },
      {
        id: "sensitive-irritation",
        type: "부정 리뷰 증가",
        title: "민감성 자극 언급 증가",
        description: "민감성 리뷰에서 레티놀 사용 주기와 농도 안내 니즈가 감지되었습니다.",
        time: "2025.04.30 09:10",
        metric: "+6.1%p",
        severity: "중간",
        reasons: [
          "민감성 리뷰에서 자극 우려가 전주 대비 증가했습니다.",
          "저농도/격일 사용 가이드 관련 문의가 늘었습니다.",
        ],
        actions: [
          "초보자용 사용 루틴을 FAQ와 상세페이지에 추가하세요.",
          "고농도 표현보다 저자극/완충 성분 메시지를 우선 노출하세요.",
        ],
        metrics: {
          "부정비율": "+6.1%p",
          "관련 키워드": "자극",
          "권장 대응": "사용법 안내",
        },
      },
    ],
  },
  page5: {
    promptPlaceholder: "예: 건성 타겟을 위한 레티놀 마케팅 전략 제안해줘",
    suggestions: [
      "이번 주 진입 검토 성분 추천해줘",
      "건성 타겟 레티놀 전략 알려줘",
      "공급 과열 성분 알려줘",
      "부정 리뷰 많은 성분 개선 방향 알려줘",
      "20대 타겟 미백 성분 전략 제안해줘",
    ],
    insights: [
      {
        id: "dry-retinol",
        title: "건성 타겟 레티놀 번들 전략",
        level: "높음",
        summary: "검색 수요는 상승 중이지만 건성 리뷰에서 건조감 이슈가 함께 증가했습니다.",
        evidence: "2025.04.30 ~ 2025.05.05 기준 레티놀 검색량은 전주 대비 +24.8%, 건성 리뷰의 건조감 이슈는 +9.4%p 증가했습니다.",
        strategy: "레티놀 + 세라마이드/판테놀 보습 조합을 묶고, 첫 2주 사용 루틴을 상세페이지 상단에 배치하세요.",
      },
      {
        id: "pdrn-content",
        title: "PDRN 비교 콘텐츠 테스트",
        level: "중간",
        summary: "PDRN은 수요 대비 공급 노출이 낮아 콘텐츠 선점 여지가 있습니다.",
        evidence: "동기간 PDRN은 수요 지수 86, 공급 지수 42로 수요 대비 노출이 낮은 구간에 있습니다.",
        strategy: "레티놀 대비 회복/광채 포지션을 강조한 숏폼 A/B 테스트를 7일 단위로 운영하세요.",
      },
      {
        id: "adenosine-check",
        title: "아데노신 프로모션 효율 점검",
        level: "중간",
        summary: "공급 노출은 높지만 검색 수요가 약해 발주 확대 전 검토가 필요합니다.",
        evidence: "2025.04.30 ~ 2025.05.05 기준 공급 지수는 높지만 검색 수요 지수는 46에 머물렀습니다.",
        strategy: "신규 발주 확대보다 기존 SKU의 가격/증정 혜택 반응과 리뷰 키워드를 먼저 확인하세요.",
      },
    ],
    targetStrategy: {
      title: "레티놀 × 건성 타겟 전략",
      issues: ["건조감", "자극", "따가움"],
      directions: ["세라마이드/판테놀 결합", "저자극 메시지", "샘플링 유도"],
      actions: ["상세페이지 문구 개선", "리뷰 키워드 반영", "배너 카피 제안"],
    },
  },
};

window.dashboardMeta = dashboardMeta;
window.page1Summary = page1Summary;
