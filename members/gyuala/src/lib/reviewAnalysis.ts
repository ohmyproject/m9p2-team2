import { NEGATIVE_REVIEW_KEYWORDS, POSITIVE_REVIEW_KEYWORDS } from "@/lib/reviewConstants";
import { createClient } from "@supabase/supabase-js";

export type ReviewKeyword = {
  keyword: string;
  count: number;
  percentage: number;
};

export type ReviewTopProduct = {
  goodsNo: string;
  productName: string;
  platform: string;
  rank: number;
  reviewCount: number;
  reviewRating: number;
  positiveRatio: number;
  sentimentCounts: SentimentCounts;
  score: number;
  reason: string;
};

export type SkinTypeAnalysis = {
  skinType: string;
  positive: number;
  neutral: number;
  negative: number;
  issue: string;
};

export type ReviewAnalysisResult = {
  ingredient: string;
  totalReviews: number;
  sentiment: {
    positive: number;
    neutral: number;
    negative: number;
    positiveRatio: number;
    neutralRatio: number;
    negativeRatio: number;
  };
  keywords: {
    positive: ReviewKeyword[];
    negative: ReviewKeyword[];
  };
  topProducts: ReviewTopProduct[];
  skinTypeAnalysis: SkinTypeAnalysis[];
  insights: string[];
};

type SentimentLabel = "positive" | "neutral" | "negative";
type SentimentCounts = Record<SentimentLabel, number>;

const REVIEW_SENTIMENT_ENGINE = {
  usesHuggingFace: false,
  modelName: "",
  method: "keyword/rating rules",
} as const;

export async function analyzeIngredientReviews(ingredient: string): Promise<ReviewAnalysisResult> {
  const rows = (await fetchProductReviews()).filter((row) => matchesIngredient(row.main_ingredients, ingredient));
  if (!rows.length) {
    const emptyCounts: SentimentCounts = { positive: 0, neutral: 0, negative: 0 };
    logReviewAnalysisDebug(ingredient, emptyCounts, []);
    return emptyReviewAnalysis(ingredient);
  }

  const productMeta = await fetchProductMetaMap(getUniqueGoodsNos(rows));
  const sentiments = rows.map(sentimentFromReview);
  const totalReviews = rows.length;
  const sentimentCounts = countSentiments(sentiments);
  const positiveCount = sentimentCounts.positive;
  const neutralCount = sentimentCounts.neutral;
  const negativeCount = sentimentCounts.negative;
  const positive = countKeywords(rows, POSITIVE_REVIEW_KEYWORDS, totalReviews);
  const negative = countKeywords(rows, NEGATIVE_REVIEW_KEYWORDS, totalReviews);
  const topProducts = buildTopProducts(rows, productMeta);

  logReviewAnalysisDebug(ingredient, sentimentCounts, topProducts);

  return {
    ingredient,
    totalReviews,
    sentiment: {
      positive: positiveCount,
      neutral: neutralCount,
      negative: negativeCount,
      positiveRatio: ratio(positiveCount, totalReviews),
      neutralRatio: ratio(neutralCount, totalReviews),
      negativeRatio: ratio(negativeCount, totalReviews),
    },
    keywords: {
      positive,
      negative,
    },
    topProducts,
    skinTypeAnalysis: buildSkinTypeAnalysis(rows),
    insights: buildReviewInsights(ingredient, totalReviews, positiveCount, negativeCount, positive, negative),
  };
}

type ProductReviewRow = {
  goods_no?: string | number | null;
  platform?: string | null;
  rank?: string | number | null;
  main_ingredients?: string | null;
  review_rating?: string | number | null;
  skin_type?: string | null;
  review_text?: string | null;
};

const PAGE_SIZE = 1000;
const META_CHUNK_SIZE = 200;

type ProductMeta = {
  productName?: string;
};

const INGREDIENT_ALIASES: Record<string, string[]> = {
  "나이아신아마이드": ["나이아신아마이드", "니아신아마이드", "나이아신", "niacinamide"],
  "히알루론산": ["히알루론산", "히알루로닉", "히알루로닉산", "hyaluronic"],
  "병풀/시카": ["병풀", "시카", "센텔라", "cica", "centella"],
  PDRN: ["pdrn", "피디알엔", "피디알앤"],
  "레티놀": ["레티놀", "레티날", "retinol", "retinal"],
};

function getSupabaseClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) throw new Error("Supabase 환경변수가 필요합니다.");
  return createClient(url, key, { auth: { persistSession: false } });
}

async function fetchProductReviews() {
  const supabase = getSupabaseClient();
  const rows: ProductReviewRow[] = [];

  for (let from = 0; ; from += PAGE_SIZE) {
    const { data, error } = await supabase
      .from("product_reviews")
      .select("goods_no, platform, rank, main_ingredients, review_rating, skin_type, review_text")
      .range(from, from + PAGE_SIZE - 1);

    if (error) throw new Error(`product_reviews 조회 실패: ${error.message}`);

    const page = (data || []) as ProductReviewRow[];
    rows.push(...page);
    if (page.length < PAGE_SIZE) break;
  }

  return rows;
}

