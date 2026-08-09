import type { ITransactionRepository, TransactionFilterParams } from '../../domain/repositories/ITransactionRepository';
import { Transaction } from '../../domain/entities/Transaction';

export class ListTransactionsUseCase {
  private repository: ITransactionRepository;

  constructor(repository: ITransactionRepository) {
    this.repository = repository;
  }

  async execute(params?: TransactionFilterParams): Promise<Transaction[]> {
    return this.repository.getTransactions(params);
  }
}
