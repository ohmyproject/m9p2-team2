import { NextResponse } from "next/server";
import {
  AGE_GROUPS,
  ANCHOR_GROUP,
  CONCERN_SIGNAL_GROUPS,
  FUNCTION_SIGNAL_GROUPS,
  PAGE2_MAIN_INGREDIENT_GROUPS,
  buildIngredientKeywordGroups,
  type NaverDatalabKeywordGroup,
} from "@/lib/naver-datalab-groups";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type DatalabPoint = {
  period?: string;
  ratio?: number;
};

type DatalabResult = {
  title?: string;
  data?: DatalabPoint[];
};

type DatalabResponse = {
  results?: DatalabResult[];
};

type WeeklyInterestRow = {
  key: string;
  label: string;
  currentWeekIndex: number;
  previousWeekIndex: number;
  growth: number;
  searchIndex: number;
};

const NAVER_DATALAB_URL = "https://openapi.naver.com/v1/datalab/search";
const KEYWORD_GROUPS_PER_REQUEST = 4;
const KEYWORDS_PER_GROUP = Number(process.env.NAVER_DATALAB_KEYWORDS_PER_GROUP || 8);

export async function GET(request: Request) {
  try {
    const clientId = process.env.NAVER_CLIENT_ID;
    const clientSecret = process.env.NAVER_CLIENT_SECRET;

    if (!clientId || !clientSecret) {
      return NextResponse.json(
        { message: "NAVER_CLIENT_ID 또는 NAVER_CLIENT_SECRET 서버 환경변수가 필요합니다." },
        { status: 500 },
      );
    }

    const url = new URL(request.url);
    const scope = url.searchParams.get("scope") || "page1";

    if (scope === "page2") {
      const periodKey = url.searchParams.get("period") || "snapshot";
      const { startDate, endDate, label } = getPeriodRange(periodKey);
      const [searchTrend, concernPayload] = await Promise.all([
        fetchTrendSeries(PAGE2_MAIN_INGREDIENT_GROUPS, startDate, endDate, clientId, clientSecret),
        fetchConcernHeatmap(startDate, endDate, clientId, clientSecret),
      ]);

      const leadSeries = searchTrend.series[0];
      const leadValues = leadSeries?.values || [];
      const startValue = leadValues[0] || 0;
      const endValue = leadValues.at(-1) || 0;
      const growthRate = startValue > 0 ? ((endValue - startValue) / startValue) * 100 : 0;

      return NextResponse.json({
        meta: {
          source: "naver_datalab",
          dataRange: `${startDate} ~ ${endDate}`,
          lastUpdated: endDate,
          comparisonLabel: "기간 내 검색 관심도",
        },
        page2: {
          periodLabel: label,
          selectedIngredient: leadSeries?.ingredient || PAGE2_MAIN_INGREDIENT_GROUPS[0]?.label || "",
          selectedSummary: {
            growthRate: round(growthRate, 1),
            startIndex: round(startValue, 1),
            endIndex: round(endValue, 1),
            periodKey,
          },
          searchTrend,
          concernMetrics: concernPayload.concernMetrics,
          concernTable: concernPayload.concernTable,
          insights: buildPage2Insights(searchTrend, concernPayload.concernTable),
        },
      });
    }

    const { startDate, endDate } = getWeeklyRange();
    const [functionRows, ingredientRows] = await Promise.all([
      fetchWeeklyInterestRows(FUNCTION_SIGNAL_GROUPS, startDate, endDate, clientId, clientSecret),
      fetchWeeklyInterestRows(buildIngredientKeywordGroups(), startDate, endDate, clientId, clientSecret),
    ]);

    return NextResponse.json({
      meta: {
        source: "naver_datalab",
        dataRange: `${startDate} ~ ${endDate}`,
        lastUpdated: endDate,
        comparisonLabel: "전주 대비 증감률",
      },
      page1: {
        functionRisers: functionRows
          .slice()
          .sort((a, b) => b.growth - a.growth)
          .slice(0, 5),
        ingredientPopularity: ingredientRows
          .slice()
          .sort((a, b) => b.currentWeekIndex - a.currentWeekIndex)
          .slice(0, 5),
        ingredientDemand: ingredientRows,
      },
    });
  } catch (error) {
    console.error("Naver DataLab 검색 관심도 조회 실패", error);
    return NextResponse.json(
      { message: error instanceof Error ? error.message : "네이버 데이터랩 검색 관심도 조회에 실패했습니다." },
      { status: 500 },
    );
  }
}

async function fetchWeeklyInterestRows(
  groups: NaverDatalabKeywordGroup[],
  startDate: string,
  endDate: string,
  clientId: string,
  clientSecret: string,
) {
  const rows: WeeklyInterestRow[] = [];

  for (const chunk of chunkGroups(groups, KEYWORD_GROUPS_PER_REQUEST)) {
    const response = await requestNaverDatalab([...chunk, ANCHOR_GROUP], startDate, endDate, clientId, clientSecret);
    rows.push(...rowsFromDatalabResults(response, chunk));
  }

  return normalizeSearchIndexes(rows);
}

