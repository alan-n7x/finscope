import { FinancialSummary } from '../value-objects/FinancialSummary';
import { Debt } from '../entities/Debt';

export interface BalanceUpdateResult {
  account: string;
  balance: number;
  date: string;
  total_balance: number;
}

export interface IDashboardRepository {
  getDashboardSummary(month?: string, date?: string): Promise<FinancialSummary>;
  getDebtsSummary(): Promise<Debt[]>;
  updateAccountBalance(account: string, balance: number, date?: string): Promise<BalanceUpdateResult>;
}
