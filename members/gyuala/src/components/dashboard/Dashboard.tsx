"use client";

import { Fragment, useEffect, useMemo, useRef, useState, type CSSProperties, type MouseEvent, type ReactNode } from "react";
import { dashboardData } from "@/lib/mock-data";
import {
  DEFAULT_DEMAND_SUPPLY_MATRIX_CONFIG,
  fetchDemandSupplyMatrixFromSupabase,
} from "@/lib/demand-supply-matrix";
import { fetchPriceDistributionFromSupabase, getEmptyPriceDistribution } from "@/lib/price-distribution";
import type {
  AlertItem,
  ConcernMetric,
  DashboardData,
  DashboardMeta,
  DemandSupplyItem,
  Keyword,
  MarketProduct,
  Page1Summary,
  PriceDistributionItem,
  PriceDistributionPoint,
  RankItem,
  ReviewIngredient,
  SearchTrendSeries,
} from "@/lib/types";

type TabId = "A" | "B" | "C" | "D" | "E";
type PriceType = "sale" | "list";
type ApiState = "idle" | "loading" | "ready" | "error";

type DataLoadState = {
  dashboardSignals: ApiState;
  searchTrend: ApiState;
  priceDistribution: ApiState;
  demandSupplyMatrix: ApiState;
  page1Insights: ApiState;
  dashboardSignalsError: string;
  searchTrendError: string;
  priceDistributionError: string;
  demandSupplyMatrixError: string;
  page1InsightsError: string;
};

type DashboardSignalsPayload = Omit<Partial<DashboardData>, "page1" | "page2"> & {
  page1?: Partial<DashboardData["page1"]>;
  page2?: Partial<DashboardData["page2"]>;
};

const DATALAB_API_BASE_URL = process.env.NEXT_PUBLIC_DATALAB_API_BASE_URL || "https://cosmetic-api-clae.onrender.com";

const NAV_ITEMS: Array<{ id: TabId; index: string; label: string; badge?: string }> = [
  { id: "A", index: "01", label: "시장 요약" },
  { id: "B", index: "02", label: "검색 트렌드 분석" },
  { id: "C", index: "03", label: "소비자 리뷰 분석" },
  { id: "D", index: "04", label: "경보", badge: "5" },
  { id: "E", index: "05", label: "AI Agent" },
];

const SEARCH_PERIOD_OPTIONS = [
  { key: "snapshot", label: "스냅샷" },
  { key: "1m", label: "1개월" },
  { key: "6m", label: "6개월" },
  { key: "1y", label: "1년" },
  { key: "3y", label: "3년" },
];

const MAIN_INGREDIENTS = [
  { key: "niacinamide", label: "나이아신아마이드" },
  { key: "hyaluronic_acid", label: "히알루론산" },
  { key: "centella", label: "병풀/시카" },
  { key: "pdrn", label: "PDRN" },
  { key: "retinol", label: "레티놀" },
];

type RankingProduct = {
  collected_date?: string;
  sort_type?: string;
  rank?: number;
  brand?: string;
  product_name?: string;
  product_name_clean?: string;
};

type DashboardSummaryResponse = {
  meta?: Partial<DashboardMeta> & { source?: string };
  page1?: Partial<DashboardData["page1"]>;
  page2?: Partial<DashboardData["page2"]>;
  counts?: Array<{ table_name?: string; cnt?: number }>;
  latest_rankings?: RankingProduct[];
  top_review_products?: RankingProduct[];
  review_data_status?: string;
};

type DatalabWeeklyInterestResponse = {
  meta?: Partial<DashboardMeta> & { source?: string };
  page1?: {
    functionRisers?: unknown;
    ingredientPopularity?: unknown;
    ingredientDemand?: unknown;
  };
};

const DATALAB_WEEKLY_API_REQUIRED_MESSAGE = "네이버 데이터랩 주간 검색 관심도를 불러오지 못했습니다.";
const NAVER_DEMAND_API_REQUIRED_MESSAGE = "네이버 데이터랩 수요 데이터를 불러오지 못했습니다.";
const INSIGHT_GENERATION_ERROR_MESSAGE = "인사이트 요약을 생성하지 못했습니다.";

// Page 1 DataLab rankings are loaded through the server-only Next route
// /api/dashboard/datalab-weekly-interest so Naver credentials never reach the browser.

const DATALAB_TREND_COLORS: Record<string, string> = {
  "레티놀": "#3B66A6",
  "PDRN": "#2CA6A4",
  "나이아신아마이드": "#E6A23C",
  "히알루론산": "#8B7CC8",
  "병풀/시카": "#5AAA6E",
};

const STATUS_LABELS: Record<DemandSupplyItem["status"], string> = {
  growth: "성장",
  shortage: "기회",
  opportunity: "기회",
  oversupply: "공급 과잉",
  stable: "관찰",
};

const STATUS_COLORS: Record<DemandSupplyItem["status"], string> = {
  growth: "#5AAA6E",
  shortage: "#D96A7A",
  opportunity: "#3FA7B5",
  oversupply: "#C97A9B",
  stable: "#7B8493",
};

const MATRIX_STATUS_KEYS: DemandSupplyItem["status"][] = ["growth", "opportunity", "oversupply", "stable"];

const CHART_COLORS = ["#2563eb", "#14b8a6", "#f59e0b", "#8b5cf6", "#64748b"];

const INITIAL_DASHBOARD_DATA = {
  ...dashboardData,
  page1Summary: {
    analyzedProducts: 0,
    analyzedIngredients: 0,
    totalSearchGrowthRate: 0,
    risingIngredientCount: 0,
    supplyShortageIngredientCount: 0,
  },
  page1: {
    ...dashboardData.page1,
    insights: [],
    priceDistribution: getEmptyPriceDistribution(),
    demandSupplyMatrix: [],
  },
} satisfies DashboardData;

function buildDatalabApiUrl(path: string) {
  const baseUrl = DATALAB_API_BASE_URL.replace(/\/+$/, "");
  const apiPath = path.startsWith("/") ? path : `/${path}`;
  return `${baseUrl}${apiPath}`;
}

async function fetchDatalabJson<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(buildDatalabApiUrl(path), {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = getApiErrorMessage(payload);
    throw new Error(message);
  }
  return payload as T;
}

async function fetchLocalJson<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(getApiErrorMessage(payload));
  }
  return payload as T;
}

async function fetchCurrentApiDashboardSignals(): Promise<DashboardSignalsPayload> {
  const [summaryResult, weeklyResult] = await Promise.allSettled([
    fetchDatalabJson<DashboardSummaryResponse>("/dashboard/summary"),
    fetchLocalJson<DatalabWeeklyInterestResponse>("/api/dashboard/datalab-weekly-interest"),
  ]);
  const summary = summaryResult.status === "fulfilled" ? summaryResult.value : {};
  const weekly = weeklyResult.status === "fulfilled" ? weeklyResult.value : {};
  const summaryPayload = normalizeDashboardSummary(summary);
  const weeklyPayload = normalizeDatalabWeeklyInterest(weekly);
  const functionRisers = weeklyPayload.page1?.functionRisers || [];
  const ingredientPopularity = weeklyPayload.page1?.ingredientPopularity || [];

  if (summaryResult.status === "rejected") {
    console.error("FastAPI /dashboard/summary 조회 실패", summaryResult.reason);
  }

  if (weeklyResult.status === "rejected") {
    console.error("Naver DataLab 주간 검색 관심도 직접 조회 실패", weeklyResult.reason);
  }

  return {
    ...summaryPayload,
    meta: {
      ...summaryPayload.meta,
      ...(weeklyPayload.meta || {}),
      dataRange: weeklyPayload.meta?.dataRange || summaryPayload.meta?.dataRange || "Naver DataLab 주간 검색 관심도",
      lastUpdated: weeklyPayload.meta?.lastUpdated || summaryPayload.meta?.lastUpdated || "-",
      comparisonLabel: "전주 대비 증감률",
    },
    page1Summary: {
      analyzedProducts: summaryPayload.page1Summary?.analyzedProducts || 0,
      analyzedIngredients: summaryPayload.page1Summary?.analyzedIngredients || 0,
      totalSearchGrowthRate: getAverageGrowth([...functionRisers, ...ingredientPopularity]),
      risingIngredientCount: functionRisers.length,
      supplyShortageIngredientCount: summaryPayload.page1Summary?.supplyShortageIngredientCount || 0,
    },
    page1: {
      ...summaryPayload.page1,
      functionRisers,
      ingredientPopularity,
    },
  };
}

function normalizeDatalabWeeklyInterest(payload: DatalabWeeklyInterestResponse): DashboardSignalsPayload {
  return {
    meta: {
      ...payload.meta,
      apiSource: payload.meta?.apiSource || payload.meta?.source || "naver_datalab",
      dataRange: payload.meta?.dataRange || "Naver DataLab 주간 검색 관심도",
      lastUpdated: payload.meta?.lastUpdated || "-",
      comparisonLabel: "전주 대비 증감률",
    },
    page1: {
      functionRisers: normalizeDatalabWeeklyRankItems(payload.page1?.functionRisers, "growth"),
      ingredientPopularity: normalizeDatalabWeeklyRankItems(payload.page1?.ingredientPopularity, "searchIndex"),
    },
  };
}

function normalizeDashboardSummary(summary: DashboardSummaryResponse): DashboardSignalsPayload {
  const latestDate = getLatestRankingDate(summary.latest_rankings || []);
  const tableCounts = new Map((summary.counts || []).map((row) => [row.table_name || "", Number(row.cnt || 0)]));
  const page1 = summary.page1 || {};
  const page2 = summary.page2 || {};

  return {
    meta: {
      ...summary.meta,
      apiSource: summary.meta?.apiSource || summary.meta?.source || "fastapi_supabase",
      dataRange: summary.meta?.dataRange || (latestDate ? `${latestDate} 랭킹 스냅샷` : "FastAPI Supabase 최신 데이터"),
      lastUpdated: summary.meta?.lastUpdated || latestDate || "-",
      comparisonLabel: summary.meta?.comparisonLabel || "전주 대비 증감률",
    },
    page1Summary: {
      analyzedProducts: tableCounts.get("products") || 0,
      analyzedIngredients: tableCounts.get("product_main_ingredients") || 0,
      totalSearchGrowthRate: 0,
      risingIngredientCount: page1.functionRisers?.length || 0,
      supplyShortageIngredientCount: 0,
    },
    page1: {
      functionRisers: normalizeDatalabWeeklyRankItems(page1.functionRisers, "growth"),
      ingredientPopularity: normalizeDatalabWeeklyRankItems(page1.ingredientPopularity, "searchIndex"),
      insights: [],
    },
    page2: {
      concernMetrics: page2.concernMetrics || [],
      concernTable: page2.concernTable || [],
      marketProducts: page2.marketProducts || [],
      insights: page2.insights || [],
    },
  };
}

