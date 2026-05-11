import { NextResponse } from "next/server";
import {
  ANCHOR_GROUP,
  FUNCTION_SIGNAL_GROUPS,
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

export async function GET() {
  try {
    const clientId = process.env.NAVER_CLIENT_ID;
    const clientSecret = process.env.NAVER_CLIENT_SECRET;

    if (!clientId || !clientSecret) {
      return NextResponse.json(
        { message: "NAVER_CLIENT_ID 또는 NAVER_CLIENT_SECRET 서버 환경변수가 필요합니다." },
        { status: 500 },
      );
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
    console.error("Naver DataLab 주간 검색 관심도 조회 실패", error);
    return NextResponse.json(
      { message: error instanceof Error ? error.message : "네이버 데이터랩 주간 검색 관심도 조회에 실패했습니다." },
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

async function requestNaverDatalab(
  groups: NaverDatalabKeywordGroup[],
  startDate: string,
  endDate: string,
  clientId: string,
  clientSecret: string,
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