async function fetchTrendSeries(
  groups: NaverDatalabKeywordGroup[],
  startDate: string,
  endDate: string,
  clientId: string,
  clientSecret: string,
) {
  const rawByLabel = new Map<string, Map<string, number>>();
  const orderedDates = new Set<string>();

  for (const chunk of chunkGroups(groups, KEYWORD_GROUPS_PER_REQUEST)) {
    const response = await requestNaverDatalab([...chunk, ANCHOR_GROUP], startDate, endDate, clientId, clientSecret);
    const normalized = normalizedSeriesFromDatalabResults(response, chunk);

    normalized.forEach((points, label) => {
      const current = rawByLabel.get(label) || new Map<string, number>();
      points.forEach((value, date) => {
        current.set(date, value);
        orderedDates.add(date);
      });
      rawByLabel.set(label, current);
    });
  }

  const dates = Array.from(orderedDates).sort();
  const maxValue = Math.max(
    1,
    ...Array.from(rawByLabel.values()).flatMap((points) => dates.map((date) => points.get(date) || 0)),
  );

  return {
    dates,
    series: groups.map((group) => {
      const points = rawByLabel.get(group.label) || new Map<string, number>();
      return {
        ingredient: group.label,
        values: dates.map((date) => round(((points.get(date) || 0) / maxValue) * 100, 1)),
      };
    }),
  };
}

async function fetchConcernHeatmap(
  startDate: string,
  endDate: string,
  clientId: string,
  clientSecret: string,
) {
  const rawRows = AGE_GROUPS.map((ageGroup) => ({
    age: ageGroup.label,
    values: new Map<string, number>(),
  }));

  for (const row of rawRows) {
    const ageGroup = AGE_GROUPS.find((item) => item.label === row.age);
    if (!ageGroup) continue;

    for (const chunk of chunkGroups(CONCERN_SIGNAL_GROUPS, KEYWORD_GROUPS_PER_REQUEST)) {
      const response = await requestNaverDatalab([...chunk, ANCHOR_GROUP], startDate, endDate, clientId, clientSecret, ageGroup.ages);
      const normalized = normalizedSeriesFromDatalabResults(response, chunk);
      normalized.forEach((points, label) => {
        row.values.set(label, average(Array.from(points.values())));
      });
    }
  }

  const maxValue = Math.max(1, ...rawRows.flatMap((row) => Array.from(row.values.values())));

  return {
    concernMetrics: CONCERN_SIGNAL_GROUPS.map((group) => ({
      key: group.key,
      label: group.label,
    })),
    concernTable: rawRows.map((row) => {
      const tableRow: Record<string, string | number> = { age: row.age };
      CONCERN_SIGNAL_GROUPS.forEach((group) => {
        tableRow[group.key] = round(((row.values.get(group.label) || 0) / maxValue) * 100, 1);
      });
      return tableRow;
    }),
  };
}

async function requestNaverDatalab(
  groups: NaverDatalabKeywordGroup[],
  startDate: string,
  endDate: string,
  clientId: string,
  clientSecret: string,
  ages?: string[],
) {
  const response = await fetch(NAVER_DATALAB_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Naver-Client-Id": clientId,
      "X-Naver-Client-Secret": clientSecret,
    },
    body: JSON.stringify({
      startDate,
      endDate,
      timeUnit: "date",
      ...(ages?.length ? { ages } : {}),
      keywordGroups: groups.map((group) => ({
        groupName: group.label,
        keywords: Array.from(new Set(group.keywords.map((keyword) => keyword.trim()).filter(Boolean))).slice(0, KEYWORDS_PER_GROUP),
      })),
    }),
  });
  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    const message = typeof payload?.errorMessage === "string"
      ? payload.errorMessage
      : typeof payload?.message === "string"
        ? payload.message
        : "네이버 데이터랩 API 요청에 실패했습니다.";
    throw new Error(message);
  }

  return payload as DatalabResponse;
}

function rowsFromDatalabResults(response: DatalabResponse, sourceGroups: NaverDatalabKeywordGroup[]) {
  const results = response.results || [];
  const byTitle = new Map(results.map((item) => [item.title || "", item]));
  const anchor = byTitle.get(ANCHOR_GROUP.label);
  const anchorByDate = new Map(
    (anchor?.data || []).map((point) => [point.period || "", Math.max(Number(point.ratio || 0), 0.0001)]),
  );

  return sourceGroups.flatMap((group) => {
    const result = byTitle.get(group.label);
    const values = (result?.data || []).map((point) => {
      const ratio = Number(point.ratio || 0);
      const anchorValue = anchorByDate.get(point.period || "") || 1;
      return ratio / anchorValue;
    });

    if (values.length < 2) return [];

    const midpoint = Math.max(1, Math.floor(values.length / 2));
    const previousWeekIndex = average(values.slice(0, midpoint));
    const currentWeekIndex = average(values.slice(midpoint));

    return [{
      key: group.key,
      label: group.label,
      currentWeekIndex,
      previousWeekIndex,
      growth: calculateGrowth(currentWeekIndex, previousWeekIndex),
      searchIndex: currentWeekIndex,
    }];
  });
}

