export type NaverDatalabKeywordGroup = {
  key: string;
  label: string;
  keywords: string[];
};

export const ANCHOR_GROUP: NaverDatalabKeywordGroup = {
  key: "anchor",
  label: "화장품",
  keywords: ["화장품", "스킨케어", "세럼", "앰플"],
};

export const FUNCTION_SIGNAL_GROUPS: NaverDatalabKeywordGroup[] = [
  { key: "wrinkle_elasticity", label: "주름/탄력", keywords: ["주름 개선", "탄력", "레티놀", "안티에이징"] },
  { key: "tone_spot", label: "잡티/톤", keywords: ["잡티", "미백", "피부톤", "나이아신아마이드"] },
  { key: "trouble_calming", label: "트러블/진정", keywords: ["트러블", "진정", "시카", "병풀"] },
  { key: "dryness_barrier", label: "건조/장벽", keywords: ["보습", "피부장벽", "히알루론산", "세라마이드"] },
  { key: "pore_sebum", label: "모공/피지", keywords: ["모공", "피지", "각질", "피부결"] },
];

export const PAGE2_MAIN_INGREDIENT_GROUPS: NaverDatalabKeywordGroup[] = [
  { key: "niacinamide", label: "나이아신아마이드", keywords: ["나이아신아마이드", "나이아신아마이드 세럼", "나이아신아마이드 앰플"] },
  { key: "hyaluronic_acid", label: "히알루론산", keywords: ["히알루론산", "히알루론산 세럼", "히알루론산 앰플"] },
  { key: "centella", label: "병풀/시카", keywords: ["병풀", "시카", "시카 세럼", "병풀 앰플"] },
  { key: "pdrn", label: "PDRN", keywords: ["PDRN", "PDRN 세럼", "PDRN 앰플"] },
  { key: "retinol", label: "레티놀", keywords: ["레티놀", "레티놀 세럼", "레티놀 앰플"] },
];

export const CONCERN_SIGNAL_GROUPS: NaverDatalabKeywordGroup[] = [
  { key: "wrinkleElasticity", label: "주름/탄력", keywords: ["주름", "탄력", "안티에이징", "레티놀"] },
  { key: "toneSpot", label: "잡티/톤", keywords: ["잡티", "기미", "피부톤", "미백"] },
  { key: "troubleCalming", label: "트러블/진정", keywords: ["트러블", "여드름", "진정", "시카"] },
  { key: "drynessBarrier", label: "건조/장벽", keywords: ["건조", "보습", "피부장벽", "수분"] },
  { key: "poreSebum", label: "모공/피지", keywords: ["모공", "피지", "유분", "각질"] },
];

export const AGE_GROUPS = [
  { label: "20대", ages: ["3", "4"] },
  { label: "30대", ages: ["5", "6"] },
  { label: "40대", ages: ["7", "8"] },
  { label: "50대+", ages: ["9", "10", "11"] },
];

export function buildIngredientKeywordGroups(): NaverDatalabKeywordGroup[] {
  return PAGE2_MAIN_INGREDIENT_GROUPS;
}
