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
      selectedIngredient: "레티놀",
      selectedSummary: {},
      searchTrend: { dates: [], series: [] },
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
    page4: { summary: [], alerts: [] },
    page5: { promptPlaceholder: "", recommendations: [] },
  };

  const DATA = window.DASHBOARD_DATA || FALLBACK_DATA;
  const META = DATA.meta;
  const chartRendered = {};
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
      ["전체 검색량 증감률", formatPct(summary.totalSearchGrowthRate), "▴", "positive"],
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

  function renderRankList(targetId, items, valueLabel) {
    qs(`#${targetId}`).innerHTML = items.map((item, index) => `
      <div class="rank-item">
        <div class="rank-index">${index + 1}</div>
        <div class="rank-body">
          <div class="rank-title">${escapeHtml(item.label)}</div>
          <div class="rank-bar">
            <span style="width:${Math.max(8, Math.min(100, Number(item.searchIndex || 0)))}%"></span>
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
    renderRankList("functionRiserList", DATA.page1.functionRisers, META.comparisonLabel);
    renderRankList("ingredientPopularityList", DATA.page1.ingredientPopularity, META.comparisonLabel);
    renderMatrixLegend();
    renderInsightList("marketInsights", DATA.page1.insights);
  }

  function renderSearchPage() {
    const page = DATA.page2;
    qs("#searchPeriodLabel").textContent = page.periodLabel;
    const leadSeries = page.searchTrend.series[0];
    const leadStart = Number(leadSeries?.values?.[0] || 0);
    const leadEnd = Number(leadSeries?.values?.[leadSeries.values.length - 1] || 0);
    const leadGrowth = leadStart ? ((leadEnd - leadStart) / leadStart) * 100 : page.selectedSummary.growthRate;
    qs("#searchTrendBadges").innerHTML = [
      `${leadSeries?.ingredient || page.selectedIngredient} ${META.comparisonLabel} ${formatPct(page.selectedSummary.growthRate)}`,
      `시작일 대비 ${formatPct(leadGrowth)}`,
      "마우스 휠 확대",
      "하단 슬라이더로 구간 선택",
    ].map((label, index) => `
      <span class="trend-badge ${index === 0 ? "primary" : ""}">${escapeHtml(label)}</span>
    `).join("");
    qs("#selectedIngredientSummary").innerHTML = [
      ["선택 성분", page.selectedIngredient],
      ["주간 검색량", formatNumber(page.selectedSummary.weeklySearchVolume)],
      [META.comparisonLabel, formatPct(page.selectedSummary.growthRate), "positive"],
      ["검색 피크", page.selectedSummary.peakDate],
      ["주요 피부고민", page.selectedSummary.leadingConcern],
    ].map(([label, value, tone]) => `
      <div class="mini-summary ${tone || ""}">
        <span>${escapeHtml(label)}</span>
        <strong>${escapeHtml(value)}</strong>
      </div>
    `).join("");
    const concernMetrics = [
      ["elasticity", "탄력/주름"],
      ["texture", "피부결"],
      ["barrier", "장벽"],
      ["calming", "진정"],
    ];
    const concernValues = page.concernTable.flatMap((row) => concernMetrics.map(([key]) => Number(row[key] || 0)));
    const maxConcernValue = Math.max(...concernValues, 1);
    qs("#concernHeatmap").innerHTML = `
      <div class="heatmap-grid" style="--heatmap-columns:${concernMetrics.length}">
        <div class="heatmap-head">연령대</div>
        ${concernMetrics.map(([, label]) => `<div class="heatmap-head">${escapeHtml(label)}</div>`).join("")}
        ${page.concernTable.map((row) => `
          <div class="heatmap-age">${escapeHtml(row.age)}</div>
          ${concernMetrics.map(([key]) => {
            const value = Number(row[key] || 0);
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
    qs("#ageTopIngredients").innerHTML = page.ageTopIngredients.map((row) => `
      <div class="age-top-card">
        <div class="age-label">${escapeHtml(row.age)}</div>
        ${row.top.map((item, index) => `
          <div class="age-rank">
            <span>${index + 1}</span>
            <strong>${escapeHtml(item)}</strong>
          </div>
        `).join("")}
      </div>
    `).join("");
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

  function renderAlertPage() {
    const page = DATA.page4;
    qs("#alertSummary").innerHTML = page.summary.map((item) => `
      <div class="summary-chip ${item.tone}">
        <span>${escapeHtml(item.label)}</span>
        <strong>${escapeHtml(item.value)}</strong>
      </div>
    `).join("");
    qs("#alertList").innerHTML = page.alerts.map((alert) => `
      <article class="alert-item ${alert.level}">
        <div class="alert-marker">${escapeHtml(alert.type)}</div>
        <div class="alert-body">
          <div class="alert-title-row">
            <strong>${escapeHtml(alert.title)}</strong>
            <span>${escapeHtml(alert.timestamp)}</span>
          </div>
          <p>${escapeHtml(alert.message)}</p>
        </div>
        <div class="alert-metric">${escapeHtml(alert.metric)}</div>
      </article>
    `).join("");
  }

  function renderAgentPage() {
    const page = DATA.page5;
    const input = qs("#agentPrompt");
    input.placeholder = page.promptPlaceholder;
    qs("#aiRecommendations").innerHTML = page.recommendations.map((item) => `
      <article class="recommendation-card">
        <div class="recommendation-top">
          <strong>${escapeHtml(item.title)}</strong>
          <span>${escapeHtml(item.confidence)}</span>
        </div>
        <p class="recommendation-overview">${escapeHtml(item.evidence)}</p>
        <div class="recommendation-details">
          <div class="action-box">
            <span>근거 데이터</span>
            <strong>${escapeHtml(item.evidence)}</strong>
          </div>
          <div class="action-box">
            <span>추천 전략</span>
            <strong>${escapeHtml(item.action)}</strong>
          </div>
        </div>
        <button class="btn btn-outline strategy-button" type="button">전략 상세 보기</button>
      </article>
    `).join("");
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
      hovertemplate: `${item.ingredient}<br>%{x}<br>검색 지수 %{y}<extra></extra>`,
    }));
    drawPlot("searchTrendPlot", traces, {
      yaxis: { title: "검색량 상대지수", gridcolor: "#eef2f7", range: [40, 105] },
      xaxis: {
        title: "기간",
        gridcolor: "#f8fafc",
        rangeslider: { visible: true, thickness: 0.12, bgcolor: "#f8fafc", bordercolor: "#dbe2ea", borderwidth: 1 },
      },
      legend: { orientation: "h", y: -0.22 },
      hovermode: "x unified",
      dragmode: "zoom",
      margin: { l: 58, r: 28, t: 20, b: 88 },
    }, { scrollZoom: true, displayModeBar: true, modeBarButtonsToRemove: ["lasso2d", "select2d"] });
  }

  function renderSentimentPlot() {
    const sentiment = DATA.page3.sentiment;
    drawPlot("sentimentPlot", [{
      type: "pie",
      labels: ["긍정", "중립", "부정"],
      values: [sentiment.positive, sentiment.neutral, sentiment.negative],
      hole: 0.62,
      marker: { colors: ["#22c55e", "#94a3b8", "#ef4444"] },
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
        font: { size: 18, color: "#14532d" },
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
    if (id === "B") renderSearchTrendPlot();
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
    bindWindowEvents();
    renderChartsForPanel("A");
  }

  window.renderDataStatus = renderDataStatus;
  window.switchTab = switchTab;
  window.addEventListener("DOMContentLoaded", init);
})();
