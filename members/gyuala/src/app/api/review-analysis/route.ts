import { NextResponse } from "next/server";
import { REVIEW_INGREDIENT_OPTIONS } from "@/lib/reviewConstants";
import { analyzeIngredientReviews } from "@/lib/reviewAnalysis";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const url = new URL(request.url);
    const ingredient = url.searchParams.get("ingredient") || REVIEW_INGREDIENT_OPTIONS[0];

    if (!REVIEW_INGREDIENT_OPTIONS.includes(ingredient as (typeof REVIEW_INGREDIENT_OPTIONS)[number])) {
      return NextResponse.json({ message: "지원하지 않는 성분입니다." }, { status: 400 });
    }

    const result = await analyzeIngredientReviews(ingredient);
    return NextResponse.json(result);
  } catch (error) {
    console.error("리뷰 분석 API 실패", error);
    return NextResponse.json(
      { message: error instanceof Error ? error.message : "리뷰 분석에 실패했습니다." },
      { status: 500 },
    );
  }
}
