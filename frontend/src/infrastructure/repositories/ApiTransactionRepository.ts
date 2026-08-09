import type {
  ITransactionRepository,
  TransactionFilterParams,
  CreateTransactionDTO,
  FilterOptions,
} from '../../domain/repositories/ITransactionRepository';
import { Transaction } from '../../domain/entities/Transaction';
import { HttpClient } from '../http/httpClient';

export class ApiTransactionRepository implements ITransactionRepository {
  async getTransactions(params?: TransactionFilterParams): Promise<Transaction[]> {
    const searchParams = new URLSearchParams();
    if (params?.month) searchParams.append('month', params.month);
    if (params?.category) searchParams.append('category', params.category);
    if (params?.search) searchParams.append('search', params.search);
    if (params?.status) searchParams.append('status', params.status);
    if (params?.limit) searchParams.append('limit', params.limit.toString());

    const query = searchParams.toString() ? `?${searchParams.toString()}` : '';
    const data = await HttpClient.get<any[]>(`/api/transactions${query}`);

    return (data || []).map((t: any) => new Transaction(t));
  }

  async createTransaction(dto: CreateTransactionDTO): Promise<Transaction> {
    const data = await HttpClient.post<any>('/api/transactions', dto);
    return new Transaction(data);
  }

  async getFilterOptions(): Promise<FilterOptions> {
    return HttpClient.get<FilterOptions>('/api/options');
  }
}
