import type { ICashFlowRepository } from '../../domain/repositories/ICashFlowRepository';
import type { CashFlowSeries } from '../../domain/value-objects/CashFlow';
import { HttpClient } from '../http/httpClient';

export class ApiCashFlowRepository implements ICashFlowRepository {
  async getCashFlow(month?: string, date?: string): Promise<CashFlowSeries> {
    const params = new URLSearchParams();
    if (date) params.set('date', date);
    else if (month) params.set('month', month);
    const query = params.toString() ? `?${params.toString()}` : '';
    return HttpClient.get<CashFlowSeries>(`/api/dashboard/cash-flow${query}`);
  }
}
