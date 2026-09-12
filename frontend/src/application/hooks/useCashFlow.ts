import { useQuery } from '@tanstack/react-query';
import { ApiCashFlowRepository } from '../../infrastructure/repositories/ApiCashFlowRepository';

const repository = new ApiCashFlowRepository();

export function useCashFlow(month?: string, date?: string) {
  return useQuery({
    queryKey: ['cash-flow', month, date],
    queryFn: () => repository.getCashFlow(month, date),
  });
}