function normalizeDatalabWeeklyRankItems(items: unknown, sortBy: "growth" | "searchIndex"): RankItem[] {
  if (!Array.isArray(items)) return [];
  const rows: RankItem[] = [];

  items.forEach((item) => {
    const row = item as Partial<RankItem> & {
      rawIndex?: number;
      ingredient_label?: string;
      title?: string;
      currentWeekIndex?: number;
      previousWeekIndex?: number;
      current_week_index?: number;
      previous_week_index?: number;
      this_week_index?: number;
      last_week_index?: number;
      search_index_recent?: number;
      search_index_previous?: number;
      current_index?: number;
      previous_index?: number;
      growth?: number;
    };
    const label = row.label || row.ingredient_label || row.title;
    if (!label) return;
    const currentWeekIndex = getFirstFiniteNumber(row, [
      "currentWeekIndex",
      "current_week_index",
      "this_week_index",
      "search_index_recent",
      "current_index",
    ]);
    const previousWeekIndex = getFirstFiniteNumber(row, [
      "previousWeekIndex",
      "previous_week_index",
      "last_week_index",
      "search_index_previous",
      "previous_index",
    ]);

    if (currentWeekIndex === null || previousWeekIndex === null) {
      console.error("DataLab 주간 검색 관심도 응답에 이번 주/전주 지수가 없습니다.", { label, row });
      return;
    }
    const providedGrowth = getFirstFiniteNumber(row, ["growth"]);
    const growth = providedGrowth ?? calculateWeeklyGrowth(currentWeekIndex, previousWeekIndex);

    rows.push({
      label,
      growth,
      searchIndex: currentWeekIndex,
    });
  });

  return sortDatalabRankItems(rows, sortBy).slice(0, 5);
}

function sortDatalabRankItems(items: RankItem[], sortBy: "growth" | "searchIndex") {
  // 성분 인기 순위는 "인기" 문맥에 맞춰 이번 주 검색 관심도(searchIndex)가 높은 순으로 정렬한다.
  return items.slice().sort((a, b) => Number(b[sortBy] || 0) - Number(a[sortBy] || 0));
}

function calculateWeeklyGrowth(currentWeekIndex: number, previousWeekIndex: number) {
  if (previousWeekIndex <= 0) return currentWeekIndex > 0 ? 100 : 0;
  return ((currentWeekIndex - previousWeekIndex) / previousWeekIndex) * 100;
}

function getAverageGrowth(items: RankItem[]) {
  const growthValues = items.map((item) => Number(item.growth || 0)).filter((value) => Number.isFinite(value));
  if (!growthValues.length) return 0;
  return growthValues.reduce((sum, value) => sum + value, 0) / growthValues.length;
}

function getFirstFiniteNumber(row: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    if (!(key in row)) continue;
    const value = row[key];
    if (value === null || value === undefined || value === "") continue;
    const number = Number(value);
    if (Number.isFinite(number)) return number;
  }

  return null;
}

function getLatestRankingDate(items: RankingProduct[]) {
  return items
    .map((item) => item.collected_date || "")
    .filter(Boolean)
    .sort()
    .at(-1);
}

function getApiErrorMessage(payload: unknown) {
  const row = payload as { message?: unknown; detail?: unknown; error?: unknown };
  if (typeof row.message === "string") return row.message;
  if (typeof row.detail === "string") return row.detail;
  if (typeof row.error === "string") return row.error;
  return "FastAPI 요청에 실패했습니다.";
}

function mergeDashboardSignals(current: DashboardData, payload: DashboardSignalsPayload) {
  const nextMeta = payload.meta as (Partial<DashboardMeta> & { source?: string }) | undefined;
  const hasPage1Payload = Boolean(payload.page1);
  return {
    ...current,
    meta: {
      ...current.meta,
      ...(payload.meta || {}),
      apiSource: nextMeta?.apiSource || nextMeta?.source || current.meta.apiSource,
    } as DashboardMeta,
    page1Summary: {
      ...current.page1Summary,
      ...(payload.page1Summary || {}),
    },
    page1: {
      ...current.page1,
      functionRisers: hasPage1Payload && "functionRisers" in (payload.page1 || {}) ? payload.page1?.functionRisers || [] : current.page1.functionRisers,
      ingredientPopularity: hasPage1Payload && "ingredientPopularity" in (payload.page1 || {}) ? payload.page1?.ingredientPopularity || [] : current.page1.ingredientPopularity,
      insights: current.page1.insights,
    },
    page2: {
      ...current.page2,
      concernMetrics: payload.page2?.concernMetrics?.length ? payload.page2.concernMetrics : current.page2.concernMetrics,
      concernTable: payload.page2?.concernTable?.length ? payload.page2.concernTable : current.page2.concernTable,
      marketProducts: payload.page2?.marketProducts?.length ? payload.page2.marketProducts : current.page2.marketProducts,
      insights: payload.page2?.insights?.length ? payload.page2.insights : current.page2.insights,
    },
  } satisfies DashboardData;
}

function mergeIngredientTrend(current: DashboardData, payload: Partial<DashboardData["page2"]>) {
  if (!payload.searchTrend?.dates?.length || !payload.searchTrend?.series?.length) return current;
  return {
    ...current,
    page2: {
      ...current.page2,
      periodLabel: payload.periodLabel || current.page2.periodLabel,
      selectedIngredient: payload.selectedIngredient || current.page2.selectedIngredient,
      selectedSummary: {
        ...current.page2.selectedSummary,
        ...(payload.selectedSummary || {}),
      },
      searchTrend: payload.searchTrend,
    },
  };
}

function mergePriceDistribution(current: DashboardData, priceDistribution: PriceDistributionItem[]) {
  return {
    ...current,
    page1: {
      ...current.page1,
      priceDistribution,
    },
  } satisfies DashboardData;
}

function mergeDemandSupplyMatrix(current: DashboardData, demandSupplyMatrix: DemandSupplyItem[]) {
  return {
    ...current,
    page1: {
      ...current.page1,
      demandSupplyMatrix,
    },
  } satisfies DashboardData;
}

function mergePage1Insights(current: DashboardData, insights: string[]) {
  return {
    ...current,
    page1: {
      ...current.page1,
      insights,
    },
  } satisfies DashboardData;
}

function formatNumber(value: number | string | undefined) {
  return Number(value || 0).toLocaleString("ko-KR");
}

function formatPct(value: number | string | undefined) {
  const number = Number(value || 0);
  return `${number > 0 ? "+" : ""}${number.toFixed(1)}%`;
}

function calculateSeriesGrowth(series?: SearchTrendSeries, fallback = 0) {
  const values = (series?.values || []).filter((value) => Number.isFinite(Number(value)));
  if (values.length < 2) return fallback;
  const start = Number(values[0]);
  const end = Number(values[values.length - 1]);
  return start ? ((end - start) / start) * 100 : fallback;
}

function getRankBarWidth(item: RankItem, items: RankItem[], barMetric: "growth" | "searchIndex") {
  if (barMetric === "growth") {
    const maxGrowth = Math.max(...items.map((row) => Math.max(0, Number(row.growth || 0))), 1);
    return Math.max(8, Math.min(100, (Math.max(0, Number(item.growth || 0)) / maxGrowth) * 100));
  }

  return Math.max(8, Math.min(100, Number(item.searchIndex || 0)));
}

function getPriceValues(item: PriceDistributionItem, priceType: PriceType) {
  const points = priceType === "list" ? item.listPricePoints : item.salePricePoints;
  if (points?.length) return points.map((point) => point.value);
  if (priceType === "list") return item.listPrices || item.prices || item.salePrices || [];
  return item.salePrices || item.prices || item.listPrices || [];
}

function getPricePoints(item: PriceDistributionItem, priceType: PriceType): PriceDistributionPoint[] {
  const points = priceType === "list" ? item.listPricePoints : item.salePricePoints;
  if (points?.length) return points;

  return getPriceValues(item, priceType).map((value) => ({
    value,
    ingredient: item.ingredient,
    productName: "상품명 없음",
    basisPrice: null,
    regularPrice: null,
    salesPrice: null,
    volumeMl: null,
    priceType,
  }));
}

function getPriceAxisRange(values: number[]) {
  const rawMin = Math.min(...values);
  const rawMax = Math.max(...values);
  const spread = Math.max(1000, rawMax - rawMin);
  const min = Math.max(0, Math.floor((rawMin - spread * 0.08) / 1000) * 1000);
  const max = Math.ceil((rawMax + spread * 0.08) / 1000) * 1000;
  return { min, max: Math.max(max, min + 1000) };
}

function getQuantile(values: number[], ratio: number) {
  if (!values.length) return 0;
  return values[Math.min(values.length - 1, Math.floor(values.length * ratio))];
}

function getDisplayPricePoints(values: PriceDistributionPoint[], maxPoints = 70) {
  if (values.length <= maxPoints) return values;
  const step = Math.ceil(values.length / maxPoints);
  return values.filter((_, index) => index % step === 0).slice(0, maxPoints);
}

