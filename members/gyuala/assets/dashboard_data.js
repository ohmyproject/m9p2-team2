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
      { label: "레티놀", growth: 24.8, searchIndex: 100 },
      { label: "PDRN", growth: 21.1, searchIndex: 92 },
      { label: "나이아신아마이드", growth: 17.6, searchIndex: 86 },
      { label: "세라마이드", growth: 13.9, searchIndex: 81 },
      { label: "판테놀", growth: 11.4, searchIndex: 74 },
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
    selectedIngredient: "레티놀",
    selectedSummary: {
      weeklySearchVolume: 118420,
      growthRate: 24.8,
      peakDate: "2025.05.03",
      leadingConcern: "탄력/주름",
    },
    searchTrend: {
      dates: ["2025.04.30", "2025.05.01", "2025.05.02", "2025.05.03", "2025.05.04", "2025.05.05"],
      series: [
        { ingredient: "레티놀", values: [72, 79, 88, 100, 94, 97], color: "#3B66A6" },
        { ingredient: "PDRN", values: [68, 72, 76, 84, 88, 91], color: "#2CA6A4" },
        { ingredient: "세라마이드", values: [54, 59, 62, 65, 69, 72], color: "#E6A23C" },
        { ingredient: "판테놀", values: [48, 51, 55, 58, 60, 63], color: "#8B7CC8" },
      ],
    },
    concernTable: [
      { age: "20대", elasticity: 18200, texture: 21400, barrier: 15600, calming: 14300 },
      { age: "30대", elasticity: 26800, texture: 24200, barrier: 19200, calming: 16600 },
      { age: "40대", elasticity: 31400, texture: 20600, barrier: 17400, calming: 12200 },
      { age: "50대+", elasticity: 22600, texture: 13800, barrier: 11900, calming: 8200 },
    ],
    ageTopIngredients: [
      { age: "20대", top: ["나이아신아마이드", "판테놀", "레티놀"] },
      { age: "30대", top: ["레티놀", "PDRN", "세라마이드"] },
      { age: "40대", top: ["레티놀", "아데노신", "PDRN"] },
      { age: "50대+", top: ["레티놀", "펩타이드", "세라마이드"] },
    ],
    insights: [
      "2025.04.30 ~ 2025.05.05 주간에는 레티놀 검색이 2025.05.03에 최고점을 기록했고, 이후에도 높은 관심도가 유지되었습니다.",
      "30~40대의 탄력/주름 검색량이 전체 상승을 견인해 고기능 앰플 메시지와 궁합이 좋습니다.",
      "PDRN은 레티놀 대비 절대 검색량은 낮지만 상승 속도가 빠르므로 비교 콘텐츠 테스트 후보입니다.",
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
    summary: [
      { label: "급등 성분", value: "2건", tone: "up" },
      { label: "공급 과열", value: "1건", tone: "warn" },
      { label: "부정 리뷰 증가", value: "2건", tone: "down" },
    ],
    alerts: [
      {
        level: "critical",
        type: "급등",
        title: "레티놀 검색량 급등",
        timestamp: "2025.05.05 21:40",
        metric: "+31.2%",
        message: "탄력/주름 개선 검색과 함께 레티놀 관심도가 전주 대비 빠르게 상승했습니다.",
      },
      {
        level: "high",
        type: "급등",
        title: "PDRN 관심도 재상승",
        timestamp: "2025.05.04 18:20",
        metric: "+21.1%",
        message: "앰플 카테고리에서 PDRN 검색 지수가 2025.05.04 이후 다시 상승했습니다.",
      },
      {
        level: "medium",
        type: "공급 과열",
        title: "아데노신 노출 과다",
        timestamp: "2025.05.03 11:10",
        metric: "공급 79",
        message: "검색 수요 대비 제품 노출이 높아 신규 발주보다 차별화 메시지 점검이 필요합니다.",
      },
      {
        level: "high",
        type: "부정 리뷰 증가",
        title: "레티놀 건성 리뷰 건조감 증가",
        timestamp: "2025.05.02 15:35",
        metric: "+9.4%p",
        message: "건성 피부 리뷰에서 건조감과 따가움 키워드가 증가했습니다.",
      },
      {
        level: "medium",
        type: "부정 리뷰 증가",
        title: "민감성 자극 언급 증가",
        timestamp: "2025.04.30 09:10",
        metric: "+6.1%p",
        message: "민감성 리뷰에서 레티놀 사용 주기와 농도 안내 니즈가 감지되었습니다.",
      },
    ],
  },
  page5: {
    promptPlaceholder: "예: 건성 타겟을 위한 레티놀 마케팅 전략 제안해줘",
    recommendations: [
      {
        title: "건성 타겟 레티놀 번들 전략",
        confidence: "높음",
        evidence: "2025.04.30 ~ 2025.05.05 기준 레티놀 검색량은 전주 대비 +24.8%, 건성 리뷰의 건조감 이슈는 +9.4%p 증가했습니다.",
        action: "레티놀 + 세라마이드/판테놀 보습 조합을 한 세트로 묶고, 첫 2주 사용 루틴을 상세페이지 상단에 배치하세요.",
      },
      {
        title: "PDRN 비교 콘텐츠 테스트",
        confidence: "중간",
        evidence: "동기간 PDRN은 수요 지수 86, 공급 지수 42로 수요 대비 노출이 낮은 구간에 있습니다.",
        action: "레티놀 대비 회복/광채 포지션을 강조한 숏폼 A/B 테스트를 7일 단위로 운영하세요.",
      },
      {
        title: "아데노신 프로모션 효율 점검",
        confidence: "중간",
        evidence: "2025.04.30 ~ 2025.05.05 기준 공급 지수는 높지만 검색 수요 지수는 46에 머물렀습니다.",
        action: "신규 발주 확대보다 기존 SKU의 가격/증정 혜택 반응과 리뷰 키워드를 먼저 확인하세요.",
      },
    ],
  },
};

window.dashboardMeta = dashboardMeta;
window.page1Summary = page1Summary;
