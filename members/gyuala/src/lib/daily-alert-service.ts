import type { DailyAlertsPayload } from "@/lib/alerts";
import { SupabaseAlertsRepository, createServerSupabaseClient } from "@/lib/alert-repository";
import type { AlertItem } from "@/lib/types";

type EnsureDailyAlertsOptions = {
  alertDate?: string;
  forceRefresh?: boolean;
  requestUrl: string;
};

export async function ensureDailyAlerts({
  alertDate,
}: EnsureDailyAlertsOptions): Promise<DailyAlertsPayload> {
  const resolvedAlertDate = alertDate || await getLatestAlertDate();
  if (!resolvedAlertDate) {
    return {
      alertDate: alertDate || new Date().toISOString().slice(0, 10),
      summary: {
        opportunityCount: 0,
        inventoryRiskCount: 0,
        reviewIssueCount: 0,
      },
      alerts: [],
    };
  }

  const repository = new SupabaseAlertsRepository();
  const alerts = await repository.listAlertsByDate(resolvedAlertDate);

  return {
    alertDate: resolvedAlertDate,
    summary: summarizeAlerts(alerts),
    alerts,
  };
}

async function getLatestAlertDate() {
  const supabase = createServerSupabaseClient();
  const { data, error } = await supabase
    .from("alerts")
    .select("alert_date")
    .order("alert_date", { ascending: false })
    .limit(1);

  if (error) throw new Error(`alerts 최신일 조회 실패: ${error.message}`);
  return String(data?.[0]?.alert_date || "").slice(0, 10);
}

function summarizeAlerts(alerts: AlertItem[]): DailyAlertsPayload["summary"] {
  return {
    opportunityCount: alerts.filter((alert) => alert.alert_type === "opportunity").length,
    inventoryRiskCount: alerts.filter((alert) => alert.alert_type === "inventory_risk").length,
    reviewIssueCount: alerts.filter((alert) => alert.alert_type === "review_issue").length,
  };
}
