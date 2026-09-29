export type ChartPoint = { date: string; index: number };
export type Summary = { available: boolean; national_index?: number; base_period?: number; daily_change?: number; weekly_change?: number; monthly_change?: number; observations?: number; available_observations?: number; data_quality?: number; last_updated?: string; message?: string; source?: string; weight_note?: string };
export type RouteIndex = { route: string; index: number; current_fare: number; base_fare: number; weight: number; contribution_points?: number };
export type LeadPoint = { lead_days: number; label: string; current_fare: number; historical_median: number; change_pct: number };
export type Airline = { airline: string; average_fare: number; observations: number };
export type Shock = { route: string; current_fare: number; historical_reference: number; change_pct: number; severity: "NORMAL" | "ELEVATED" | "SHOCK"; timestamp: string; threshold_pct: number };