function getUniqueGoodsNos(rows: ProductReviewRow[]) {
  return Array.from(
    new Set(
      rows
        .map((row) => String(row.goods_no ?? "").trim())
        .filter(Boolean),
    ),
  );
}

async function fetchProductMetaMap(goodsNos: string[]) {
  const meta = new Map<string, ProductMeta>();
  if (!goodsNos.length) return meta;

  const supabase = getSupabaseClient();

  for (const chunk of chunkArray(goodsNos, META_CHUNK_SIZE)) {
    const { data, error } = await supabase
      .from("products")
      .select("goods_no, product_name")
      .in("goods_no", chunk);

    if (error) {
      console.error(`products 제품명 조회 실패: ${error.message}`);
      continue;
    }

    (data || []).forEach((row) => {
      const goodsNo = String(row.goods_no ?? "").trim();
      const productName = String(row.product_name ?? "").trim();
      if (!goodsNo || !productName) return;
      meta.set(goodsNo, { ...meta.get(goodsNo), productName });
    });
  }

  return meta;
}

function chunkArray<T>(items: T[], size: number) {
  const chunks: T[][] = [];
  for (let index = 0; index < items.length; index += size) {
    chunks.push(items.slice(index, index + size));
  }
  return chunks;
}

function matchesIngredient(value: unknown, ingredient: string) {
  const normalized = normalize(String(value || ""));
  const aliases = INGREDIENT_ALIASES[ingredient] || [ingredient];
  return aliases.some((alias) => normalized.includes(normalize(alias)));
}

function normalize(value: string) {
  return value.toLowerCase().replace(/\s+/g, "");
}

function sentimentFromReview(row: ProductReviewRow): SentimentLabel {
  const rating = Number(row.review_rating);
  const text = String(row.review_text || "");
  const positiveKeywordCount = countKeywordHits(text, POSITIVE_REVIEW_KEYWORDS);
  const negativeKeywordCount = countKeywordHits(text, NEGATIVE_REVIEW_KEYWORDS);

  if (negativeKeywordCount >= 2) return "negative";
  if (negativeKeywordCount >= 1 && Number.isFinite(rating) && rating <= 4) return "negative";
  if (negativeKeywordCount >= 1 && Number.isFinite(rating) && rating >= 5) return "neutral";
  if (Number.isFinite(rating) && rating <= 2) return "negative";
  if (Number.isFinite(rating) && rating === 3) return "neutral";
  if (positiveKeywordCount > 0 || (Number.isFinite(rating) && rating >= 4)) return "positive";
  return "neutral";
}

function countKeywordHits(text: string, keywords: string[]) {
  const normalized = normalize(text);
  return keywords.filter((keyword) => normalized.includes(normalize(keyword))).length;
}

function countSentiments(labels: SentimentLabel[]): SentimentCounts {
  return labels.reduce<SentimentCounts>(
    (counts, label) => {
      counts[label] += 1;
      return counts;
    },
    { positive: 0, neutral: 0, negative: 0 },
  );
}

function countKeywords(rows: ProductReviewRow[], keywords: string[], totalReviews: number): ReviewKeyword[] {
  return keywords
    .map((keyword) => {
      const count = rows.filter((row) => countKeywordHits(String(row.review_text || ""), [keyword]) > 0).length;
      return { keyword, count, percentage: ratio(count, totalReviews) };
    })
    .filter((row) => row.count > 0)
    .sort((a, b) => b.count - a.count)
    .slice(0, 5);
}

function buildTopProducts(rows: ProductReviewRow[], productMeta: Map<string, ProductMeta>): ReviewTopProduct[] {
  const grouped = new Map<string, ProductReviewRow[]>();
  rows.forEach((row) => {
    const goodsNo = String(row.goods_no ?? "").trim();
    if (!goodsNo) return;
    grouped.set(goodsNo, [...(grouped.get(goodsNo) || []), row]);
  });

  return Array.from(grouped.entries())
    .map(([goodsNo, productRows]) => {
      const analyzedReviewCount = productRows.length;
      const sentimentCounts = countSentiments(productRows.map(sentimentFromReview));
      const positiveCount = sentimentCounts.positive;
      const ratingValues = productRows
        .map((row) => Number(row.review_rating))
        .filter((value) => Number.isFinite(value));
      const reviewRating = ratingValues.length
        ? ratingValues.reduce((sum, value) => sum + value, 0) / ratingValues.length
        : 0;
      const meta = productMeta.get(goodsNo);
      const positiveRatio = ratio(positiveCount, analyzedReviewCount);
      const rankValues = productRows
        .map((row) => Number(row.rank))
        .filter((value) => Number.isFinite(value) && value > 0);
      const rank = rankValues.length ? Math.min(...rankValues) : 0;
      const negativeKeywords = countKeywords(productRows, NEGATIVE_REVIEW_KEYWORDS, analyzedReviewCount);
      const productName = meta?.productName;
      if (!productName) return null;

      return {
        goodsNo,
        productName,
        platform: productRows[0]?.platform || "올리브영",
        rank,
        reviewCount: analyzedReviewCount,
        reviewRating: round(reviewRating, 1),
        positiveRatio: round(positiveRatio, 1),
        sentimentCounts,
        score: analyzedReviewCount * 0.45 + positiveRatio * 0.35 + reviewRating * 4 - rank * 0.1,
        reason: negativeKeywords[0]
          ? `${negativeKeywords[0].keyword} 이슈 ${negativeKeywords[0].count}건 확인`
          : "긍정 리뷰 비율이 높습니다.",
      };
    })
    .filter((product): product is ReviewTopProduct => Boolean(product))
    .sort((a, b) => b.score - a.score)
    .slice(0, 3);
}

