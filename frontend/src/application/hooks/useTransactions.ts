import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ApiTransactionRepository } from '../../infrastructure/repositories/ApiTransactionRepository';
import { ListTransactionsUseCase } from '../use-cases/ListTransactionsUseCase';
import { CreateTransactionUseCase } from '../use-cases/CreateTransactionUseCase';
import { GetTransactionUseCase } from '../use-cases/GetTransactionUseCase';
import { UpdateTransactionUseCase } from '../use-cases/UpdateTransactionUseCase';
import type {
  TransactionFilterParams,
  CreateTransactionDTO,
  UpdateTransactionDTO,
} from '../../domain/repositories/ITransactionRepository';
import { Transaction } from '../../domain/entities/Transaction';

const repository = new ApiTransactionRepository();
const listUseCase = new ListTransactionsUseCase(repository);
const createUseCase = new CreateTransactionUseCase(repository);
const getUseCase = new GetTransactionUseCase(repository);
const updateUseCase = new UpdateTransactionUseCase(repository);

export function useTransactions(params?: TransactionFilterParams) {
  return useQuery({
    queryKey: ['transactions', params],
    queryFn: () => listUseCase.execute(params),
  });
}

export function useTransaction(id?: string, initialData?: Transaction) {
  return useQuery({
    queryKey: ['transaction', id],
    queryFn: () => getUseCase.execute(id as string),
    enabled: Boolean(id),
    initialData,
    // Usa os dados da linha na hora, mas revalida em background.
    initialDataUpdatedAt: 0,
  });
}

export function useFilterOptions() {
  return useQuery({
    queryKey: ['filter-options'],
    queryFn: () => repository.getFilterOptions(),
  });
}

export function useCreateTransaction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (dto: CreateTransactionDTO) => createUseCase.execute(dto),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

export function useUpdateTransaction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, dto }: { id: string; dto: UpdateTransactionDTO }) =>
      updateUseCase.execute(id, dto),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      queryClient.invalidateQueries({ queryKey: ['transaction'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['cash-flow'] });
      queryClient.invalidateQueries({ queryKey: ['filter-options'] });
    },
  });
}
