import type { DemandSupplyItem } from "@/lib/types";
import { createClient } from "@/utils/supabase/client";

export const DEFAULT_DEMAND_SUPPLY_MATRIX_CONFIG = {
  threshold: 50,
};

export async function fetchDemandSupplyMatrixFromSupabase(config = DEFAULT_DEMAND_SUPPLY_MATRIX_CONFIG): Promise<{
  items: DemandSupplyItem[];
  isUnavailable: boolean;
  error: string;
}> {
  const supabase = createClient();
  const { data, error } = await supabase
    .from("daily_metric_snapshot")
    .select("snapshot_date, ingredient_matrix")
    .order("snapshot_date", { ascending: false })
    .limit(1);

  if (error) {
    return {
      items: [],
      isUnavailable: true,
      error: `daily_metric_snapshot 조회 실패: ${error.message}`,
    };
  }

  const matrix = data?.[0]?.ingredient_matrix;
  if (!Array.isArray(matrix) || !matrix.length) {
    return {
      items: [],
      isUnavailable: true,
      error: "daily_metric_snapshot에 수요-공급 매트릭스 데이터가 없습니다.",
    };
  }

  const threshold = Number.isFinite(Number(config.threshold))
    ? Number(config.threshold)
    : DEFAULT_DEMAND_SUPPLY_MATRIX_CONFIG.threshold;

  return {
    items: matrix.map((row) => normalizeDemandSupplyItem(row, threshold)).sort(sortDemandSupplyItems),
    isUnavailable: false,
    error: "",
  };
}

function normalizeDemandSupplyItem(row: unknown, threshold: number): DemandSupplyItem {
  const item = row as Partial<DemandSupplyItem> & Record<string, unknown>;
  const demand = clampScore(item.demand);
  const supply = clampScore(item.supply);
  const gap = toNumber(item.gap, demand - supply);

  return {
    ingredient: String(item.ingredient || ""),
    demand,
    supply,
    growth: toNumber(item.growth ?? item.demandWow ?? item.demandMom, 0),
    status: normalizeStatus(demand, supply, threshold),
    size: Math.max(18, toNumber(item.size, 24)),
    previousDemand: optionalNumber(item.previousDemand),
    previousSupply: optionalNumber(item.previousSupply),
    demandWow: optionalNumber(item.demandWow ?? item.demandMom),
    supplyWow: optionalNumber(item.supplyWow),
    supplyCount: optionalNumber(item.supplyCount),
    gap,
    opportunityScore: optionalNumber(item.opportunityScore),
  };
}

function normalizeStatus(demand: number, supply: number, threshold: number): DemandSupplyItem["status"] {
  const isHighDemand = demand >= threshold;
  const isHighSupply = supply >= threshold;

  if (isHighDemand && !isHighSupply) return "opportunity";
  if (isHighDemand && isHighSupply) return "growth";
  if (!isHighDemand && isHighSupply) return "oversupply";
  return "stable";
}

function sortDemandSupplyItems(a: DemandSupplyItem, b: DemandSupplyItem) {
  const priority: Record<DemandSupplyItem["status"], number> = {
    opportunity: 4,
    growth: 3,
    oversupply: 2,
    shortage: 1,
    stable: 0,
  };

  return (
    priority[b.status] - priority[a.status] ||
    Math.abs(Number(b.gap || 0)) - Math.abs(Number(a.gap || 0)) ||
    Number(b.demand || 0) - Number(a.demand || 0)
  );
}

function clampScore(value: unknown) {
  return Math.min(100, Math.max(0, toNumber(value, 0)));
}

function optionalNumber(value: unknown) {
  const number = Number(value);
  return Number.isFinite(number) ? number : undefined;
}

function toNumber(value: unknown, fallback: number) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}