function normalizedSeriesFromDatalabResults(response: DatalabResponse, sourceGroups: NaverDatalabKeywordGroup[]) {
  const results = response.results || [];
  const byTitle = new Map(results.map((item) => [item.title || "", item]));
  const anchor = byTitle.get(ANCHOR_GROUP.label);
  const anchorByDate = new Map(
    (anchor?.data || []).map((point) => [point.period || "", Math.max(Number(point.ratio || 0), 0.0001)]),
  );
  const output = new Map<string, Map<string, number>>();

  sourceGroups.forEach((group) => {
    const points = new Map<string, number>();
    const result = byTitle.get(group.label);
    (result?.data || []).forEach((point) => {
      const date = point.period || "";
      if (!date) return;
      const anchorValue = anchorByDate.get(date) || 1;
      points.set(date, Number(point.ratio || 0) / anchorValue);
    });
    output.set(group.label, points);
  });

  return output;
}

function normalizeSearchIndexes(rows: WeeklyInterestRow[]) {
  const maxCurrent = Math.max(1, ...rows.map((row) => row.currentWeekIndex));

  return rows.map((row) => ({
    ...row,
    currentWeekIndex: round((row.currentWeekIndex / maxCurrent) * 100, 1),
    previousWeekIndex: round((row.previousWeekIndex / maxCurrent) * 100, 1),
    growth: round(row.growth, 1),
    searchIndex: round((row.currentWeekIndex / maxCurrent) * 100, 1),
  }));
}

function getWeeklyRange() {
  if (process.env.DASHBOARD_START_DATE && process.env.DASHBOARD_END_DATE) {
    return {
      startDate: process.env.DASHBOARD_START_DATE,
      endDate: process.env.DASHBOARD_END_DATE,
    };
  }

  const end = new Date();
  end.setDate(end.getDate() - 1);
  const start = new Date(end);
  start.setDate(start.getDate() - 13);

  return {
    startDate: toDateString(start),
    endDate: toDateString(end),
  };
}

function getPeriodRange(periodKey: string) {
  const end = new Date();
  end.setDate(end.getDate() - 1);

  const dayMap: Record<string, { days: number; label: string }> = {
    snapshot: { days: 7, label: "스냅샷" },
    "1m": { days: 30, label: "1개월" },
    "6m": { days: 180, label: "6개월" },
    "1y": { days: 365, label: "1년" },
    "3y": { days: 1095, label: "3년" },
  };
  const option = dayMap[periodKey] || dayMap.snapshot;
  const start = new Date(end);
  start.setDate(start.getDate() - option.days + 1);

  return {
    startDate: toDateString(start),
    endDate: toDateString(end),
    label: option.label,
  };
}

function buildPage2Insights(
  searchTrend: { dates: string[]; series: Array<{ ingredient: string; values: number[] }> },
  concernTable: Array<Record<string, string | number>>,
) {
  const strongestIngredient = searchTrend.series
    .slice()
    .sort((a, b) => Number(b.values.at(-1) || 0) - Number(a.values.at(-1) || 0))[0];
  const strongestConcern = concernTable.flatMap((row) =>
    Object.entries(row)
      .filter(([key]) => key !== "age")
      .map(([key, value]) => ({ age: String(row.age), key, value: Number(value || 0) })),
  ).sort((a, b) => b.value - a.value)[0];

  return [
    strongestIngredient
      ? `${strongestIngredient.ingredient}의 현재 검색 관심도가 주요 성분 중 가장 높습니다.`
      : "표시할 성분 검색 관심도 데이터가 없습니다.",
    strongestConcern
      ? `${strongestConcern.age}에서 ${strongestConcern.key} 고민 키워드 집중도가 상대적으로 높게 나타납니다.`
      : "표시할 연령대별 피부 고민 데이터가 없습니다.",
  ];
}

function toDateString(date: Date) {
  return date.toISOString().slice(0, 10);
}

function average(values: number[]) {
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;
}

function calculateGrowth(current: number, previous: number) {
  if (previous <= 0) return current > 0 ? 100 : 0;
  return ((current - previous) / previous) * 100;
}

function round(value: number, digits = 0) {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

function chunkGroups<T>(items: T[], size: number) {
  const chunks: T[][] = [];
  for (let index = 0; index < items.length; index += size) {
    chunks.push(items.slice(index, index + size));
  }
  return chunks;
}
