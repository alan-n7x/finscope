import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ApiDashboardRepository } from '../../infrastructure/repositories/ApiDashboardRepository';
import { UpdateAccountBalanceUseCase } from '../use-cases/UpdateAccountBalanceUseCase';

const repository = new ApiDashboardRepository();
const updateBalanceUseCase = new UpdateAccountBalanceUseCase(repository);

export interface UpdateBalanceInput {
  account: string;
  balance: number;
  date?: string;
}

export function useUpdateAccountBalance() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: UpdateBalanceInput) =>
      updateBalanceUseCase.execute(input.account, input.balance, input.date),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['cash-flow'] });
    },
  });
}
