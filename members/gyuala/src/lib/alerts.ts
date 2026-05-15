import type { AlertItem, AlertSeverity, AlertType } from "@/lib/types";

export type { AlertItem };

export type DailyAlertsPayload = {
  alertDate: string;
  summary: {
    opportunityCount: number;
    inventoryRiskCount: number;
    reviewIssueCount: number;
  };
  alerts: AlertItem[];
  notificationTargets?: unknown[];
};

export type DailyMetricSnapshot = {
  snapshotDate: string;
  ingredientMatrix: unknown[];
  reviewIssueSummary: unknown[];
  createdAt: string;
};

export const ALERT_TYPE_LABELS: Record<AlertType, string> = {
  opportunity: "신제품 기회",
  inventory_risk: "재고 리스크",
  review_issue: "부정 리뷰",
};

export const ALERT_SEVERITY_LABELS: Record<AlertSeverity, string> = {
  high: "High",
  medium: "Medium",
  low: "Low",
};

export function sortAlerts(alerts: AlertItem[]) {
  const severityWeight: Record<AlertSeverity, number> = { high: 3, medium: 2, low: 1 };
  return alerts.slice().sort((a, b) =>
    severityWeight[b.severity] - severityWeight[a.severity] ||
    String(a.title || "").localeCompare(String(b.title || ""), "ko-KR"),
  );
}

export function getHighSeverityNotificationTargets(alerts: AlertItem[]) {
  return sortAlerts(alerts).filter((alert) => alert.severity === "high" && !alert.is_sent);
}
