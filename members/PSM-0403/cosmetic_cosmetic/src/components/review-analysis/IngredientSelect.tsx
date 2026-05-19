import { REVIEW_INGREDIENT_OPTIONS } from "@/lib/reviewConstants";

export function IngredientSelect({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <select
      className="review-ingredient-select"
      value={value}
      onChange={(event) => onChange(event.target.value)}
      aria-label="리뷰 분석 성분 선택"
    >
      {REVIEW_INGREDIENT_OPTIONS.map((ingredient) => (
        <option value={ingredient} key={ingredient}>
          {ingredient}
        </option>
      ))}
    </select>
  );
}