function buildSkinTypeAnalysis(rows: ProductReviewRow[]): SkinTypeAnalysis[] {
  const skinTypes = ["건성", "복합성", "지성", "민감성"];

  return skinTypes.map((skinType) => {
    const matchedRows = rows.filter((row) => String(row.skin_type || "").includes(skinType));
    const positive = matchedRows.filter((row) => sentimentFromReview(row) === "positive").length;
    const neutral = matchedRows.filter((row) => sentimentFromReview(row) === "neutral").length;
    const negative = matchedRows.filter((row) => sentimentFromReview(row) === "negative").length;
    const negativeKeywords = countKeywords(matchedRows, NEGATIVE_REVIEW_KEYWORDS, matchedRows.length);

    return {
      skinType,
      positive: ratio(positive, matchedRows.length),
      neutral: ratio(neutral, matchedRows.length),
      negative: ratio(negative, matchedRows.length),
      issue: matchedRows.length
        ? negativeKeywords[0]
          ? `${negativeKeywords[0].keyword} 언급 ${negativeKeywords[0].count}건`
          : "큰 부정 이슈 없음"
        : "해당 피부 타입 리뷰 부족",
    };
  });
}

function emptyReviewAnalysis(ingredient: string): ReviewAnalysisResult {
  return {
    ingredient,
    totalReviews: 0,
    sentiment: {
      positive: 0,
      neutral: 0,
      negative: 0,
      positiveRatio: 0,
      neutralRatio: 0,
      negativeRatio: 0,
    },
    keywords: {
      positive: [],
      negative: [],
    },
    topProducts: [],
    skinTypeAnalysis: [],
    insights: [],
  };
}

function logReviewAnalysisDebug(
  ingredient: string,
  sentimentCounts: SentimentCounts,
  topProducts: ReviewTopProduct[],
) {
  if (process.env.NODE_ENV === "production") return;

  console.info("[review-analysis] summary", {
    ingredient,
    analyzedReviewCount: sentimentCounts.positive + sentimentCounts.neutral + sentimentCounts.negative,
    positive: sentimentCounts.positive,
    neutral: sentimentCounts.neutral,
    negative: sentimentCounts.negative,
    usesHuggingFace: REVIEW_SENTIMENT_ENGINE.usesHuggingFace,
    huggingFaceModel: REVIEW_SENTIMENT_ENGINE.modelName || null,
    method: REVIEW_SENTIMENT_ENGINE.method,
  });
  console.info("[review-analysis] topProducts", topProducts.map((product) => ({
    goodsNo: product.goodsNo,
    productName: product.productName,
    reviewCount: product.reviewCount,
    positive: product.sentimentCounts.positive,
    neutral: product.sentimentCounts.neutral,
    negative: product.sentimentCounts.negative,
  })));
}

function buildReviewInsights(
  ingredient: string,
  totalReviews: number,
  positiveCount: number,
  negativeCount: number,
  positiveKeywords: ReviewKeyword[],
  negativeKeywords: ReviewKeyword[],
) {
  if (!totalReviews) {
    return [`${ingredient} 관련 리뷰 데이터가 아직 충분히 수집되지 않았습니다.`];
  }

  const insights = [
    `${ingredient} 관련 리뷰 ${totalReviews.toLocaleString("ko-KR")}건 중 긍정 비율은 ${ratio(positiveCount, totalReviews).toFixed(1)}%입니다.`,
  ];

  if (positiveKeywords[0]) {
    insights.push(`긍정 키워드는 '${positiveKeywords[0].keyword}'가 가장 많이 반복되어 상세페이지 강점 메시지로 활용할 수 있습니다.`);
  }

  if (negativeCount > 0 && negativeKeywords[0]) {
    insights.push(`부정 리뷰에서는 '${negativeKeywords[0].keyword}'가 감지되어 제형/사용법/타겟 피부 타입 안내를 보완해야 합니다.`);
  }

  return insights;
}

function ratio(value: number, total: number) {
  if (!total) return 0;
  return (value / total) * 100;
}

function round(value: number, digits = 1) {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}
