export interface AnalyticsCategoryDTO {
  name: string;
  value: number;
  percentage: number;
}

export interface AnalyticsSummaryDTO {
  month: string;
  total_expenses: number;
  categories: AnalyticsCategoryDTO[];
}

export interface IAnalyticsRepository {
  getSummary(month?: string): Promise<AnalyticsSummaryDTO>;
}
