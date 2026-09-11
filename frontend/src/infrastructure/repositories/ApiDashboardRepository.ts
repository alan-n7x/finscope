import type { IDashboardRepository } from '../../domain/repositories/IDashboardRepository';
import { FinancialSummary } from '../../domain/value-objects/FinancialSummary';
import { Account } from '../../domain/entities/Account';
import { Debt } from '../../domain/entities/Debt';
import { HttpClient } from '../http/httpClient';

export class ApiDashboardRepository implements IDashboardRepository {
  async getDashboardSummary(month?: string, date?: string): Promise<FinancialSummary> {
    const params = new URLSearchParams();
    if (date) params.set('date', date);
    else if (month) params.set('month', month);
    const query = params.toString() ? `?${params.toString()}` : '';
    const data = await HttpClient.get<any>(`/api/dashboard${query}`);

    const accounts = (data.accounts || []).map(
      (a: any) => new Account({ name: a.name, type: a.type, balance: a.balance, balance_source: a.balance_source })
    );

    return new FinancialSummary({
      month: data.month,
      ref_date: data.ref_date,
      total_balance: data.total_balance,
      income_month: data.income_month,
      expense_month: data.expense_month,
      net_month: data.net_month,
      projected_final: data.projected_final,
      reserve_min: data.reserve_min,
      free_after_reserve: data.free_after_reserve,
      accounts,
      recommended_per_day: data.recommended_per_day ?? 0,
      spent_today: data.spent_today ?? 0,
      remaining_today: data.remaining_today ?? 0,
      days_remaining: data.days_remaining ?? 0,
      free_balance: data.free_balance ?? 0,
      status: data.status ?? 'NORMAL',
    });
  }

  async getDebtsSummary(): Promise<Debt[]> {
    const data = await HttpClient.get<any[]>('/api/debts');
    return (data || []).map((d: any) => new Debt(d));
  }
}
