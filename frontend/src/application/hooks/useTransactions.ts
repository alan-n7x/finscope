import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ApiTransactionRepository } from '../../infrastructure/repositories/ApiTransactionRepository';
import { ListTransactionsUseCase } from '../use-cases/ListTransactionsUseCase';
import { CreateTransactionUseCase } from '../use-cases/CreateTransactionUseCase';
import type { TransactionFilterParams, CreateTransactionDTO } from '../../domain/repositories/ITransactionRepository';

const repository = new ApiTransactionRepository();
const listUseCase = new ListTransactionsUseCase(repository);
const createUseCase = new CreateTransactionUseCase(repository);

export function useTransactions(params?: TransactionFilterParams) {
  return useQuery({
    queryKey: ['transactions', params],
    queryFn: () => listUseCase.execute(params),
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
