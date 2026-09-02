import { FinancialSummary } from '../value-objects/FinancialSummary';
import { Debt } from '../entities/Debt';

export interface IDashboardRepository {
  getDashboardSummary(month?: string, date?: string): Promise<FinancialSummary>;
  getDebtsSummary(): Promise<Debt[]>;
}
