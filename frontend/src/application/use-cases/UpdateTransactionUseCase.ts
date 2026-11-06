import type {
  ITransactionRepository,
  UpdateTransactionDTO,
} from '../../domain/repositories/ITransactionRepository';
import { Transaction } from '../../domain/entities/Transaction';

export class UpdateTransactionUseCase {
  private repository: ITransactionRepository;

  constructor(repository: ITransactionRepository) {
    this.repository = repository;
  }

  async execute(id: string, dto: UpdateTransactionDTO): Promise<Transaction> {
    return this.repository.updateTransaction(id, dto);
  }
}
