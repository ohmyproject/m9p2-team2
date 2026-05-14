import { NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type Page1InsightRequest = {
  functionTop5: unknown[];
  ingredientTop5: unknown[];
  priceOutliers: unknown[];
  demandSupplyMatrix: unknown[];
  dataAvailability: Record<string, string>;
};

const OPENAI_API_URL = "https://api.openai.com/v1/responses";
const DEFAULT_OPENAI_MODEL = "gpt-4.1-mini";
const ERROR_MESSAGE = "인사이트 요약을 생성하지 못했습니다.";

export async function POST(request: Request) {
  const apiKey = process.env.OPENAI_API_KEY;

  if (!apiKey) {
    console.error("OPENAI_API_KEY가 서버 환경변수에 없습니다.");
    return NextResponse.json({ error: ERROR_MESSAGE }, { status: 500 });
  }

  try {
    const body = (await request.json()) as Page1InsightRequest;
    const response = await fetch(OPENAI_API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: process.env.OPENAI_MODEL || DEFAULT_OPENAI_MODEL,
        input: [
          {
            role: "system",
            content: [
              "너는 화장품 MD 대시보드의 Page 1 데이터를 요약하는 분석가다.",
              "제공된 실제 데이터만 근거로 한국어 인사이트를 2~5개 작성한다.",
              "각 문장은 화장품 MD가 성분 기획, 소싱, 재고, 가격 포지션, 상세페이지 메시지 중 하나를 결정하는 데 바로 쓸 수 있어야 한다.",
              "데이터가 비어 있거나 필요한 API가 없으면 그 한계를 명확히 말한다.",
              "없는 수치나 제품명은 만들지 않는다.",
            ].join(" "),
          },
          {
            role: "user",
            content: JSON.stringify(body),
          },
        ],
        text: {
          format: {
            type: "json_schema",
            name: "page1_insights",
            strict: true,
            schema: {
              type: "object",
              additionalProperties: false,
              properties: {
                insights: {
                  type: "array",
                  minItems: 2,
                  maxItems: 5,
                  items: { type: "string" },
                },
              },
              required: ["insights"],
            },
          },
        },
      }),
    });
    const payload = await response.json().catch(() => ({}));

    if (!response.ok) {
      console.error("OpenAI 인사이트 요약 API 실패", {
        status: response.status,
        error: getOpenAiErrorMessage(payload),
      });
      return NextResponse.json({ error: ERROR_MESSAGE }, { status: 500 });
    }

    const outputText = extractResponseText(payload);
    const parsed = JSON.parse(outputText) as { insights?: unknown };
    const insights = Array.isArray(parsed.insights)
      ? parsed.insights.map((item) => String(item).trim()).filter(Boolean).slice(0, 5)
      : [];

    if (!insights.length) {
      throw new Error("OpenAI 응답에 insights 배열이 없습니다.");
    }

    return NextResponse.json({ insights });
  } catch (error) {
    console.error("인사이트 요약 생성 실패", error);
    return NextResponse.json({ error: ERROR_MESSAGE }, { status: 500 });
  }
}

function extractResponseText(payload: unknown) {
  const row = payload as {
    output_text?: unknown;
    output?: Array<{ content?: Array<{ text?: unknown }> }>;
  };

  if (typeof row.output_text === "string" && row.output_text.trim()) {
    return row.output_text;
  }

  const text = row.output
    ?.flatMap((item) => item.content || [])
    .map((item) => (typeof item.text === "string" ? item.text : ""))
    .filter(Boolean)
    .join("\n");

  if (text) return text;
  throw new Error("OpenAI 응답 텍스트를 찾지 못했습니다.");
}

function getOpenAiErrorMessage(payload: unknown) {
  const row = payload as { error?: { message?: unknown } };
  return typeof row.error?.message === "string" ? row.error.message : "unknown";
}
