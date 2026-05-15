import { env, pipeline } from "@xenova/transformers";

export type SentimentLabel = "positive" | "neutral" | "negative";

// Transformers.js 감정 분석 유틸에서 사용하는 Hugging Face 모델입니다.
// 현재 /api/review-analysis 화면 API는 이 모델을 호출하지 않고, src/lib/reviewAnalysis.ts의 별점+키워드 규칙을 사용합니다.
export const HUGGING_FACE_SENTIMENT_MODEL = "Xenova/nlptown-bert-base-multilingual-uncased-sentiment";

let sentimentPipeline: any = null;
let sentimentPipelineUnavailable = false;

async function getSentimentPipeline() {
  if (sentimentPipelineUnavailable) return null;

  if (!sentimentPipeline) {
    try {
      env.allowRemoteModels = true;
      env.allowLocalModels = true;
      sentimentPipeline = await pipeline(
        "sentiment-analysis",
        HUGGING_FACE_SENTIMENT_MODEL,
      );
    } catch (error) {
      sentimentPipelineUnavailable = true;
      console.error("Transformers.js 감정 분석 모델 로드 실패, fallback 사용", error instanceof Error ? error.message : error);
      return null;
    }
  }

  return sentimentPipeline;
}

export async function analyzeSentiment(text: string): Promise<SentimentLabel> {
  const classifier = await getSentimentPipeline();
  if (!classifier) return analyzeSentimentFallback(text);

  const result = await classifier(text);
  return labelToSentiment(result?.[0]?.label ?? "");
}

export async function analyzeSentiments(texts: string[]): Promise<SentimentLabel[]> {
  try {
    const classifier = await getSentimentPipeline();
    if (!classifier) return texts.map(analyzeSentimentFallback);

    const labels: SentimentLabel[] = [];

    for (let index = 0; index < texts.length; index += 16) {
      const chunk = texts.slice(index, index + 16);
      const result = await classifier(chunk);
      const rows = Array.isArray(result) ? result : [];
      labels.push(...rows.map((item: { label?: string } | Array<{ label?: string }>) => {
        const row = Array.isArray(item) ? item[0] : item;
        return labelToSentiment(row?.label ?? "");
      }));
    }

    return labels.length === texts.length ? labels : texts.map(analyzeSentimentFallback);
  } catch (error) {
    console.error("Transformers.js 감정 분석 실행 실패, fallback 사용", error instanceof Error ? error.message : error);
    return texts.map(analyzeSentimentFallback);
  }
}

function labelToSentiment(label: string): SentimentLabel {
  if (label.includes("1") || label.includes("2")) return "negative";
  if (label.includes("4") || label.includes("5")) return "positive";
  return "neutral";
}

function analyzeSentimentFallback(text: string): SentimentLabel {
  const normalized = text.toLowerCase();
  const positiveWords = ["좋", "촉촉", "진정", "흡수", "산뜻", "매끈", "광채", "재구매", "만족", "편안"];
  const negativeWords = ["건조", "자극", "따가", "트러블", "끈적", "밀림", "무거", "답답", "붉", "가려"];
  const positive = positiveWords.filter((word) => normalized.includes(word)).length;
  const negative = negativeWords.filter((word) => normalized.includes(word)).length;

  if (positive > negative) return "positive";
  if (negative > positive) return "negative";
  return "neutral";
}
