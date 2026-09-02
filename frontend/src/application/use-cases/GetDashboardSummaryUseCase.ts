import type { IDashboardRepository } from '../../domain/repositories/IDashboardRepository';
import { FinancialSummary } from '../../domain/value-objects/FinancialSummary';
import { Debt } from '../../domain/entities/Debt';

export class GetDashboardSummaryUseCase {
  private repository: IDashboardRepository;

  constructor(repository: IDashboardRepository) {
    this.repository = repository;
  }

  async execute(month?: string, date?: string): Promise<{ summary: FinancialSummary; debts: Debt[] }> {
    const [summary, debts] = await Promise.all([
      this.repository.getDashboardSummary(month, date),
      this.repository.getDebtsSummary(),
    ]);
    return { summary, debts };
  }
}
