(function () {
  const FALLBACK_DATA = {
    meta: {
      dataRange: "2025.04.30 ~ 2025.05.05",
      lastUpdated: "2025.05.05 23:59",
      comparisonLabel: "전주 대비",
    },
    page1Summary: {
      analyzedProducts: 3842,
      analyzedIngredients: 126,
      totalSearchGrowthRate: 18.4,
      risingIngredientCount: 12,
      supplyShortageIngredientCount: 7,
    },
    page1: {
      functionRisers: [],
      ingredientPopularity: [],
      priceDistribution: [],
      demandSupplyMatrix: [],
      insights: [],
    },
    page2: {
      periodLabel: "2025.04.30 ~ 2025.05.05",
      selectedIngredient: "나이아신아마이드",
      selectedSummary: {},
      searchTrend: { dates: [], series: [] },
      // TODO: 전처리 완료 제품 수 데이터 연결 후 아래 mock 값을 실제 집계값으로 교체
      marketProducts: [
        { ingredient_key: "niacinamide", ingredient_label: "나이아신아마이드", product_count: 128, unique_product_count: 118, brand_count: 43, crawl_start: "2025-05-01", crawl_end: "2025-05-07", source: "oliveyoung", is_mock: true },
        { ingredient_key: "hyaluronic_acid", ingredient_label: "히알루론산", product_count: 96, unique_product_count: 89, brand_count: 36, crawl_start: "2025-05-01", crawl_end: "2025-05-07", source: "oliveyoung", is_mock: true },
        { ingredient_key: "centella", ingredient_label: "병풀/시카", product_count: 74, unique_product_count: 69, brand_count: 30, crawl_start: "2025-05-01", crawl_end: "2025-05-07", source: "oliveyoung", is_mock: true },
        { ingredient_key: "retinol", ingredient_label: "레티놀", product_count: 49, unique_product_count: 45, brand_count: 21, crawl_start: "2025-05-01", crawl_end: "2025-05-07", source: "oliveyoung", is_mock: true },
        { ingredient_key: "pdrn", ingredient_label: "PDRN", product_count: 27, unique_product_count: 25, brand_count: 13, crawl_start: "2025-05-01", crawl_end: "2025-05-07", source: "oliveyoung", is_mock: true },
      ],
      concernTable: [],
      ageTopIngredients: [],
      insights: [],
    },
    page3: {
      ingredient: "레티놀",
      functionChips: [],
      sentiment: { positive: 0, neutral: 0, negative: 0 },
      keywords: [],
      positiveKeywords: [],
      negativeKeywords: [],
      brandProducts: [],
      skinTypeSentiment: [],
      opportunities: [],
    },
    page4: { summary: {}, alerts: [] },
    page5: { promptPlaceholder: "", suggestions: [], insights: [], targetStrategy: {} },
  };

  const DATA = window.DASHBOARD_DATA || FALLBACK_DATA;
  const META = DATA.meta;
  const chartRendered = {};
  // TODO: 1페이지 네이버 검색 관심도 + 올리브영 성분별 제품 수를 종합해 유의미한 변화 성분을 산출
  // TODO: 유의미한 변화 성분 / 주요 성분 토글 UI 추가
  const MAIN_INGREDIENTS = [
    { key: "niacinamide", label: "나이아신아마이드" },
    { key: "hyaluronic_acid", label: "히알루론산" },
    { key: "centella", label: "병풀/시카" },
    { key: "pdrn", label: "PDRN" },
    { key: "retinol", label: "레티놀" },
  ];
  const DATALAB_TREND_COLORS = {
    "레티놀": "#3B66A6",
    "PDRN": "#2CA6A4",
    "나이아신아마이드": "#E6A23C",
    "히알루론산": "#8B7CC8",
    "병풀/시카": "#5AAA6E",
  };
  const SEARCH_PERIOD_OPTIONS = [
    { key: "1m", label: "1개월", dayCount: 30, timeUnit: "date" },
    { key: "6m", label: "6개월", dayCount: 180, timeUnit: "week" },
    { key: "1y", label: "1년", dayCount: 365, timeUnit: "week" },
    { key: "3y", label: "3년", dayCount: 1095, timeUnit: "month" },
  ];
  let activeSearchPeriodKey = "6m";
  const STATUS_LABELS = {
    growth: "성장",
    shortage: "공급 부족",
    opportunity: "기회",
    oversupply: "공급 과열",
    stable: "관찰",
  };
  const STATUS_COLORS = {
  growth: "#5AAA6E",      // 성장: 연두
  shortage: "#D96A7A",    // 공급 부족: 로즈핑크
  opportunity: "#3FA7B5", // 기회: 하늘/청록
  oversupply: "#C97A9B",  // 공급 과열: 분홍
  stable: "#7B8493",      // 관찰: 회색
};

  function qs(selector) {
    return document.querySelector(selector);
  }

  function qsa(selector) {
    return Array.from(document.querySelectorAll(selector));
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function formatNumber(value) {
    return Number(value || 0).toLocaleString("ko-KR");
  }

  function formatPct(value) {
    const number = Number(value || 0);
    return `${number > 0 ? "+" : ""}${number.toFixed(1)}%`;
  }

  async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.message || "네이버 데이터랩 API 요청에 실패했습니다.");
    }
    return data;
  }

  function fetchDashboardSignals() {
    return fetchJson("/api/datalab/dashboard-signals");
  }

  function fetchIngredientTrend(periodKey) {
    return fetchJson("/api/datalab/ingredient-trend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ periodKey }),
    });
  }

  function getActivePeriodOption() {
    return SEARCH_PERIOD_OPTIONS.find((item) => item.key === activeSearchPeriodKey) || SEARCH_PERIOD_OPTIONS[1];
  }

  function calculateSeriesGrowth(series, fallback = 0) {
    const values = (series?.values || []).filter((value) => Number.isFinite(Number(value)));
    if (values.length < 2) return fallback;
    const start = Number(values[0]);
    const end = Number(values[values.length - 1]);
    return start ? ((end - start) / start) * 100 : fallback;
  }

  function findSeriesPeakDate(series, dates, fallback = "") {
    let peakIndex = -1;
    let peakValue = Number.NEGATIVE_INFINITY;
    (series?.values || []).forEach((value, index) => {
      const number = Number(value);
      if (!Number.isFinite(number) || number <= peakValue) return;
      peakValue = number;
      peakIndex = index;
    });
    return peakIndex >= 0 ? dates[peakIndex] : fallback;
  }

  function withTrendColors(trend) {
    return {
      dates: trend?.dates || [],
      series: (trend?.series || []).map((item) => ({
        ...item,
        color: item.color || DATALAB_TREND_COLORS[item.ingredient] || "#6B7280",
      })),
    };
  }

  function hasUsefulTrendData(trend) {
    const maxValue = (trend?.series || [])
      .flatMap((item) => item.values || [])
      .map(Number)
      .filter(Number.isFinite)
      .reduce((max, value) => Math.max(max, value), 0);
    return maxValue > 1;
  }

  function applySearchTrendResponse(payload) {
    const trend = withTrendColors(payload?.searchTrend || {});
    if (!trend.dates.length || !trend.series.length) return false;
    if (!hasUsefulTrendData(trend)) return false;
    const leadSeries = trend.series[0];

    DATA.page2.searchTrend = trend;
    DATA.page2.periodLabel = payload.periodLabel || DATA.page2.periodLabel;
    DATA.page2.selectedIngredient = payload.selectedIngredient || leadSeries?.ingredient || DATA.page2.selectedIngredient;
    DATA.page2.selectedSummary = {
      ...DATA.page2.selectedSummary,
      ...(payload.selectedSummary || {}),
      growthRate: Number(payload.selectedSummary?.growthRate ?? calculateSeriesGrowth(leadSeries, DATA.page2.selectedSummary.growthRate)),
      peakDate: payload.selectedSummary?.peakDate || findSeriesPeakDate(leadSeries, trend.dates, DATA.page2.selectedSummary.peakDate),
    };
    return true;
  }

  function applyDashboardSignals(payload) {
    let changed = false;
    if (payload?.page1?.functionRisers?.length) {
      DATA.page1.functionRisers = payload.page1.functionRisers;
      changed = true;
    }
    if (payload?.page1?.ingredientPopularity?.length) {
      DATA.page1.ingredientPopularity = payload.page1.ingredientPopularity;
      changed = true;
    }
    if (payload?.page2?.concernTable?.length) {
      DATA.page2.concernTable = payload.page2.concernTable;
      changed = true;
    }
    if (payload?.page2?.insights?.length) {
      DATA.page2.insights = payload.page2.insights;
      changed = true;
    }
    if (!changed) return false;
    renderMarketPage();
    renderSearchPage();
    resizeVisiblePlots();
    return true;
  }

  function getMarketProducts() {
    const products = DATA.page2.marketProducts?.length
      ? DATA.page2.marketProducts
      : FALLBACK_DATA.page2.marketProducts;
    return (products || [])
      .map((item) => ({
        ...item,
        product_count: Number(item.product_count || 0),
      }))
      .sort((a, b) => b.product_count - a.product_count);
  }

  function getMarketProductByLabel(label) {
    return getMarketProducts().find((item) => item.ingredient_label === label);
  }

  function getMarketReflectionStatus(growthRate, productCount) {
    const isSearchUp = Number(growthRate || 0) >= 5;
    const isProductHigh = Number(productCount || 0) >= 70;
    if (isSearchUp && !isProductHigh) return "기회 성분";
    if (isSearchUp && isProductHigh) return "주류/포화 성분";
    if (!isSearchUp && isProductHigh) return "리스크 성분";
    return "미성숙/관망 성분";
  }

  async function loadDatalabSearchTrend() {
    try {
      const response = await fetchIngredientTrend(activeSearchPeriodKey);
      if (!applySearchTrendResponse(response)) return;

      renderSearchPage();

      if (chartRendered.B || qs("#panel-B")?.classList.contains("active")) {
        renderSearchTrendPlot();
        renderMarketProductPlot();
        chartRendered.B = true;
        resizeVisiblePlots();
      }
    } catch (error) {
      console.warn("네이버 데이터랩 API 연결 실패: mock 검색 트렌드 데이터를 유지합니다.", error);
    }
  }

  async function loadDatalabDashboardSignals() {
    try {
      applyDashboardSignals(await fetchDashboardSignals());
    } catch (error) {
      console.warn("네이버 데이터랩 집계 API 연결 실패: mock 검색 관련 데이터를 유지합니다.", error);
    }
  }

  function renderDataStatus() {
    qsa(".data-status-slot").forEach((target, index) => {
      target.innerHTML = `
      <div class="data-status-card">
        <div class="data-status-copy">
          <div class="data-status-line">
            <span>데이터 기준</span>
            <strong>${escapeHtml(META.dataRange)}</strong>
          </div>
          <div class="data-status-line">
            <span>마지막 업데이트</span>
            <strong>${escapeHtml(META.lastUpdated)}</strong>
          </div>
        </div>
        <button class="btn btn-outline update-data-button" type="button" data-status-index="${index}" aria-label="데이터 업데이트 요청" title="데이터 업데이트 요청">↻</button>
      </div>
    `;
    });
    qsa(".update-data-button").forEach((button) => button.addEventListener("click", () => {
      console.log("데이터 업데이트 요청");
      alert("데이터 업데이트 요청");
    }));
  }

  function renderSummaryStrip() {
    const summary = DATA.page1Summary;
    const items = [
      ["분석 제품 수", `${formatNumber(summary.analyzedProducts)}개`, "▯", ""],
      ["분석 성분 수", `${formatNumber(summary.analyzedIngredients)}개`, "◎", "green"],
      ["전체 검색 관심도 증감률", formatPct(summary.totalSearchGrowthRate), "▴", "positive"],
      ["급상승 성분 수", `${formatNumber(summary.risingIngredientCount)}개`, "⚡", "blue"],
      ["공급 부족 성분 수", `${formatNumber(summary.supplyShortageIngredientCount)}개`, "△", "warning"],
    ];
    qs("#page1SummaryStrip").innerHTML = items.map(([label, value, icon, tone]) => `
      <div class="summary-chip ${tone || ""}">
        <div class="summary-icon">${escapeHtml(icon)}</div>
        <div>
          <span>${escapeHtml(label)}</span>
          <strong>${escapeHtml(value)}</strong>
        </div>
      </div>
    `).join("");
  }

  function getRankBarWidth(item, items, options = {}) {
    if (options.barMetric === "growth") {
      const positiveValues = items
        .map((row) => Math.max(0, Number(row.growth || 0)))
        .filter((value) => Number.isFinite(value));
      const maxGrowth = Math.max(...positiveValues, 1);
      const growth = Math.max(0, Number(item.growth || 0));
      return Math.max(8, Math.min(100, (growth / maxGrowth) * 100));
    }
    return Math.max(8, Math.min(100, Number(item.searchIndex || 0)));
  }

  function renderRankList(targetId, items, valueLabel, options = {}) {
    qs(`#${targetId}`).innerHTML = items.map((item, index) => `
      <div class="rank-item">
        <div class="rank-index">${index + 1}</div>
        <div class="rank-body">
          <div class="rank-title">${escapeHtml(item.label)}</div>
          <div class="rank-bar">
            <span style="width:${getRankBarWidth(item, items, options)}%"></span>
          </div>
        </div>
        <div class="rank-value">
          <strong>${formatPct(item.growth)}</strong>
          <span>${escapeHtml(valueLabel)}</span>
        </div>
      </div>
    `).join("");
  }

  function renderInsightList(targetId, items) {
    qs(`#${targetId}`).innerHTML = items.map((item) => `
      <div class="insight-item">${escapeHtml(item)}</div>
    `).join("");
  }

  function renderMatrixLegend() {
    qs("#marketMatrixLegend").innerHTML = Object.entries(STATUS_LABELS).map(([key, label]) => `
      <div class="legend-pill">
        <span class="legend-dot" style="background:${STATUS_COLORS[key]}"></span>
        <span>${label}</span>
      </div>
    `).join("");
  }

  function renderMarketPage() {
    renderSummaryStrip();
    renderRankList("functionRiserList", DATA.page1.functionRisers, META.comparisonLabel, { barMetric: "growth" });
    renderRankList("ingredientPopularityList", DATA.page1.ingredientPopularity, META.comparisonLabel, { barMetric: "searchIndex" });
    renderMatrixLegend();
    renderInsightList("marketInsights", DATA.page1.insights);
  }

  function renderSearchPage() {
    const page = DATA.page2;
    const activeOption = getActivePeriodOption();
    qs("#searchPeriodLabel").textContent = page.periodLabel;
    const selectedCount = qs("#selectedIngredientCount");
    if (selectedCount) selectedCount.textContent = `${MAIN_INGREDIENTS.length}개 선택됨`;

    const periodTarget = qs("#searchPeriodButtons");
    if (periodTarget) {
      periodTarget.innerHTML = SEARCH_PERIOD_OPTIONS.map((option) => `
        <button class="period-button ${option.key === activeOption.key ? "active" : ""}" type="button" data-period-key="${escapeHtml(option.key)}">
          ${escapeHtml(option.label)}
        </button>
      `).join("");
    }

    const leadSeries = page.searchTrend.series[0];
    const leadIngredient = leadSeries?.ingredient || page.selectedIngredient;
    const leadGrowth = calculateSeriesGrowth(leadSeries, page.selectedSummary.growthRate);
    const leadProduct = getMarketProductByLabel(leadIngredient);
    const marketStatus = getMarketReflectionStatus(leadGrowth, leadProduct?.product_count || 0);

    qs("#searchTrendBadges").innerHTML = [
      `${leadIngredient} 시작일 대비 ${formatPct(leadGrowth)}`,
      `현재 보기 ${activeOption.label}`,
      `제품 수 ${formatNumber(leadProduct?.product_count || 0)}개`,
      marketStatus,
    ].map((label, index) => `
      <span class="trend-badge ${index === 0 ? "primary" : ""}">${escapeHtml(label)}</span>
    `).join("");

    const concernMetrics = [
      ["wrinkleElasticity", "주름/탄력", "elasticity"],
      ["toneSpot", "잡티/톤", "texture"],
      ["troubleCalming", "트러블/진정", "calming"],
      ["drynessBarrier", "건조/장벽", "barrier"],
    ];
    const concernValues = page.concernTable.flatMap((row) => concernMetrics.map(([key, , legacyKey]) => Number(row[key] ?? row[legacyKey] ?? 0)));
    const maxConcernValue = Math.max(...concernValues, 1);
    qs("#concernHeatmap").innerHTML = `
      <div class="heatmap-grid" style="--heatmap-columns:${concernMetrics.length}">
        <div class="heatmap-head">연령대</div>
        ${concernMetrics.map(([, label]) => `<div class="heatmap-head">${escapeHtml(label)}</div>`).join("")}
        ${page.concernTable.map((row) => `
          <div class="heatmap-age">${escapeHtml(row.age)}</div>
          ${concernMetrics.map(([key, , legacyKey]) => {
            const value = Number(row[key] ?? row[legacyKey] ?? 0);
            const intensity = Math.max(0.12, value / maxConcernValue);
            const alpha = 0.1 + (intensity * 0.72);
            return `
              <div class="heatmap-cell" style="background: rgba(9, 95, 233, ${alpha.toFixed(3)})">
              <strong>${formatNumber(value)}</strong>
              </div>
            `;
          }).join("")}
        `).join("")}
      </div>
      <div class="heatmap-legend">
        <span>낮음</span>
        <div></div>
        <span>높음</span>
      </div>
    `;
    renderInsightList("searchInsights", page.insights);
  }

  function renderReviewPage() {
    const page = DATA.page3;
    qs("#reviewIngredient").textContent = page.ingredient;
    qs("#reviewFunctionChips").innerHTML = page.functionChips.map((chip) => `
      <span class="feature-chip">${escapeHtml(chip)}</span>
    `).join("");
    const positiveKeywords = page.positiveKeywords?.length
      ? page.positiveKeywords
      : page.keywords.filter((keyword) => keyword.tone === "positive").map((keyword) => ({ label: keyword.label, score: keyword.score }));
    const negativeKeywords = page.negativeKeywords?.length
      ? page.negativeKeywords
      : page.keywords.filter((keyword) => keyword.tone === "negative").map((keyword) => ({ label: keyword.label, score: keyword.score }));
    qs("#reviewKeywords").innerHTML = [
      ["긍정 키워드 TOP 5", positiveKeywords, "positive"],
      ["부정 키워드 TOP 5", negativeKeywords, "negative"],
    ].map(([title, keywords, tone]) => `
      <div class="keyword-panel ${tone}">
        <div class="keyword-panel-title">${escapeHtml(title)}</div>
        ${keywords.map((keyword) => `
          <div class="keyword-row">
            <span>${escapeHtml(keyword.label)}</span>
            <strong>${Number(keyword.score || 0).toFixed(1)}%</strong>
          </div>
        `).join("")}
      </div>
    `).join("");
    qs("#retinolProducts").innerHTML = page.brandProducts.map((item) => `
      <div class="product-row">
        <div class="product-rank">${formatNumber(item.rank)}</div>
        <div>
          <span>${escapeHtml(item.brand)}</span>
          <strong>${escapeHtml(item.product)}</strong>
          <p>${escapeHtml(item.issue)}</p>
        </div>
        <div class="product-stat">
          <span>리뷰 수</span>
          <strong>${formatNumber(item.reviewCount)}</strong>
        </div>
        <div class="product-stat">
          <span>평점</span>
          <strong>${Number(item.rating || 0).toFixed(1)}</strong>
        </div>
      </div>
    `).join("");
    qs("#skinTypeSentimentTable").innerHTML = `
      <table>
        <thead>
          <tr>
            <th>피부 타입</th>
            <th>긍정</th>
            <th>중립</th>
            <th>부정</th>
            <th>주요 이슈</th>
          </tr>
        </thead>
        <tbody>
          ${page.skinTypeSentiment.map((row) => `
            <tr>
              <td>${escapeHtml(row.type)}</td>
              <td>${row.positive}%</td>
              <td>${row.neutral}%</td>
              <td>${row.negative}%</td>
              <td>${escapeHtml(row.issue)}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    `;
    renderInsightList("reviewOpportunities", page.opportunities);
  }

  function getSeverityClass(severity) {
    if (severity === "높음") return "high";
    if (severity === "낮음") return "low";
    return "medium";
  }

  function renderAlertDetail(alert) {
    const metrics = Object.entries(alert.metrics || {});
    qs("#alertDetailPanel").innerHTML = `
      <div class="alert-detail">
        <div class="detail-title-row">
          <div>
            <span class="detail-type">${escapeHtml(alert.type)}</span>
            <h2>${escapeHtml(alert.title)}</h2>
          </div>
          <span class="severity-badge ${getSeverityClass(alert.severity)}">${escapeHtml(alert.severity)}</span>
        </div>
        <p class="detail-description">${escapeHtml(alert.description)}</p>

        <div class="detail-meta-grid">
          <div>
            <span>감지 시점</span>
            <strong>${escapeHtml(alert.time)}</strong>
          </div>
          <div>
            <span>대표 지표</span>
            <strong>${escapeHtml(alert.metric)}</strong>
          </div>
        </div>

        <div class="detail-section">
          <h3>감지 이유</h3>
          <ul>
            ${(alert.reasons || []).map((reason) => `<li>${escapeHtml(reason)}</li>`).join("")}
          </ul>
        </div>

        <div class="detail-section">
          <h3>관련 지표 요약</h3>
          <div class="detail-metrics">
            ${metrics.map(([label, value]) => `
              <div class="metric-pill">
                <span>${escapeHtml(label)}</span>
                <strong>${escapeHtml(value)}</strong>
              </div>
            `).join("")}
          </div>
        </div>

        <div class="detail-section">
          <h3>권장 액션</h3>
          <ul>
            ${(alert.actions || []).map((action) => `<li>${escapeHtml(action)}</li>`).join("")}
          </ul>
        </div>
      </div>
    `;
  }

  function renderAlertPage() {
    const page = DATA.page4;
    const summary = page.summary || {};
    const summaryItems = [
      { label: "급등 성분", value: `${summary.spikeCount || 0}건`, tone: "up" },
      { label: "공급 과열", value: `${summary.oversupplyCount || 0}건`, tone: "warn" },
      { label: "부정 리뷰 증가", value: `${summary.negativeReviewCount || 0}건`, tone: "down" },
    ];
    qs("#alertSummary").innerHTML = summaryItems.map((item) => `
      <div class="summary-chip ${item.tone}">
        <span>${escapeHtml(item.label)}</span>
        <strong>${escapeHtml(item.value)}</strong>
      </div>
    `).join("");

    const alerts = page.alerts || [];
    qs("#alertList").innerHTML = alerts.map((alert, index) => `
      <article class="alert-item ${getSeverityClass(alert.severity)} ${index === 0 ? "active" : ""}" role="button" tabindex="0" data-alert-id="${escapeHtml(alert.id)}">
        <div class="alert-marker">${escapeHtml(alert.type)}</div>
        <div class="alert-body">
          <div class="alert-title-row">
            <strong>${escapeHtml(alert.title)}</strong>
            <span>${escapeHtml(alert.time)}</span>
          </div>
          <p>${escapeHtml(alert.description)}</p>
        </div>
        <div class="alert-metric">${escapeHtml(alert.metric)}</div>
      </article>
    `).join("");

    if (alerts.length) renderAlertDetail(alerts[0]);
    function selectAlert(item) {
      const selected = alerts.find((alert) => alert.id === item.dataset.alertId);
      if (!selected) return;
      qsa(".alert-item").forEach((node) => node.classList.remove("active"));
      item.classList.add("active");
      renderAlertDetail(selected);
    }
    qsa(".alert-item").forEach((item) => {
      item.addEventListener("click", () => selectAlert(item));
      item.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault();
        selectAlert(item);
      });
    });
  }

  function renderAgentPage() {
    const page = DATA.page5;
    const input = qs("#agentPrompt");
    input.placeholder = page.promptPlaceholder;
    qs("#aiRecommendations").innerHTML = (page.insights || []).map((item) => `
      <article class="recommendation-card">
        <div class="recommendation-top">
          <strong>${escapeHtml(item.title)}</strong>
          <span>${escapeHtml(item.level)}</span>
        </div>
        <p class="recommendation-overview">${escapeHtml(item.summary)}</p>
        <div class="recommendation-details">
          <div class="action-box">
            <span>근거 데이터</span>
            <strong>${escapeHtml(item.evidence)}</strong>
          </div>
          <div class="action-box">
            <span>추천 전략</span>
            <strong>${escapeHtml(item.strategy)}</strong>
          </div>
        </div>
        <button class="btn btn-outline strategy-button" type="button">전략 상세 보기</button>
      </article>
    `).join("");
    qs("#agentSuggestions").innerHTML = (page.suggestions || []).map((suggestion) => `
      <button class="question-chip" type="button">${escapeHtml(suggestion)}</button>
    `).join("");
    qsa(".question-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        input.value = chip.textContent.trim();
        input.focus();
      });
    });
    const strategy = page.targetStrategy || {};
    qs("#targetStrategy").innerHTML = `
      <div class="target-strategy">
        <h2>${escapeHtml(strategy.title || "")}</h2>
        <div class="strategy-block">
          <span>부정 포인트</span>
          <div class="strategy-tags">${(strategy.issues || []).map((item) => `<em>${escapeHtml(item)}</em>`).join("")}</div>
        </div>
        <div class="strategy-block">
          <span>제안 방향</span>
          <ul>${(strategy.directions || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
        </div>
        <div class="strategy-block">
          <span>추천 액션</span>
          <ul>${(strategy.actions || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
        </div>
      </div>
    `;
    qs("#agentRunButton")?.addEventListener("click", () => {
      console.log("AI Agent 전략 제안 요청", input.value);
      alert("AI Agent 전략 제안 요청");
    });
  }

  function drawPlot(id, traces, layout, config = {}) {
    const container = qs(`#${id}`);
    if (!container) return;
    if (!window.Plotly) {
      container.innerHTML = '<div class="empty-state">차트 라이브러리를 불러오면 이 영역에 시각화가 표시됩니다.</div>';
      return;
    }
    Plotly.newPlot(container, traces, {
      paper_bgcolor: "#ffffff",
      plot_bgcolor: "#ffffff",
      font: { family: "'Segoe UI', 'Noto Sans KR', sans-serif", size: 12, color: "#334155" },
      margin: { l: 58, r: 28, t: 20, b: 58 },
      ...layout,
    }, { responsive: true, displayModeBar: false, ...config });
  }

  function renderPriceViolinPlot() {
    const traces = DATA.page1.priceDistribution.map((item, index) => ({
      type: "violin",
      name: item.ingredient,
      y: item.prices,
      box: { visible: true },
      meanline: { visible: true },
      points: false,
      line: { color: ["#2563eb", "#14b8a6", "#f59e0b", "#8b5cf6", "#64748b"][index] },
      fillcolor: ["rgba(37,99,235,.18)", "rgba(20,184,166,.18)", "rgba(245,158,11,.2)", "rgba(139,92,246,.16)", "rgba(100,116,139,.16)"][index],
      hovertemplate: "%{x}<br>가격 %{y:,}원<extra></extra>",
    }));
    drawPlot("priceViolinPlot", traces, {
      yaxis: { title: "판매가(원)", gridcolor: "#eef2f7", tickformat: "," },
      xaxis: { title: "", gridcolor: "#f8fafc" },
      showlegend: false,
    });
  }

  function renderDemandSupplyPlot() {
    const items = DATA.page1.demandSupplyMatrix;
    const traces = [{
      type: "scatter",
      mode: "markers+text",
      x: items.map((item) => item.supply),
      y: items.map((item) => item.demand),
      text: items.map((item) => item.ingredient),
      textposition: "top center",
      marker: {
        size: items.map((item) => item.size),
        color: items.map((item) => STATUS_COLORS[item.status]),
        opacity: 0.9,
        line: { color: "rgba(255,255,255,.92)", width: 2 },
      },
      customdata: items.map((item) => [
        STATUS_LABELS[item.status],
        formatPct(item.growth),
      ]),
      hovertemplate: [
        "<b>%{text}</b>",
        "상태: %{customdata[0]}",
        "수요 지수: %{y}",
        "공급 지수: %{x}",
        `${META.comparisonLabel}: %{customdata[1]}`,
        "<extra></extra>",
      ].join("<br>"),
      showlegend: false,
    }];
    drawPlot("demandSupplyPlot", traces, {
      xaxis: { title: "공급 지수", range: [20, 100], gridcolor: "#eef2f7" },
      yaxis: { title: "수요 지수", range: [25, 105], gridcolor: "#eef2f7" },
      shapes: [
        // 좌상단: 기회 영역
        { type: "rect", x0: 20, x1: 55, y0: 65, y1: 105, fillcolor: "rgba(63, 167, 181, .10)", line: { width: 0 }, layer: "below" },

        // 우상단: 성장 영역
        { type: "rect", x0: 55, x1: 100, y0: 65, y1: 105, fillcolor: "rgba(90, 170, 110, .11)", line: { width: 0 }, layer: "below" },

        // 좌하단: 관찰 영역
        { type: "rect", x0: 20, x1: 55, y0: 25, y1: 65, fillcolor: "rgba(123, 132, 147, .08)", line: { width: 0 }, layer: "below" },

        // 우하단: 공급 과열 영역
        { type: "rect", x0: 55, x1: 100, y0: 25, y1: 65, fillcolor: "rgba(201, 122, 155, .10)", line: { width: 0 }, layer: "below" },

        { type: "line", x0: 55, x1: 55, y0: 25, y1: 105, line: { color: "#D8DEE8", width: 1, dash: "dot" } },
        { type: "line", x0: 20, x1: 100, y0: 65, y1: 65, line: { color: "#D8DEE8", width: 1, dash: "dot" } },
  ],
      annotations: [
        { x: 35, y: 100, text: "기회 영역", showarrow: false, font: { size: 11, color: "#2C7F89" } },
        { x: 76, y: 100, text: "성장 영역", showarrow: false, font: { size: 11, color: "#3F8D58" } },
        { x: 35, y: 36, text: "관찰 영역", showarrow: false, font: { size: 11, color: "#6B7280" } },
        { x: 86, y: 36, text: "공급 과열", showarrow: false, font: { size: 11, color: "#A65378" } },
  ],
    });
  }

  function getSearchTrendYAxisRange(trend) {
    const values = (trend.series || [])
      .flatMap((item) => item.values || [])
      .map(Number)
      .filter(Number.isFinite);
    if (!values.length) return [0, 105];
    const min = Math.max(0, Math.floor(Math.min(...values) - 5));
    const max = Math.min(105, Math.ceil(Math.max(...values) + 5));
    return [min, Math.max(max, min + 10)];
  }

  function createSparseTickValues(values, maxTicks = 8) {
    if (!Array.isArray(values) || values.length <= maxTicks) return values || [];
    const step = Math.max(1, Math.ceil(values.length / maxTicks));
    const ticks = values.filter((_, index) => index % step === 0);
    const last = values[values.length - 1];
    if (last && ticks[ticks.length - 1] !== last) ticks.push(last);
    return ticks;
  }

  function renderMarketProductPlot() {
    const products = getMarketProducts();
    const labels = products.map((item) => item.ingredient_label).reverse();
    const counts = products.map((item) => item.product_count).reverse();
    drawPlot("marketProductBarPlot", [{
      type: "bar",
      orientation: "h",
      y: labels,
      x: counts,
      text: counts.map((value) => `${formatNumber(value)}개`),
      textposition: "auto",
      marker: { color: "#2CA6A4", opacity: 0.82 },
      hovertemplate: "%{y}<br>제품 수 %{x:,}개<extra></extra>",
    }], {
      xaxis: { title: "제품 수", gridcolor: "#eef2f7", zeroline: false },
      yaxis: { title: "", automargin: true },
      showlegend: false,
      margin: { l: 112, r: 24, t: 10, b: 44 },
    });
  }

  function renderSearchTrendPlot() {
    const trend = DATA.page2.searchTrend;
    const traces = trend.series.map((item) => ({
      type: "scatter",
      mode: "lines+markers",
      name: item.ingredient,
      x: trend.dates,
      y: item.values,
      line: { color: item.color, width: 3 },
      marker: { size: 7 },
      hovertemplate: `${item.ingredient}<br>%{x}<br>검색 관심도 %{y:.2f}<extra></extra>`,
    }));
    drawPlot("searchTrendPlot", traces, {
      yaxis: { title: "검색 관심도 지수", gridcolor: "#eef2f7", range: getSearchTrendYAxisRange(trend) },
      xaxis: {
        title: "기간",
        gridcolor: "#f8fafc",
        tickmode: "array",
        tickvals: createSparseTickValues(trend.dates, 8),
        ticktext: createSparseTickValues(trend.dates, 8),
        tickangle: 0,
      },
      legend: { orientation: "h", y: -0.22 },
      hovermode: "x unified",
      dragmode: false,
      margin: { l: 58, r: 28, t: 20, b: 76 },
    }, { scrollZoom: false, displayModeBar: false });
  }

  function renderSentimentPlot() {
  const sentiment = DATA.page3.sentiment;

  drawPlot("sentimentPlot", [{
    type: "pie",
    labels: ["긍정", "중립", "부정"],
    values: [sentiment.positive, sentiment.neutral, sentiment.negative],
    hole: 0.62,

    marker: {
      colors: [
        "#2BB7A9", // 긍정
        "#94A3B8", // 중립
        "#F28B82"  // 부정
      ],

      line: {
        color: "#ffffff",
        width: 3
      }
    },

    textinfo: "label+percent",
    hovertemplate: "%{label}: %{value}%<extra></extra>",
  }], {
    margin: { l: 10, r: 10, t: 10, b: 10 },
    showlegend: false,

    annotations: [{
      text: `긍정<br>${sentiment.positive}%`,
      x: 0.5,
      y: 0.5,
      showarrow: false,

      font: {
        size: 18,
        color: "#2F6B66"
      },
    }],
  });
}

  function renderChartsForPanel(id) {
    if (chartRendered[id]) {
      resizeVisiblePlots();
      return;
    }
    if (id === "A") {
      renderPriceViolinPlot();
      renderDemandSupplyPlot();
    }
    if (id === "B") {
      renderSearchTrendPlot();
      renderMarketProductPlot();
    }
    if (id === "C") renderSentimentPlot();
    chartRendered[id] = true;
    resizeVisiblePlots();
  }

  function resizeVisiblePlots() {
    if (!window.Plotly) return;
    window.requestAnimationFrame(() => {
      qsa(".panel.active .js-plot").forEach((plot) => Plotly.Plots.resize(plot));
    });
  }

  function switchTab(id) {
    qsa(".panel").forEach((panel) => panel.classList.remove("active"));
    qsa(".nav-item").forEach((item) => item.classList.remove("active"));
    qs(`#panel-${id}`)?.classList.add("active");
    qs(`.nav-item[data-tab="${id}"]`)?.classList.add("active");
    renderChartsForPanel(id);
  }

  function bindNavigation() {
    qsa(".nav-item").forEach((item) => {
      item.addEventListener("click", () => switchTab(item.dataset.tab));
    });
  }

  function bindSearchPeriodControls() {
    qs("#searchPeriodButtons")?.addEventListener("click", (event) => {
      const button = event.target.closest(".period-button");
      if (!button || button.dataset.periodKey === activeSearchPeriodKey) return;
      activeSearchPeriodKey = button.dataset.periodKey;
      renderSearchPage();
      if (chartRendered.B || qs("#panel-B")?.classList.contains("active")) {
        renderSearchTrendPlot();
        renderMarketProductPlot();
        resizeVisiblePlots();
      }
      loadDatalabSearchTrend();
    });
  }

  function bindWindowEvents() {
    window.addEventListener("resize", resizeVisiblePlots);
  }

  function init() {
    renderDataStatus();
    qs("#sidebarSnapshotText").textContent = `떡잎마을 방범대 · ${META.dataRange}`;
    renderMarketPage();
    renderSearchPage();
    renderReviewPage();
    renderAlertPage();
    renderAgentPage();
    bindNavigation();
    bindSearchPeriodControls();
    bindWindowEvents();
    renderChartsForPanel("A");
    loadDatalabDashboardSignals();
    loadDatalabSearchTrend();
  }

  window.renderDataStatus = renderDataStatus;
  window.switchTab = switchTab;
  window.addEventListener("DOMContentLoaded", init);
})();
