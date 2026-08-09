import { Transaction } from '../entities/Transaction';

export interface TransactionFilterParams {
  month?: string;
  category?: string;
  search?: string;
  status?: string;
  limit?: number;
}

export interface CreateTransactionDTO {
  date: string;
  type: string;
  category: string;
  description: string;
  payment_method: string;
  amount: number;
  essential: boolean;
  paid: boolean;
  obs?: string;
  account: string;
}

export interface FilterOptions {
  categories: string[];
  payment_methods: string[];
  accounts: string[];
  months: string[];
  types: string[];
}

export interface ITransactionRepository {
  getTransactions(params?: TransactionFilterParams): Promise<Transaction[]>;
  createTransaction(data: CreateTransactionDTO): Promise<Transaction>;
  getFilterOptions(): Promise<FilterOptions>;
}
