import type { ITransactionRepository } from '../../domain/repositories/ITransactionRepository';
import { Transaction } from '../../domain/entities/Transaction';

export class GetTransactionUseCase {
  private repository: ITransactionRepository;

  constructor(repository: ITransactionRepository) {
    this.repository = repository;
  }

  async execute(id: string): Promise<Transaction> {
    return this.repository.getTransaction(id);
  }
}