function getViolinPath(values: number[], x: number, yFor: (value: number) => number, maxWidth: number) {
  const localMin = values[0];
  const localMax = values[values.length - 1];
  const spread = Math.max(1, localMax - localMin);
  const bandwidth = Math.max(spread / 5, 800);
  const densityPoints = Array.from({ length: 30 }, (_, index) => {
    const value = localMin + (spread * index) / 29;
    const density = values.reduce((sum, price) => {
      const distance = (value - price) / bandwidth;
      return sum + Math.exp(-0.5 * distance * distance);
    }, 0) / values.length;

    return { value, density };
  });
  const maxDensity = Math.max(...densityPoints.map((point) => point.density), 1);
  const rightPoints = densityPoints.map((point) => {
    const halfWidth = 4 + (point.density / maxDensity) * maxWidth;
    return `${x + halfWidth},${yFor(point.value)}`;
  });
  const leftPoints = densityPoints.slice().reverse().map((point) => {
    const halfWidth = 4 + (point.density / maxDensity) * maxWidth;
    return `${x - halfWidth},${yFor(point.value)}`;
  });

  return `M ${rightPoints.join(" L ")} L ${leftPoints.join(" L ")} Z`;
}

function formatPriceTooltip(point: PriceDistributionPoint, priceType: PriceType) {
  const basisLabel = priceType === "list" ? "정가" : "판매가";
  const basisPrice = point.basisPrice ? `${formatNumber(point.basisPrice)}원` : "-";
  const volume = point.volumeMl ? `${formatNumber(point.volumeMl)}ml/g` : "-";
  const lines = [
    `제품명: ${point.productName || point.goodsNo || "상품명 없음"}`,
    `성분명: ${point.ingredient}`,
    `10ml당 가격: ${formatNumber(point.value)}원`,
    `${basisLabel}: ${basisPrice}`,
    `용량: ${volume}`,
  ];

  if (point.goodsNo) lines.push(`goods_no: ${point.goodsNo}`);
  return lines.join("\n");
}

function getPriceDistributionHighlights(items: PriceDistributionItem[]) {
  const points = items.flatMap((item) => [
    ...getPricePoints(item, "sale").map((point) => ({ ...point, priceBasis: "판매가" })),
    ...getPricePoints(item, "list").map((point) => ({ ...point, priceBasis: "정가" })),
  ]);

  return points
    .filter((point) => Number.isFinite(point.value))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8)
    .map((point) => ({
      ingredient: point.ingredient,
      productName: point.productName || point.goodsNo || "상품명 없음",
      goodsNo: point.goodsNo || "",
      priceBasis: point.priceBasis,
      pricePer10ml: point.value,
      basisPrice: point.basisPrice,
      volumeMl: point.volumeMl,
    }));
}

function buildPage1InsightPayload(data: DashboardData, loadState: DataLoadState) {
  return {
    functionTop5: data.page1.functionRisers.map((item) => ({
      label: item.label,
      weekOverWeekGrowthRate: roundNumber(Number(item.growth || 0), 1),
      currentWeekSearchIndex: roundNumber(Number(item.searchIndex || 0), 1),
    })),
    ingredientTop5: data.page1.ingredientPopularity.map((item) => ({
      label: item.label,
      weekOverWeekGrowthRate: roundNumber(Number(item.growth || 0), 1),
      currentWeekSearchIndex: roundNumber(Number(item.searchIndex || 0), 1),
    })),
    priceOutliers: getPriceDistributionHighlights(data.page1.priceDistribution),
    demandSupplyMatrix: data.page1.demandSupplyMatrix.map((item) => ({
      ingredient: item.ingredient,
      demandScore: roundNumber(item.demand, 1),
      supplyScore: roundNumber(item.supply, 1),
      weekOverWeekDemandGrowthRate: roundNumber(item.growth, 1),
      quadrant: STATUS_LABELS[item.status],
    })),
    dataAvailability: {
      functionTop5: loadState.dashboardSignalsError || (data.page1.functionRisers.length ? "ready" : DATALAB_WEEKLY_API_REQUIRED_MESSAGE),
      ingredientTop5: loadState.dashboardSignalsError || (data.page1.ingredientPopularity.length ? "ready" : DATALAB_WEEKLY_API_REQUIRED_MESSAGE),
      priceDistribution: loadState.priceDistributionError || (getPriceDistributionHighlights(data.page1.priceDistribution).length ? "ready" : "가격 데이터 없음"),
      demandSupplyMatrix: loadState.demandSupplyMatrixError || (data.page1.demandSupplyMatrix.length ? "ready" : NAVER_DEMAND_API_REQUIRED_MESSAGE),
    },
  };
}

