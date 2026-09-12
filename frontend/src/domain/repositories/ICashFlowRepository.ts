import type { CashFlowSeries } from '../value-objects/CashFlow';

export interface ICashFlowRepository {
  getCashFlow(month?: string, date?: string): Promise<CashFlowSeries>;
}
