import type { IDashboardRepository, BalanceUpdateResult } from '../../domain/repositories/IDashboardRepository';

export class UpdateAccountBalanceUseCase {
  private repository: IDashboardRepository;

  constructor(repository: IDashboardRepository) {
    this.repository = repository;
  }

  async execute(account: string, balance: number, date?: string): Promise<BalanceUpdateResult> {
    return this.repository.updateAccountBalance(account, balance, date);
  }
}
