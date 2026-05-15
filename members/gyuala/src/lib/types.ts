export type Page1Summary = {
  analyzedProducts: number;
  analyzedIngredients: number;
  totalSearchGrowthRate: number;
  risingIngredientCount: number;
  supplyShortageIngredientCount: number;
};

export type DashboardMeta = {
  dataRange: string;
  lastUpdated: string;
  comparisonLabel: string;
  apiSource?: string;
  source?: string;
  warnings?: string[];
};

export type RankItem = {
  key?: string;
  label: string;
  score?: number;
  growth?: number;
  searchIndex?: number;
  currentWeekIndex?: number;
  previousWeekIndex?: number;
  weekOverWeekGrowthRate?: number;
  currentWeekSearchIndex?: number;
  averageRank?: number;
  bestRank?: number;
  productCount?: number;
};

export type PriceDistributionPoint = {
  value: number;
  ingredient: string;
  productName?: string;
  goodsNo?: string;
  basisPrice?: number | null;
  regularPrice?: number | null;
  salesPrice?: number | null;
  volumeMl?: number | null;
  priceType?: "sale" | "list" | string;
};

export type PriceDistributionItem = {
  ingredient: string;
  salePrices?: number[];
  listPrices?: number[];
  prices?: number[];
  salePricePoints?: PriceDistributionPoint[];
  listPricePoints?: PriceDistributionPoint[];
};

export type DemandSupplyStatus = "growth" | "shortage" | "opportunity" | "oversupply" | "stable";

export type DemandSupplyItem = {
  ingredient: string;
  demand: number;
  supply: number;
  growth: number;
  status: DemandSupplyStatus;
  size: number;
  previousDemand?: number;
  previousSupply?: number;
  demandWow?: number;
  supplyWow?: number;
  supplyCount?: number;
  gap?: number;
  opportunityScore?: number;
};

export type SearchTrendSeries = {
  ingredient: string;
  values: number[];
  color?: string;
};

export type ConcernMetric = {
  key: string;
  label: string;
  legacyKey?: string;
};

export type MarketProduct = {
  ingredient_key: string;
  ingredient_label: string;
  product_count: number;
  previous_product_count: number;
  product_growth_rate?: number;
  product_growth_count?: number;
  source?: string;
};

export type AlertSeverity = "high" | "medium" | "low";
export type AlertType = "opportunity" | "inventory_risk" | "review_issue";

export type AlertItem = {
  id: string;
  alert_date: string;
  alert_type: AlertType;
  severity: AlertSeverity;
  title: string;
  ingredient_name: string;
  product_name?: string | null;
  summary: string;
  detected_metric_name: string;
  detected_metric_value: string | number | null;
  baseline_metric_value?: string | number | null;
  reason_json: Record<string, unknown> & {
    reasons?: string[];
    metrics?: Record<string, string | number>;
    relatedLowKeywords?: Array<{ keyword?: string; count?: number }>;
  };
  action_items_json: string[];
  is_sent?: boolean;
  sent_channel?: string | null;
  created_at?: string;
};

export type AgentInsight = {
  id: string;
  title: string;
  level: string;
  summary: string;
  evidence: string;
  strategy: string;
  targetTitle?: string;
  issues?: string[];
  directions?: string[];
  actions?: string[];
  detailSections?: Array<{ title: string; items: string[] }>;
  downloadable?: boolean;
  downloadTitle?: string;
};

export type TargetStrategy = {
  title: string;
  targetTitle?: string;
  issues: string[];
  directions: string[];
  actions: string[];
};

export type DashboardData = {
  meta: DashboardMeta;
  page1Summary: Page1Summary;
  page1: {
    functionRisers: RankItem[];
    functionDemand?: RankItem[];
    ingredientPopularity: RankItem[];
    ingredientDemand?: RankItem[];
    priceDistribution: PriceDistributionItem[];
    demandSupplyMatrix: DemandSupplyItem[];
    insights: string[];
  };
  page2: {
    periodLabel: string;
    selectedIngredient: string;
    selectedSummary: Record<string, unknown> & { growthRate?: number };
    searchTrend: {
      dates: string[];
      series: SearchTrendSeries[];
    };
    concernMetrics: ConcernMetric[];
    marketProducts: MarketProduct[];
    concernTable: Array<Record<string, string | number>>;
    ageTopIngredients: unknown[];
    insights: string[];
  };
  page3: Record<string, unknown>;
  page4: {
    alertDate: string;
    summary: {
      opportunityCount: number;
      inventoryRiskCount: number;
      reviewIssueCount: number;
    };
    alerts: AlertItem[];
  };
  page5: {
    promptPlaceholder: string;
    suggestions: string[];
    insights: AgentInsight[];
    targetStrategy: TargetStrategy;
  };
};