function roundNumber(value: number, digits = 0) {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

function getProductGrowth(item: MarketProduct) {
  const growth = Number(item.product_growth_rate);
  if (Number.isFinite(growth)) return growth;
  const current = Number(item.product_count || 0);
  const previous = Number(item.previous_product_count || 0);
  return previous > 0 ? ((current - previous) / previous) * 100 : 0;
}

function getGrowthDisplay(growthRate: number) {
  const growth = Number(growthRate || 0);
  if (growth > 0) return { text: `▲ +${growth.toFixed(1)}%`, color: "#059669" };
  if (growth < 0) return { text: `▼ ${growth.toFixed(1)}%`, color: "#dc2626" };
  return { text: "― 0.0%", color: "#64748b" };
}

function getMarketReflectionStatus(growthRate: number, productCount: number) {
  const isSearchUp = Number(growthRate || 0) >= 5;
  const isProductHigh = Number(productCount || 0) >= 70;
  if (isSearchUp && !isProductHigh) return "기회 성분";
  if (isSearchUp && isProductHigh) return "주류/포화 성분";
  if (!isSearchUp && isProductHigh) return "리스크 성분";
  return "미성숙/관망 성분";
}

function getSeverityClass(severity: AlertItem["severity"]) {
  if (severity === "높음") return "high";
  if (severity === "낮음") return "low";
  return "medium";
}

function DataStatusCard({
  meta,
  isLoading,
  error,
  onRefresh,
}: {
  meta: DashboardMeta;
  isLoading: boolean;
  error: string;
  onRefresh: () => void;
}) {
  const dataSource = meta.apiSource === "naver_datalab"
    ? "Naver DataLab"
    : meta.apiSource === "fastapi_supabase"
      ? "FastAPI/Supabase"
      : "연결 확인 중";

  return (
    <div className="data-status-card">
      <div className="data-status-copy">
        <div className="data-status-line">
          <span>데이터 기준</span>
          <strong>{meta.dataRange}</strong>
        </div>
        <div className="data-status-line">
          <span>마지막 업데이트</span>
          <strong>{meta.lastUpdated}</strong>
        </div>
        <div className="data-status-line">
          <span>데이터 소스</span>
          <strong>{error ? "연결 오류" : isLoading ? "연결 중" : dataSource}</strong>
        </div>
      </div>
      <button
        className="btn btn-outline update-data-button"
        type="button"
        aria-label="데이터 업데이트 요청"
        title={error || "데이터 업데이트 요청"}
        onClick={onRefresh}
        disabled={isLoading}
      >
        {isLoading ? "…" : "↻"}
      </button>
    </div>
  );
}

function PageHeader({
  badge,
  title,
  description,
  actions,
  statusCard,
  compact = false,
}: {
  badge: string;
  title: string;
  description: string;
  actions?: ReactNode;
  statusCard: ReactNode;
  compact?: boolean;
}) {
  return (
    <header className={`page-header ${compact ? "compact-page-header" : ""}`}>
      <div>
        <span className="page-badge">{badge}</span>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      <div className="page-header-actions">
        {actions}
        <div className="data-status-slot">
          {statusCard}
        </div>
      </div>
    </header>
  );
}

function SummaryStrip({ summary }: { summary: Page1Summary }) {
  const items = [
    ["분석 제품 수", `${formatNumber(summary.analyzedProducts)}개`, "▯", ""],
    ["분석 성분 수", `${formatNumber(summary.analyzedIngredients)}개`, "◎", "green"],
    ["전체 검색 관심도 증감률", formatPct(summary.totalSearchGrowthRate), "▴", "positive"],
    ["급상승 성분 수", `${formatNumber(summary.risingIngredientCount)}개`, "⚡", "blue"],
    ["공급 부족 성분 수", `${formatNumber(summary.supplyShortageIngredientCount)}개`, "△", "warning"],
  ];

  return (
    <div className="summary-strip">
      {items.map(([label, value, icon, tone]) => (
        <div className={`summary-chip ${tone}`} key={label}>
          <div className="summary-icon">{icon}</div>
          <div>
            <span>{label}</span>
            <strong>{value}</strong>
          </div>
        </div>
      ))}
    </div>
  );
}

function RankList({
  items,
  valueLabel,
  barMetric,
  valueMetric = barMetric,
  isLoading,
  error,
}: {
  items: RankItem[];
  valueLabel: string;
  barMetric: "growth" | "searchIndex";
  valueMetric?: "growth" | "searchIndex";
  isLoading: boolean;
  error: string;
}) {
  if (!items.length) {
    return (
      <div className="empty-state api-state">
        {error || (isLoading ? "Naver DataLab API에서 데이터를 불러오는 중입니다." : DATALAB_WEEKLY_API_REQUIRED_MESSAGE)}
      </div>
    );
  }

  return (
    <div className="rank-list">
      {items.map((item, index) => (
        <div className="rank-item" key={`${item.label}-${index}`}>
          <div className="rank-index">{index + 1}</div>
          <div className="rank-body">
            <div className="rank-title">{item.label}</div>
            <div className="rank-bar">
              <span style={{ width: `${getRankBarWidth(item, items, barMetric)}%` }} />
            </div>
          </div>
          <div className="rank-value">
            <strong>{valueMetric === "searchIndex" ? formatNumber(Math.round(Number(item.searchIndex || 0))) : formatPct(item.growth)}</strong>
            <span>{valueLabel}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function InsightList({ items, fallback }: { items: string[]; fallback?: string }) {
  const rows = items.length ? items : fallback ? [fallback] : [];

  return (
    <div className="insight-list">
      {rows.map((item) => (
        <div className="insight-item" key={item}>
          {item}
        </div>
      ))}
    </div>
  );
}

function PriceDistributionPlot({
  items,
  priceType,
  isLoading,
  error,
}: {
  items: PriceDistributionItem[];
  priceType: PriceType;
  isLoading: boolean;
  error: string;
}) {
  const [tooltip, setTooltip] = useState<{ point: PriceDistributionPoint; x: number; y: number } | null>(null);
  const allValues = items
    .flatMap((item) => getPricePoints(item, priceType).map((point) => point.value))
    .filter((value) => Number.isFinite(value));
  const width = 640;
  const height = 276;
  const padding = { top: 24, right: 32, bottom: 52, left: 58 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;

  if (!allValues.length) {
    return (
      <div className="plot-shell chart-shell">
        <div className="empty-state api-state">
          {error ? `Supabase 오류: ${error}` : isLoading ? "Supabase에서 가격 데이터를 불러오는 중입니다." : "표시할 가격 데이터가 없습니다."}
        </div>
      </div>
    );
  }

  const { min, max } = getPriceAxisRange(allValues);
  const yFor = (value: number) => padding.top + ((max - value) / Math.max(1, max - min)) * plotHeight;
  const showTooltip = (event: MouseEvent<SVGElement>, point: PriceDistributionPoint) => {
    const container = event.currentTarget.ownerSVGElement?.parentElement;
    const rect = container?.getBoundingClientRect();
    setTooltip({
      point,
      x: rect ? event.clientX - rect.left + 12 : 16,
      y: rect ? event.clientY - rect.top + 12 : 16,
    });
  };

  return (
    <div className="plot-shell chart-shell" style={{ position: "relative" }}>
      <svg className="chart-svg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="주요 성분 10ml당 가격 분포" onMouseLeave={() => setTooltip(null)}>
        {[0, 0.25, 0.5, 0.75, 1].map((tick) => {
          const y = padding.top + tick * plotHeight;
          const value = Math.round(max - tick * (max - min));
          return (
            <g key={tick}>
              <line x1={padding.left} x2={width - padding.right} y1={y} y2={y} className="chart-grid-line" />
              <text x={padding.left - 10} y={y + 4} className="chart-axis-label" textAnchor="end">
                {formatNumber(value)}
              </text>
            </g>
          );
        })}
        {items.map((item, index) => {
          const pricePoints = getPricePoints(item, priceType).slice().sort((a, b) => a.value - b.value);
          const values = pricePoints.map((point) => point.value);
          const x = padding.left + (plotWidth / items.length) * (index + 0.5);
          const color = CHART_COLORS[index % CHART_COLORS.length];

          if (!values.length) {
            return (
              <g key={item.ingredient}>
                <text x={x} y={padding.top + plotHeight / 2} className="chart-axis-label" textAnchor="middle">
                  데이터 없음
                </text>
                <text x={x} y={height - 18} className="chart-axis-label" textAnchor="middle">
                  {item.ingredient}
                </text>
              </g>
            );
          }

          const localMin = values[0];
          const localMax = values[values.length - 1];
          const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
          const q1 = getQuantile(values, 0.25);
          const q3 = getQuantile(values, 0.75);
          const boxY = yFor(q3);
          const boxHeight = Math.max(8, yFor(q1) - boxY);
          const displayPoints = getDisplayPricePoints(pricePoints);
          const representativePoint = pricePoints[pricePoints.length - 1];

          return (
            <g key={item.ingredient}>
              {localMin === localMax ? (
                <ellipse
                  cx={x}
                  cy={yFor(mean)}
                  rx="28"
                  ry="9"
                  fill={color}
                  opacity="0.18"
                  stroke={color}
                  style={{ cursor: "help" }}
                  onMouseEnter={(event) => showTooltip(event, representativePoint)}
                  onMouseMove={(event) => showTooltip(event, representativePoint)}
                />
              ) : (
                <path
                  d={getViolinPath(values, x, yFor, 30)}
                  fill={color}
                  opacity="0.18"
                  stroke={color}
                  strokeWidth="1.5"
                  style={{ cursor: "help" }}
                  onMouseEnter={(event) => showTooltip(event, representativePoint)}
                  onMouseMove={(event) => showTooltip(event, representativePoint)}
                />
              )}
              <line x1={x} x2={x} y1={yFor(localMin)} y2={yFor(localMax)} stroke={color} strokeWidth="2.5" strokeLinecap="round" opacity="0.56" />
              <rect x={x - 10} y={boxY} width="20" height={boxHeight} rx="6" fill="#ffffff" opacity="0.82" stroke={color} strokeWidth="1.4" />
              <line x1={x - 20} x2={x + 20} y1={yFor(mean)} y2={yFor(mean)} stroke={color} strokeWidth="3" strokeLinecap="round" />
              {displayPoints.map((point, valueIndex) => (
                <g
                  key={`${item.ingredient}-${point.value}-${point.goodsNo || valueIndex}`}
                  onMouseEnter={(event) => showTooltip(event, point)}
                  onMouseMove={(event) => showTooltip(event, point)}
                  onMouseLeave={() => setTooltip(null)}
                  style={{ cursor: "help", outline: "none" }}
                >
                  <circle
                    cx={x + ((valueIndex * 19) % 17) - 8}
                    cy={yFor(point.value)}
                    r="7"
                    fill="transparent"
                  />
                  <circle
                    cx={x + ((valueIndex * 19) % 17) - 8}
                    cy={yFor(point.value)}
                    r="2.5"
                    fill={color}
                    opacity="0.58"
                  >
                    <title>{formatPriceTooltip(point, priceType)}</title>
                  </circle>
                </g>
              ))}
              <text x={x} y={padding.top - 7} className="chart-axis-label" textAnchor="middle">
                {values.length}개
              </text>
              <text x={x} y={height - 18} className="chart-axis-label" textAnchor="middle">
                {item.ingredient}
              </text>
            </g>
          );
        })}
      </svg>
      {tooltip ? (
        <div
          role="tooltip"
          style={{
            position: "absolute",
            left: tooltip.x,
            top: tooltip.y,
            maxWidth: 260,
            padding: "10px 12px",
            borderRadius: 10,
            border: "1px solid #d8e0ee",
            background: "#ffffff",
            boxShadow: "0 14px 30px rgba(15, 23, 42, .14)",
            color: "#263244",
            fontSize: 12,
            fontWeight: 800,
            lineHeight: 1.55,
            pointerEvents: "none",
            zIndex: 5,
            whiteSpace: "pre-line",
          }}
        >
          {formatPriceTooltip(tooltip.point, priceType)}
        </div>
      ) : null}
    </div>
  );
}

function MatrixLegend() {
  return (
    <div className="matrix-legend">
      {MATRIX_STATUS_KEYS.map((key) => (
        <div className="legend-pill" key={key}>
          <span className="legend-dot" style={{ background: STATUS_COLORS[key] }} />
          <span>{STATUS_LABELS[key]}</span>
        </div>
      ))}
    </div>
  );
}

type DemandSupplyTooltipState = {
  item: DemandSupplyItem;
  x: number;
  y: number;
};

function getDemandSupplyInterpretation(item: DemandSupplyItem) {
  const gap = item.gap ?? item.demand - item.supply;
  const gapDelta = item.gapDelta ?? 0;

  if (item.status === "growth") {
    return "수요와 공급이 모두 높아 이미 시장이 형성된 성장 성분입니다.";
  }
  if (item.status === "opportunity" || item.status === "shortage") {
    return gapDelta > 0
      ? "수요가 공급보다 높고 격차도 커져 기회 우선순위가 높은 성분입니다."
      : "수요는 높지만 공급이 상대적으로 낮아 기회가 있는 성분입니다.";
  }
  if (item.status === "oversupply") {
    return "공급은 높지만 수요가 낮아 공급 과잉 리스크를 점검해야 하는 성분입니다.";
  }
  return "수요와 공급 모두 낮아 추이를 지켜볼 관찰 성분입니다.";
}

function formatMatrixChange(value?: number) {
  if (!Number.isFinite(value)) return "-";
  const sign = Number(value) > 0 ? "+" : "";
  return `${sign}${Number(value).toFixed(1)}%`;
}

function formatMatrixNumber(value?: number) {
  if (!Number.isFinite(value)) return "-";
  return Number(value).toFixed(1);
}

function MatrixMotionGuide() {
  return (
    <div className="matrix-motion-guide" aria-label="수요 공급 매트릭스 이동 방향 설명">
      <span className="matrix-motion-text">
        옅은 작은 잔상 → 진한 큰 잔상 = 전주에서 현재로 이동한 흔적
      </span>
      <span className="matrix-motion-divider">·</span>
      <span className="matrix-motion-text">
        진한 버블 = 현재 위치
      </span>
    </div>
  );
}

function DemandSupplyTooltip({ tooltip }: { tooltip: DemandSupplyTooltipState }) {
  const { item } = tooltip;

  return (
    <div
      role="tooltip"
      className="matrix-tooltip"
      style={{ left: tooltip.x, top: tooltip.y }}
    >
      <div className="matrix-tooltip-title">{item.ingredient}</div>
      <div className="matrix-tooltip-grid">
        <span>영역</span>
        <strong>{STATUS_LABELS[item.status]}</strong>
        <span>현재 수요</span>
        <strong>{formatMatrixNumber(item.demand)}</strong>
        <span>전주 수요</span>
        <strong>{formatMatrixNumber(item.previousDemand)}</strong>
        <span>현재 공급</span>
        <strong>{formatMatrixNumber(item.supply)}</strong>
        <span>전주 공급</span>
        <strong>{formatMatrixNumber(item.previousSupply)}</strong>
        <span>수요 WoW</span>
        <strong className={(item.demandWow ?? item.growth) >= 0 ? "positive" : "negative"}>{formatMatrixChange(item.demandWow ?? item.growth)}</strong>
        <span>수요 MoM</span>
        <strong className={(item.demandMom ?? 0) >= 0 ? "positive" : "negative"}>{formatMatrixChange(item.demandMom)}</strong>
        <span>공급 WoW</span>
        <strong className={(item.supplyWow ?? 0) >= 0 ? "positive" : "negative"}>{formatMatrixChange(item.supplyWow)}</strong>
        <span>제품 수</span>
        <strong>{item.supplyCount ?? "-"}개</strong>
        <span>버블 크기</span>
        <strong>상대 규모 {Math.round(item.size)}</strong>
        <span>수요-공급 격차</span>
        <strong className={(item.gap ?? 0) >= 0 ? "positive" : "negative"}>{formatMatrixNumber(item.gap)}</strong>
        <span>격차 변화</span>
        <strong className={(item.gapDelta ?? 0) >= 0 ? "positive" : "negative"}>{formatMatrixNumber(item.gapDelta)}</strong>
      </div>
      <p>{getDemandSupplyInterpretation(item)} 버블 크기는 공급 제품 수를 기본으로, 현재 수요를 일부 반영한 상대적 중요도입니다.</p>
    </div>
  );
}

function DemandSupplyPlot({
  items,
  isLoading,
  error,
  threshold = DEFAULT_DEMAND_SUPPLY_MATRIX_CONFIG.threshold,
}: {
  items: DemandSupplyItem[];
  isLoading: boolean;
  error: string;
  threshold?: number;
}) {
  const [tooltip, setTooltip] = useState<DemandSupplyTooltipState | null>(null);
  const shellRef = useRef<HTMLDivElement | null>(null);
  const width = 720;
  const height = 420;
  const padding = { top: 34, right: 38, bottom: 48, left: 58 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const xFor = (value: number) => padding.left + (value / 100) * plotWidth;
  const yFor = (value: number) => padding.top + ((100 - value) / 100) * plotHeight;

  const clampTooltipPosition = (x: number, y: number) => {
    const rect = shellRef.current?.getBoundingClientRect();
    const maxX = Math.max(16, (rect?.width || 0) - 300);
    const maxY = Math.max(16, (rect?.height || 0) - 180);

    return {
      x: Math.min(Math.max(x, 12), maxX),
      y: Math.min(Math.max(y, 12), maxY),
    };
  };

  const showTooltipFromPointer = (item: DemandSupplyItem, event: MouseEvent<SVGElement>) => {
    const rect = shellRef.current?.getBoundingClientRect();
    if (!rect) return;
    const position = clampTooltipPosition(event.clientX - rect.left + 14, event.clientY - rect.top + 14);
    setTooltip({ item, ...position });
  };

  const showTooltipFromBubble = (item: DemandSupplyItem) => {
    const rect = shellRef.current?.getBoundingClientRect();
    const renderedWidth = rect?.width || width;
    const renderedHeight = rect?.height || height;
    const position = clampTooltipPosition(
      (xFor(item.supply) / width) * renderedWidth + 12,
      (yFor(item.demand) / height) * renderedHeight + 12,
    );
    setTooltip({ item, ...position });
  };

  if (!items.length) {
    return (
      <div className="plot-shell chart-shell">
        <div className="empty-state api-state">
          {error ? error : isLoading ? "수요-공급 데이터를 불러오는 중입니다." : NAVER_DEMAND_API_REQUIRED_MESSAGE}
        </div>
      </div>
    );
  }

  return (
    <div className="plot-shell chart-shell matrix-chart-shell" ref={shellRef}>
      <svg className="chart-svg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="수요 공급 매트릭스">
        <rect x={xFor(0)} y={yFor(100)} width={xFor(threshold) - xFor(0)} height={yFor(threshold) - yFor(100)} fill="rgba(63, 167, 181, .10)" />
        <rect x={xFor(threshold)} y={yFor(100)} width={xFor(100) - xFor(threshold)} height={yFor(threshold) - yFor(100)} fill="rgba(90, 170, 110, .11)" />
        <rect x={xFor(0)} y={yFor(threshold)} width={xFor(threshold) - xFor(0)} height={yFor(0) - yFor(threshold)} fill="rgba(123, 132, 147, .08)" />
        <rect x={xFor(threshold)} y={yFor(threshold)} width={xFor(100) - xFor(threshold)} height={yFor(0) - yFor(threshold)} fill="rgba(201, 122, 155, .10)" />
        {[0, 20, 40, 60, 80, 100].map((tick) => (
          <g key={`x-${tick}`}>
            <line x1={xFor(tick)} x2={xFor(tick)} y1={padding.top} y2={height - padding.bottom} className="chart-grid-line" />
            <text x={xFor(tick)} y={height - 20} className="chart-axis-label" textAnchor="middle">
              {tick}
            </text>
          </g>
        ))}
        {[0, 20, 40, 60, 80, 100].map((tick) => (
          <g key={`y-${tick}`}>
            <line x1={padding.left} x2={width - padding.right} y1={yFor(tick)} y2={yFor(tick)} className="chart-grid-line" />
            <text x={padding.left - 10} y={yFor(tick) + 4} className="chart-axis-label" textAnchor="end">
              {tick}
            </text>
          </g>
        ))}
        <line x1={xFor(threshold)} x2={xFor(threshold)} y1={padding.top} y2={height - padding.bottom} className="chart-threshold-line" />
        <line x1={padding.left} x2={width - padding.right} y1={yFor(threshold)} y2={yFor(threshold)} className="chart-threshold-line" />
        {items.map((item) => (
          typeof item.previousSupply === "number" && typeof item.previousDemand === "number"
            ? (() => {
              const startX = xFor(item.previousSupply || 0);
              const startY = yFor(item.previousDemand || 0);
              const endX = xFor(item.supply);
              const endY = yFor(item.demand);
              const radius = Math.max(10, item.size / 2);
              const movement = Math.hypot(endX - startX, endY - startY);
              const hasMovement = movement > 6;
              const trailSteps = movement > 42 ? 5 : movement > 24 ? 4 : 3;

              return hasMovement ? (
                <g key={`${item.ingredient}-trajectory`} className="matrix-trajectory" aria-hidden="true">
                  {Array.from({ length: trailSteps }).map((_, index) => {
                    const t = (index + 1) / (trailSteps + 1);
                    const cx = startX + (endX - startX) * t;
                    const cy = startY + (endY - startY) * t;
                    const trailRadius = Math.max(3, radius * (0.22 + t * 0.62));
                    const opacity = 0.12 + t * 0.24;

                    return (
                      <circle
                        key={`${item.ingredient}-trail-${index}`}
                        cx={cx}
                        cy={cy}
                        r={trailRadius}
                        className="matrix-trail-stamp"
                        style={{ fill: STATUS_COLORS[item.status], opacity }}
                      />
                    );
                  })}
                </g>
              ) : null;
            })()
            : null
        ))}
        {items.map((item) => {
          const bubbleX = xFor(item.supply);
          const bubbleY = yFor(item.demand);
          const radius = Math.max(10, item.size / 2);          return (
            <g
              key={item.ingredient}
              className="matrix-bubble"
              tabIndex={0}
              role="button"
              aria-label={`${item.ingredient} 수요 ${Math.round(item.demand)}, 공급 ${Math.round(item.supply)}, ${STATUS_LABELS[item.status]}`}
              onMouseEnter={(event) => showTooltipFromPointer(item, event)}
              onMouseMove={(event) => showTooltipFromPointer(item, event)}
              onMouseLeave={() => setTooltip(null)}
              onFocus={() => showTooltipFromBubble(item)}
              onBlur={() => setTooltip(null)}
            >
              <circle
                cx={bubbleX}
                cy={bubbleY}
                r={radius}
                fill={STATUS_COLORS[item.status]}
                opacity="0.9"
                stroke="#ffffff"
                strokeWidth="2"
              />
              <text x={bubbleX} y={bubbleY - radius - 10} className="matrix-point-label" textAnchor="middle">
                {item.ingredient}
              </text>
            </g>
          );
        })}
        <text x={width / 2} y={height - 5} className="chart-axis-title" textAnchor="middle">공급 지수</text>
        <text x="16" y={height / 2} className="chart-axis-title" textAnchor="middle" transform={`rotate(-90 16 ${height / 2})`}>수요 지수</text>
      </svg>
      {tooltip ? <DemandSupplyTooltip tooltip={tooltip} /> : null}
    </div>
  );
}

function SearchTrendPlot({
  trend,
  isLoading,
  error,
}: {
  trend: DashboardData["page2"]["searchTrend"];
  isLoading: boolean;
  error: string;
}) {
  if (!trend.dates.length || !trend.series.length) {
    return (
      <div className="plot-shell js-plot">
        <div className="empty-state api-state">
          {error ? `FastAPI 오류: ${error}` : isLoading ? "Naver DataLab API에서 검색 관심도 추이를 불러오는 중입니다." : "표시할 검색 관심도 데이터가 없습니다."}
        </div>
      </div>
    );
  }

  const width = 720;
  const height = 360;
  const padding = { top: 28, right: 28, bottom: 64, left: 58 };
  const values = trend.series.flatMap((item) => item.values);
  const min = Math.max(0, Math.floor(Math.min(...values) - 5));
  const max = Math.min(105, Math.ceil(Math.max(...values) + 5));
  const xFor = (index: number) => padding.left + (index / Math.max(1, trend.dates.length - 1)) * (width - padding.left - padding.right);
  const yFor = (value: number) => padding.top + ((max - value) / Math.max(1, max - min)) * (height - padding.top - padding.bottom);

  return (
    <div className="plot-shell chart-shell">
      <svg className="chart-svg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="성분 검색 관심도 추이">
        {trend.series.map((series) => {
          const color = series.color || DATALAB_TREND_COLORS[series.ingredient] || "#6B7280";
          const points = series.values.map((value, index) => `${xFor(index)},${yFor(value)}`).join(" ");
          return (
            <g key={series.ingredient}>
              <polyline points={points} fill="none" stroke={color} strokeWidth="3" />
              {series.values.map((value, index) => (
                <circle key={`${series.ingredient}-${index}`} cx={xFor(index)} cy={yFor(value)} r="4" fill={color} />
              ))}
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function MarketProductPlot({ products }: { products: MarketProduct[] }) {
  if (!products.length) {
    return <div className="plot-shell compact js-plot"><div className="empty-state api-state">전처리 제품 데이터를 불러오는 중입니다.</div></div>;
  }

  const rows = products.slice(0, 6);
  const maxCount = Math.max(...rows.map((item) => item.product_count), 1);

  return (
    <div className="plot-shell compact bar-chart">
      {rows.map((item) => {
        const growth = getGrowthDisplay(getProductGrowth(item));
        return (
          <div className="bar-chart-row" key={item.ingredient_key}>
            <div className="bar-chart-label">
              <strong>{item.ingredient_label}</strong>
              <span style={{ color: growth.color }}>{growth.text}</span>
            </div>
            <div className="bar-track">
              <span
                className="bar-fill"
                style={{
                  width: `${Math.max(8, (item.product_count / maxCount) * 100)}%`,
                  background: DATALAB_TREND_COLORS[item.ingredient_label] || "#2CA6A4",
                }}
              />
            </div>
            <strong className="bar-value">{formatNumber(item.product_count)}개</strong>
          </div>
        );
      })}
    </div>
  );
}

function ConcernHeatmap({
  metrics,
  table,
  isLoading,
  error,
}: {
  metrics: ConcernMetric[];
  table: DashboardData["page2"]["concernTable"];
  isLoading: boolean;
  error: string;
}) {
  if (!table.length) {
    return (
      <div className="empty-state api-state">
        {error ? `FastAPI 오류: ${error}` : isLoading ? "Naver DataLab API에서 연령대별 피부 고민 데이터를 불러오는 중입니다." : "표시할 피부 고민 데이터가 없습니다."}
      </div>
    );
  }

  const values = table.flatMap((row) => metrics.map((metric) => Number(row[metric.key] ?? row[metric.legacyKey || ""] ?? 0)));
  const maxValue = Math.max(...values, 1);
  const style = { "--heatmap-columns": metrics.length } as CSSProperties;

  return (
    <>
      <div className="heatmap-grid" style={style}>
        <div className="heatmap-head">연령대</div>
        {metrics.map((metric) => (
          <div className="heatmap-head" key={metric.key}>{metric.label}</div>
        ))}
        {table.map((row) => (
          <Fragment key={row.age}>
            <div className="heatmap-age">{row.age}</div>
            {metrics.map((metric) => {
              const value = Number(row[metric.key] ?? row[metric.legacyKey || ""] ?? 0);
              const alpha = 0.1 + Math.max(0.12, value / maxValue) * 0.72;
              return (
                <div className="heatmap-cell" style={{ background: `rgba(9, 95, 233, ${alpha.toFixed(3)})` }} key={`${row.age}-${metric.key}`}>
                  <strong>{formatNumber(value)}</strong>
                </div>
              );
            })}
          </Fragment>
        ))}
      </div>
      <div className="heatmap-legend">
        <span>낮음</span>
        <div />
        <span>높음</span>
      </div>
    </>
  );
}

function SentimentDonut({ page }: { page: ReviewIngredient }) {
  const { positive, neutral, negative } = page.sentiment;
  const positiveEnd = positive;
  const neutralEnd = positive + neutral;
  const background = `conic-gradient(#2BB7A9 0 ${positiveEnd}%, #94A3B8 ${positiveEnd}% ${neutralEnd}%, #F28B82 ${neutralEnd}% 100%)`;

  return (
    <div className="plot-shell compact sentiment-plot">
      <div className="donut-chart" style={{ background }}>
        <div>
          <span>긍정</span>
          <strong>{positive}%</strong>
        </div>
      </div>
      <div className="sentiment-legend">
        <span><i style={{ background: "#2BB7A9" }} />긍정 {positive}%</span>
        <span><i style={{ background: "#94A3B8" }} />중립 {neutral}%</span>
        <span><i style={{ background: "#F28B82" }} />부정 {negative}%</span>
      </div>
    </div>
  );
}

function KeywordPanel({ title, keywords, tone }: { title: string; keywords: Keyword[]; tone: "positive" | "negative" }) {
  return (
    <div className={`keyword-panel ${tone}`}>
      <div className="keyword-panel-title">{title}</div>
      {keywords.map((keyword) => (
        <div className="keyword-row" key={keyword.label}>
          <span>{keyword.label}</span>
          <strong>{Number(keyword.score || 0).toFixed(1)}%</strong>
        </div>
      ))}
    </div>
  );
}

function AlertDetail({ alert }: { alert: AlertItem }) {
  return (
    <div className="alert-detail">
      <div className="detail-title-row">
        <div>
          <span className="detail-type">{alert.type}</span>
          <h2>{alert.title}</h2>
        </div>
        <span className={`severity-badge ${getSeverityClass(alert.severity)}`}>{alert.severity}</span>
      </div>
      <p className="detail-description">{alert.description}</p>

      <div className="detail-meta-grid">
        <div>
          <span>감지 시점</span>
          <strong>{alert.time}</strong>
        </div>
        <div>
          <span>대표 지표</span>
          <strong>{alert.metric}</strong>
        </div>
      </div>

      <div className="detail-section">
        <h3>감지 이유</h3>
        <ul>{alert.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
      </div>

      <div className="detail-section">
        <h3>관련 지표 요약</h3>
        <div className="detail-metrics">
          {Object.entries(alert.metrics).map(([label, value]) => (
            <div className="metric-pill" key={label}>
              <span>{label}</span>
              <strong>{value}</strong>
            </div>
          ))}
        </div>
      </div>

      <div className="detail-section">
        <h3>권장 액션</h3>
        <ul>{alert.actions.map((action) => <li key={action}>{action}</li>)}</ul>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData>(INITIAL_DASHBOARD_DATA);
  const [loadState, setLoadState] = useState<DataLoadState>({
    dashboardSignals: "loading",
    searchTrend: "loading",
    priceDistribution: "loading",
    demandSupplyMatrix: "loading",
    page1Insights: "loading",
    dashboardSignalsError: "",
    searchTrendError: "",
    priceDistributionError: "",
    demandSupplyMatrixError: "",
    page1InsightsError: "",
  });
  const [activeTab, setActiveTab] = useState<TabId>("A");
  const [activePriceType, setActivePriceType] = useState<PriceType>("sale");
  const [activeSearchPeriodKey, setActiveSearchPeriodKey] = useState("snapshot");
  const [activeReviewIngredientKey, setActiveReviewIngredientKey] = useState(dashboardData.page3.selectedIngredientKey);
  const [activeAlertId, setActiveAlertId] = useState(dashboardData.page4.alerts[0]?.id || "");
  const [agentPrompt, setAgentPrompt] = useState("");
  const didRequestInitialData = useRef(false);
  const lastInsightRequestKey = useRef("");

  async function loadDashboardSignals() {
    setLoadState((current) => ({ ...current, dashboardSignals: "loading", dashboardSignalsError: "" }));
    try {
      const payload = await fetchCurrentApiDashboardSignals();
      const hasWeeklyDatalabData = Boolean(payload.page1?.functionRisers?.length && payload.page1?.ingredientPopularity?.length);
      setData((current) => mergeDashboardSignals(current, payload));
      setLoadState((current) => ({
        ...current,
        dashboardSignals: hasWeeklyDatalabData ? "ready" : "error",
        dashboardSignalsError: hasWeeklyDatalabData ? "" : DATALAB_WEEKLY_API_REQUIRED_MESSAGE,
      }));
    } catch (error) {
      console.error("FastAPI 대시보드 신호 조회 실패", error);
      setLoadState((current) => ({
        ...current,
        dashboardSignals: "error",
        dashboardSignalsError: error instanceof Error ? error.message : String(error),
      }));
    }
  }

  async function loadIngredientTrend(periodKey: string) {
    setLoadState((current) => ({ ...current, searchTrend: "loading", searchTrendError: "" }));
    try {
      const payload = await fetchDatalabJson<DashboardSummaryResponse>("/dashboard/summary");
      const trendPayload = payload.page2?.searchTrend ? payload.page2 : {};

      if (trendPayload.searchTrend) {
        setData((current) => mergeIngredientTrend(current, trendPayload));
      }
      setLoadState((current) => ({ ...current, searchTrend: "ready", searchTrendError: "" }));
    } catch (error) {
      console.error("FastAPI 검색 추이 조회 실패", { periodKey, error });
      setLoadState((current) => ({
        ...current,
        searchTrend: "error",
        searchTrendError: error instanceof Error ? error.message : String(error),
      }));
    }
  }

  async function loadPriceDistribution() {
    setLoadState((current) => ({ ...current, priceDistribution: "loading", priceDistributionError: "" }));
    try {
      const priceDistribution = await fetchPriceDistributionFromSupabase();
      setData((current) => mergePriceDistribution(current, priceDistribution));
      setLoadState((current) => ({ ...current, priceDistribution: "ready", priceDistributionError: "" }));
    } catch (error) {
      setData((current) => mergePriceDistribution(current, getEmptyPriceDistribution()));
      setLoadState((current) => ({
        ...current,
        priceDistribution: "error",
        priceDistributionError: error instanceof Error ? error.message : String(error),
      }));
    }
  }

  async function loadDemandSupplyMatrix() {
    setLoadState((current) => ({ ...current, demandSupplyMatrix: "loading", demandSupplyMatrixError: "" }));
    const result = await fetchDemandSupplyMatrixFromSupabase(DEFAULT_DEMAND_SUPPLY_MATRIX_CONFIG);
    setData((current) => mergeDemandSupplyMatrix(current, result.items));
    setLoadState((current) => ({
      ...current,
      demandSupplyMatrix: result.isUnavailable ? "error" : "ready",
      demandSupplyMatrixError: result.error,
    }));
  }

  async function loadPage1Insights(payload: ReturnType<typeof buildPage1InsightPayload>) {
    setLoadState((current) => ({ ...current, page1Insights: "loading", page1InsightsError: "" }));

    try {
      const response = await fetch("/api/dashboard/page1-insights", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = await response.json().catch(() => ({}));

      if (!response.ok || !Array.isArray(result.insights)) {
        throw new Error(typeof result.error === "string" ? result.error : INSIGHT_GENERATION_ERROR_MESSAGE);
      }

      setData((current) => mergePage1Insights(current, result.insights.map((item: unknown) => String(item)).filter(Boolean)));
      setLoadState((current) => ({ ...current, page1Insights: "ready", page1InsightsError: "" }));
    } catch (error) {
      console.error("OpenAI Page 1 인사이트 요약 생성 실패", error);
      setData((current) => mergePage1Insights(current, []));
      setLoadState((current) => ({
        ...current,
        page1Insights: "error",
        page1InsightsError: INSIGHT_GENERATION_ERROR_MESSAGE,
      }));
    }
  }

  async function refreshDatalabData(periodKey = activeSearchPeriodKey) {
    await loadDashboardSignals();
    await loadIngredientTrend(periodKey);
  }

  useEffect(() => {
    if (didRequestInitialData.current) return;
    didRequestInitialData.current = true;
    void refreshDatalabData("snapshot");
    void loadPriceDistribution();
    void loadDemandSupplyMatrix();
  }, []);

  useEffect(() => {
    const stillLoading = loadState.dashboardSignals === "loading" ||
      loadState.priceDistribution === "loading" ||
      loadState.demandSupplyMatrix === "loading";

    if (stillLoading) return;

    const payload = buildPage1InsightPayload(data, loadState);
    const requestKey = JSON.stringify(payload);
    if (requestKey === lastInsightRequestKey.current) return;

    lastInsightRequestKey.current = requestKey;
    void loadPage1Insights(payload);
  }, [
    data.page1.functionRisers,
    data.page1.ingredientPopularity,
    data.page1.priceDistribution,
    data.page1.demandSupplyMatrix,
    loadState.dashboardSignals,
    loadState.dashboardSignalsError,
    loadState.priceDistribution,
    loadState.priceDistributionError,
    loadState.demandSupplyMatrix,
    loadState.demandSupplyMatrixError,
  ]);

  const marketProducts = useMemo(
    () => data.page2.marketProducts.slice().sort((a, b) => b.product_count - a.product_count),
    [data.page2.marketProducts],
  );
  const activePeriod = SEARCH_PERIOD_OPTIONS.find((option) => option.key === activeSearchPeriodKey) || SEARCH_PERIOD_OPTIONS[0];
  const leadSeries = data.page2.searchTrend.series[0];
  const leadIngredient = leadSeries?.ingredient || data.page2.selectedIngredient || "-";
  const selectedGrowthRate = data.page2.selectedSummary.growthRate as number | undefined;
  const leadGrowth = calculateSeriesGrowth(leadSeries, Number(selectedGrowthRate || 0));
  const leadProduct = marketProducts.find((item) => item.ingredient_label === leadIngredient);
  const marketStatus = leadProduct ? getMarketReflectionStatus(leadGrowth, leadProduct.product_count) : "공급 데이터 연결 중";
  const reviewPage = data.page3.byIngredient[activeReviewIngredientKey] || data.page3;
  const activeAlert = data.page4.alerts.find((alert) => alert.id === activeAlertId) || data.page4.alerts[0];
  const isDashboardLoading = loadState.dashboardSignals === "loading";
  const isTrendLoading = loadState.searchTrend === "loading";
  const isPriceLoading = loadState.priceDistribution === "loading";
  const isDemandSupplyLoading = loadState.demandSupplyMatrix === "loading";
  const isPage1InsightsLoading = loadState.page1Insights === "loading";
  const statusCard = (
    <DataStatusCard
      meta={data.meta}
      isLoading={isDashboardLoading || isTrendLoading}
      error={loadState.dashboardSignalsError || loadState.searchTrendError}
      onRefresh={() => {
        void refreshDatalabData();
      }}
    />
  );

  if (!activeAlert) return null;

  const positiveKeywords = reviewPage.positiveKeywords.length
    ? reviewPage.positiveKeywords
    : reviewPage.keywords.filter((keyword) => keyword.tone === "positive");
  const negativeKeywords = reviewPage.negativeKeywords.length
    ? reviewPage.negativeKeywords
    : reviewPage.keywords.filter((keyword) => keyword.tone === "negative");

  return (
    <div className="dash">
      <nav className="sidebar">
        <div className="sidebar-logo">
          <div className="logo-emoji">🧴</div>
          <div className="logo-title">BeautyMD Insight</div>
          <div className="logo-sub">성분 인텔리전스 v0.3</div>
        </div>
        <div className="nav-section">
          <div className="nav-label">대시보드</div>
          {NAV_ITEMS.map((item) => (
            <button
              className={`nav-item ${activeTab === item.id ? "active" : ""}`}
              key={item.id}
              type="button"
              onClick={() => setActiveTab(item.id)}
            >
              <span className="nav-icon">{item.index}</span>
              {item.label}
              {item.badge ? <span className="nav-badge">{item.badge}</span> : null}
            </button>
          ))}
        </div>
        <div className="sidebar-footer">떡잎마을 방범대 · {data.meta.dataRange}</div>
      </nav>

      <main className="main">
        <section className="content">
          <article className={`panel ${activeTab === "A" ? "active" : ""}`}>
            <PageHeader
              badge="Page 1"
              title="1. 성분 시장 스냅샷"
              description="수요·공급·가격·검색 데이터를 기반으로 지금 주목해야 할 성분 시장 구조를 한눈에 파악합니다."
              actions={<span className="tag tag-blue">앰플 카테고리</span>}
              statusCard={statusCard}
            />
            <SummaryStrip summary={data.page1Summary} />
            <div className="dashboard-grid market-grid">
              <section className="card rank-card">
                <div className="card-header">
                  <span>기능(급상승 순위) TOP 5</span>
                  <span className="card-meta">네이버 검색 관심도 기준</span>
                </div>
                <RankList
                  items={data.page1.functionRisers}
                  valueLabel="전주 대비 증감률"
                  barMetric="growth"
                  valueMetric="growth"
                  isLoading={isDashboardLoading}
                  error={loadState.dashboardSignalsError}
                />
              </section>

              <section className="card rank-card">
                <div className="card-header">
                  <span>성분 인기 순위 TOP 5</span>
                  <span className="card-meta">네이버 검색 관심도 기준</span>
                </div>
                <RankList
                  items={data.page1.ingredientPopularity}
                  valueLabel="전주 대비 증감률"
                  barMetric="searchIndex"
                  valueMetric="growth"
                  isLoading={isDashboardLoading}
                  error={loadState.dashboardSignalsError}
                />
              </section>

              <section className="card price-card">
                <div className="card-header">
                  <span>주요 성분 10ml당 가격 분포</span>
                  <div className="price-toggle-control" aria-label="가격 기준 선택">
                    <button className={`period-button ${activePriceType === "sale" ? "active" : ""}`} type="button" onClick={() => setActivePriceType("sale")}>판매가</button>
                    <button className={`period-button ${activePriceType === "list" ? "active" : ""}`} type="button" onClick={() => setActivePriceType("list")}>정가</button>
                    <span className="card-meta">{isPriceLoading ? "Supabase 연결 중" : loadState.priceDistributionError ? "Supabase 오류" : "10ml 기준"}</span>
                  </div>
                </div>
                <PriceDistributionPlot
                  items={data.page1.priceDistribution}
                  priceType={activePriceType}
                  isLoading={isPriceLoading}
                  error={loadState.priceDistributionError}
                />
              </section>

              <section className="card market-matrix-card">
                <div className="card-header">
                  <span>수요-공급 매트릭스</span>
                  <span className="card-meta">{isDemandSupplyLoading ? "Supabase 원천 데이터 연결 중" : loadState.demandSupplyMatrixError ? "수요 API 필요" : "원천 데이터 계산"}</span>
                </div>
                <div className="status-note">공급은 성분 포함 상품 수, 수요는 네이버 데이터랩 검색 관심도를 0~100 지수로 환산합니다.</div>
                {loadState.demandSupplyMatrixError ? (
                  <div className="empty-state">{loadState.demandSupplyMatrixError}</div>
                ) : null}
                <MatrixLegend />
                <MatrixMotionGuide />
                <div className="matrix-helper-note">버블 크기 = 성분별 공급 제품 수를 기본으로, 현재 수요 지수를 일부 반영한 상대적 규모입니다.</div>
                <DemandSupplyPlot
                  items={data.page1.demandSupplyMatrix}
                  isLoading={isDemandSupplyLoading}
                  error={loadState.demandSupplyMatrixError}
                  threshold={DEFAULT_DEMAND_SUPPLY_MATRIX_CONFIG.threshold}
                />
              </section>

              <section className="card insight-card market-insight-card">
                <div className="card-header">핵심 인사이트 요약</div>
                <InsightList
                  items={data.page1.insights}
                  fallback={isPage1InsightsLoading ? "인사이트 요약을 생성 중입니다." : loadState.page1InsightsError || INSIGHT_GENERATION_ERROR_MESSAGE}
                />
              </section>
            </div>
          </article>

          <article className={`panel ${activeTab === "B" ? "active" : ""}`}>
            <PageHeader
              badge="Page 2"
              title="2. 검색 트렌드 분석"
              description="성분 검색 관심도 변화가 시장 제품 수와 연령대별 피부 고민 맥락에 어떻게 연결되는지 분석합니다."
              statusCard={statusCard}
              actions={(
                <>
                  <div className="control-chip">
                    <span>기간 선택</span>
                    <strong>{data.page2.periodLabel}</strong>
                  </div>
                  <div className="control-chip muted">
                    <span>성분 선택</span>
                    <strong>{MAIN_INGREDIENTS.length}개 선택됨</strong>
                  </div>
                </>
              )}
            />

            <div className="dashboard-grid search-grid">
              <section className="card trend-card">
                <div className="card-header">
                  <span>성분 검색 관심도 추이</span>
                  <span className="card-meta">Naver DataLab ratio</span>
                </div>
                <div className="period-control-row" aria-label="검색 관심도 기간 선택">
                  {SEARCH_PERIOD_OPTIONS.map((option) => (
                    <button
                      className={`period-button ${option.key === activeSearchPeriodKey ? "active" : ""}`}
                      key={option.key}
                      type="button"
                      onClick={() => {
                        setActiveSearchPeriodKey(option.key);
                        void loadIngredientTrend(option.key);
                      }}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
                <div className="trend-badges">
                  {[
                    `${leadIngredient} 시작일 대비 ${formatPct(leadGrowth)}`,
                    `현재 보기 ${activePeriod.label}`,
                    leadProduct ? `제품 수 ${formatNumber(leadProduct.product_count)}개` : "제품 수 연결 중",
                    marketStatus,
                  ].map((label, index) => (
                    <span className={`trend-badge ${index === 0 ? "primary" : ""}`} key={label}>{label}</span>
                  ))}
                </div>
                <SearchTrendPlot trend={data.page2.searchTrend} isLoading={isTrendLoading} error={loadState.searchTrendError} />
              </section>

              <section className="card market-products-card">
                <div className="card-header">
                  <span>성분별 시장 제품 수 현황</span>
                  <span className="card-meta">전처리 리테일 데이터 기준</span>
                </div>
                <p className="card-helper">검색 관심도와 함께 시장 공급 규모를 비교해 볼 수 있는 보조 지표입니다.</p>
                <div className="product-data-note">서버의 전처리 성분 통계에서 불러옵니다.</div>
                <MarketProductPlot products={marketProducts} />
              </section>

              <section className="card concern-card">
                <div className="card-header">
                  <span>연령대별 피부 고민 집중도</span>
                  <span className="card-meta">heatmap</span>
                </div>
                <p className="card-helper">주름/탄력, 잡티/톤, 트러블/진정, 건조/장벽, 모공/피지 키워드 집중도로 타겟 맥락을 해석합니다.</p>
                <div className="heatmap-wrap">
                  <ConcernHeatmap
                    metrics={data.page2.concernMetrics}
                    table={data.page2.concernTable}
                    isLoading={isDashboardLoading}
                    error={loadState.dashboardSignalsError}
                  />
                </div>
              </section>

              <section className="card search-insight-card">
                <div className="card-header">
                  <span>검색 트렌드 인사이트</span>
                  <span className="card-meta">summary</span>
                </div>
                <p className="card-helper">검색 관심도, 제품 수, 피부 고민 집중도를 함께 읽어 핵심 해석을 요약합니다.</p>
                <InsightList
                  items={data.page2.insights}
                  fallback={loadState.dashboardSignalsError ? `FastAPI 오류: ${loadState.dashboardSignalsError}` : "Naver DataLab API에서 검색 트렌드 인사이트를 불러오는 중입니다."}
                />
              </section>
            </div>
          </article>

          <article className={`panel ${activeTab === "C" ? "active" : ""}`}>
            <PageHeader
              badge="Page 3"
              title="3. 소비자 리뷰 분석"
              description="성분별 소비자 리뷰를 분석하여 감정, 의향과 타깃 기회를 파악합니다."
              statusCard={statusCard}
              actions={(
                <>
                  <div className="control-chip">
                    <span>성분 선택</span>
                    <select
                      className="review-ingredient-select"
                      value={activeReviewIngredientKey}
                      onChange={(event) => setActiveReviewIngredientKey(event.target.value)}
                      aria-label="리뷰 분석 성분 선택"
                    >
                      {data.page3.ingredientOptions.map((option) => (
                        <option value={option.key} key={option.key}>{option.label}</option>
                      ))}
                    </select>
                  </div>
                  <div className="control-chip feature-control">
                    <span>주요 기능</span>
                    <div className="chip-group">
                      {reviewPage.functionChips.map((chip) => <span className="feature-chip" key={chip}>{chip}</span>)}
                    </div>
                  </div>
                  <div className="control-chip muted">
                    <span>기간</span>
                    <strong>2025.04.30 ~ 2025.05.05</strong>
                  </div>
                </>
              )}
            />

            <div className="dashboard-grid review-grid">
              <section className="card sentiment-card">
                <div className="card-header">리뷰 감정 분석</div>
                <SentimentDonut page={reviewPage} />
              </section>

              <section className="card keyword-card">
                <div className="card-header">핵심 키워드</div>
                <div className="keyword-cloud">
                  <KeywordPanel title="긍정 키워드 TOP 5" keywords={positiveKeywords} tone="positive" />
                  <KeywordPanel title="부정 키워드 TOP 5" keywords={negativeKeywords} tone="negative" />
                </div>
              </section>

              <section className="card product-card">
                <div className="card-header">리뷰 반응 상위 제품 TOP 3</div>
                <div className="product-list">
                  {reviewPage.brandProducts.map((item) => (
                    <div className="product-row" key={`${item.brand}-${item.product}`}>
                      <div className="product-rank">{formatNumber(item.rank)}</div>
                      <div>
                        <span>{item.brand}</span>
                        <strong>{item.product}</strong>
                        <p>{item.issue}</p>
                      </div>
                      <div className="product-stat">
                        <span>리뷰 수</span>
                        <strong>{formatNumber(item.reviewCount)}</strong>
                      </div>
                      <div className="product-stat">
                        <span>평점</span>
                        <strong>{Number(item.rating || 0).toFixed(1)}</strong>
                      </div>
                    </div>
                  ))}
                </div>
              </section>

              <section className="card skin-table-card">
                <div className="card-header">피부 타입별 감정 비율 & 주요 이슈 요약</div>
                <div className="table-wrap">
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
                      {reviewPage.skinTypeSentiment.map((row) => (
                        <tr key={row.type}>
                          <td>{row.type}</td>
                          <td>{row.positive}%</td>
                          <td>{row.neutral}%</td>
                          <td>{row.negative}%</td>
                          <td>{row.issue}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              <section className="card review-insight-card">
                <div className="card-header">기회 인사이트</div>
                <InsightList items={reviewPage.opportunities} />
              </section>
            </div>
          </article>

          <article className={`panel ${activeTab === "D" ? "active" : ""}`}>
            <div className="compact-page-layout alert-page-layout">
              <PageHeader
                badge="Page 4"
                title="4. 경보"
                description="시장 변화를 실시간 또는 주간 기준으로 감지하여 중요한 이슈를 알립니다."
                statusCard={statusCard}
                compact
              />

              <div className="summary-strip alert-summary">
                {[
                  { label: "급등 성분", value: `${data.page4.summary.spikeCount || 0}건`, tone: "up" },
                  { label: "공급 과열", value: `${data.page4.summary.oversupplyCount || 0}건`, tone: "warn" },
                  { label: "부정 리뷰 증가", value: `${data.page4.summary.negativeReviewCount || 0}건`, tone: "down" },
                ].map((item) => (
                  <div className={`summary-chip ${item.tone}`} key={item.label}>
                    <span>{item.label}</span>
                    <strong>{item.value}</strong>
                  </div>
                ))}
              </div>

              <div className="alert-main-grid">
                <section className="card alert-list-card">
                  <div className="card-header">
                    <span>실시간 경보 리스트</span>
                    <span className="card-meta">2025.04.30 ~ 2025.05.05 기준</span>
                  </div>
                  <div className="alert-list">
                    {data.page4.alerts.map((alert) => (
                      <button
                        className={`alert-item ${getSeverityClass(alert.severity)} ${alert.id === activeAlert.id ? "active" : ""}`}
                        key={alert.id}
                        type="button"
                        onClick={() => setActiveAlertId(alert.id)}
                      >
                        <span className="alert-marker">{alert.type}</span>
                        <span className="alert-body">
                          <span className="alert-title-row">
                            <strong>{alert.title}</strong>
                            <span>{alert.time}</span>
                          </span>
                          <p>{alert.description}</p>
                        </span>
                        <span className="alert-metric">{alert.metric}</span>
                      </button>
                    ))}
                  </div>
                </section>

                <aside className="card alert-detail-card">
                  <div className="card-header">경보 상세</div>
                  <AlertDetail alert={activeAlert} />
                </aside>
              </div>
            </div>
          </article>

          <article className={`panel ${activeTab === "E" ? "active" : ""}`}>
            <div className="compact-page-layout agent-page-layout">
              <PageHeader
                badge="Page 5"
                title="5. AI Agent"
                description="앞선 분석 결과를 바탕으로 MD가 바로 활용할 수 있는 전략 초안을 제안합니다."
                statusCard={statusCard}
                compact
              />

              <div className="agent-main-grid">
                <section className="agent-left-column">
                  <div className="agent-shell">
                    <div className="agent-input-card">
                      <label htmlFor="agentPrompt">무엇을 도와드릴까요?</label>
                      <p className="agent-input-help">이번 주 성분 신호와 리뷰 이슈를 바탕으로 바로 실행할 전략을 물어보세요.</p>
                      <div className="agent-input-row">
                        <input
                          id="agentPrompt"
                          type="text"
                          placeholder={data.page5.promptPlaceholder}
                          value={agentPrompt}
                          onChange={(event) => setAgentPrompt(event.target.value)}
                        />
                        <button
                          className="btn btn-primary agent-send-button"
                          type="button"
                          aria-label="전략 제안 받기"
                          onClick={() => window.alert("AI Agent 전략 제안 요청")}
                        >
                          ➤
                        </button>
                      </div>
                    </div>
                  </div>

                  <section className="card">
                    <div className="card-header">
                      <span>AI 추천 인사이트</span>
                      <span className="card-meta">2025.04.30 ~ 2025.05.05 데이터 기준</span>
                    </div>
                    <div className="recommendation-grid">
                      {data.page5.insights.map((item) => (
                        <article className="recommendation-card" key={item.id}>
                          <div className="recommendation-top">
                            <strong>{item.title}</strong>
                            <span>{item.level}</span>
                          </div>
                          <p className="recommendation-overview">{item.summary}</p>
                          <div className="recommendation-details">
                            <div className="action-box">
                              <span>근거 데이터</span>
                              <strong>{item.evidence}</strong>
                            </div>
                            <div className="action-box">
                              <span>추천 전략</span>
                              <strong>{item.strategy}</strong>
                            </div>
                          </div>
                          <button className="btn btn-outline strategy-button" type="button">전략 상세 보기</button>
                        </article>
                      ))}
                    </div>
                  </section>
                </section>

                <aside className="agent-side-column">
                  <section className="card">
                    <div className="card-header">추천 질문</div>
                    <div className="suggestion-list">
                      {data.page5.suggestions.map((suggestion) => (
                        <button className="question-chip" type="button" key={suggestion} onClick={() => setAgentPrompt(suggestion)}>
                          {suggestion}
                        </button>
                      ))}
                    </div>
                  </section>

                  <section className="card target-strategy-card">
                    <div className="card-header">타겟 전략 카드</div>
                    <div className="target-strategy">
                      <h2>{data.page5.targetStrategy.title}</h2>
                      <div className="strategy-block">
                        <span>부정 포인트</span>
                        <div className="strategy-tags">
                          {data.page5.targetStrategy.issues.map((item) => <em key={item}>{item}</em>)}
                        </div>
                      </div>
                      <div className="strategy-block">
                        <span>제안 방향</span>
                        <ul>{data.page5.targetStrategy.directions.map((item) => <li key={item}>{item}</li>)}</ul>
                      </div>
                      <div className="strategy-block">
                        <span>추천 액션</span>
                        <ul>{data.page5.targetStrategy.actions.map((item) => <li key={item}>{item}</li>)}</ul>
                      </div>
                    </div>
                  </section>
                </aside>
              </div>
            </div>
          </article>
        </section>
      </main>
    </div>
  );
}
