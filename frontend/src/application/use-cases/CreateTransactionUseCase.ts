import type { ITransactionRepository, CreateTransactionDTO } from '../../domain/repositories/ITransactionRepository';
import { Transaction } from '../../domain/entities/Transaction';

export class CreateTransactionUseCase {
  private repository: ITransactionRepository;

  constructor(repository: ITransactionRepository) {
    this.repository = repository;
  }

  async execute(dto: CreateTransactionDTO): Promise<Transaction> {
    return this.repository.createTransaction(dto);
  }
}
