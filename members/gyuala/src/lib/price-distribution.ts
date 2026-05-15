import type { PriceDistributionItem } from "@/lib/types";
import { createClient } from "@/utils/supabase/client";

const PRICE_INGREDIENTS = ["나이아신아마이드", "히알루론산", "병풀/시카", "PDRN", "레티놀"];

type ProductSnapshotRow = {
  goods_no?: string | number | null;
  collected_date?: string | null;
  regular_price?: string | number | null;
  sales_price?: string | number | null;
};

type ProductIngredientRow = {
  goods_no?: string | number | null;
  ingredient_name?: string | null;
};

const INGREDIENT_ALIASES: Record<string, string[]> = {
  "나이아신아마이드": ["나이아신아마이드", "니아신아마이드", "나이아신", "niacinamide"],
  "히알루론산": ["히알루론산", "히알루로닉", "히알루로닉산", "hyaluronic", "sodium hyaluronate"],
  "병풀/시카": ["병풀", "시카", "센텔라", "cica", "centella"],
  PDRN: ["pdrn", "피디알엔", "피디알앤"],
  "레티놀": ["레티놀", "레티날", "retinol", "retinal"],
};

export function getEmptyPriceDistribution(): PriceDistributionItem[] {
  return PRICE_INGREDIENTS.map((ingredient) => ({
    ingredient,
    salePrices: [],
    listPrices: [],
    prices: [],
    salePricePoints: [],
    listPricePoints: [],
  }));
}

export async function fetchPriceDistributionFromSupabase(): Promise<PriceDistributionItem[]> {
  const supabase = createClient();
  const { data: latestRows, error: latestError } = await supabase
    .from("product_snapshots")
    .select("collected_date")
    .order("collected_date", { ascending: false })
    .limit(1);

  if (latestError) throw new Error(`product_snapshots 최신일 조회 실패: ${latestError.message}`);

  const latestDate = String(latestRows?.[0]?.collected_date || "").slice(0, 10);
  if (!latestDate) return getEmptyPriceDistribution();

  const { data: snapshotRows, error: snapshotError } = await supabase
    .from("product_snapshots")
    .select("goods_no, collected_date, regular_price, sales_price")
    .eq("collected_date", latestDate)
    .limit(10000);

  if (snapshotError) throw new Error(`product_snapshots 가격 조회 실패: ${snapshotError.message}`);

  const snapshots = ((snapshotRows || []) as ProductSnapshotRow[]).filter((row) => row.goods_no);
  const goodsNos = Array.from(new Set(snapshots.map((row) => String(row.goods_no))));
  if (!goodsNos.length) return getEmptyPriceDistribution();

  const ingredientRows = await fetchIngredientRows(goodsNos);
  const ingredientsByGoodsNo = new Map<string, string[]>();

  ingredientRows.forEach((row) => {
    const goodsNo = String(row.goods_no ?? "").trim();
    const ingredientName = String(row.ingredient_name ?? "").trim();
    if (!goodsNo || !ingredientName) return;
    const current = ingredientsByGoodsNo.get(goodsNo) || [];
    current.push(ingredientName);
    ingredientsByGoodsNo.set(goodsNo, current);
  });

  return PRICE_INGREDIENTS.map((ingredient) => {
    const salePricePoints: PriceDistributionItem["salePricePoints"] = [];
    const listPricePoints: PriceDistributionItem["listPricePoints"] = [];
    const aliases = INGREDIENT_ALIASES[ingredient] || [ingredient];

    snapshots.forEach((snapshot) => {
      const goodsNo = String(snapshot.goods_no ?? "").trim();
      const matched = (ingredientsByGoodsNo.get(goodsNo) || []).some((name) => matchesAlias(name, aliases));
      if (!matched) return;

      const salePrice = toNumber(snapshot.sales_price);
      const listPrice = toNumber(snapshot.regular_price);

      if (salePrice > 0) {
        salePricePoints.push({
          value: salePrice,
          ingredient,
          productName: `상품 ${goodsNo}`,
          goodsNo,
          basisPrice: salePrice,
          regularPrice: listPrice || null,
          salesPrice: salePrice,
          volumeMl: null,
          priceType: "sale",
        });
      }

      if (listPrice > 0) {
        listPricePoints.push({
          value: listPrice,
          ingredient,
          productName: `상품 ${goodsNo}`,
          goodsNo,
          basisPrice: listPrice,
          regularPrice: listPrice,
          salesPrice: salePrice || null,
          volumeMl: null,
          priceType: "list",
        });
      }
    });

    return {
      ingredient,
      salePrices: salePricePoints.map((point) => point.value),
      listPrices: listPricePoints.map((point) => point.value),
      prices: salePricePoints.map((point) => point.value),
      salePricePoints,
      listPricePoints,
    };
  });
}

async function fetchIngredientRows(goodsNos: string[]) {
  const supabase = createClient();
  const rows: ProductIngredientRow[] = [];

  for (let index = 0; index < goodsNos.length; index += 180) {
    const chunk = goodsNos.slice(index, index + 180);
    const { data, error } = await supabase
      .from("product_main_ingredients")
      .select("goods_no, ingredient_name")
      .in("goods_no", chunk)
      .limit(10000);

    if (error) throw new Error(`product_main_ingredients 가격 조인 조회 실패: ${error.message}`);
    rows.push(...((data || []) as ProductIngredientRow[]));
  }

  return rows;
}

function matchesAlias(value: string, aliases: string[]) {
  const normalized = normalize(value);
  return aliases.some((alias) => normalized.includes(normalize(alias)));
}

function normalize(value: string) {
  return value.toLowerCase().replace(/\s+/g, "");
}

function toNumber(value: unknown) {
  const number = Number(String(value ?? "").replace(/,/g, ""));
  return Number.isFinite(number) ? number : 0;
}
