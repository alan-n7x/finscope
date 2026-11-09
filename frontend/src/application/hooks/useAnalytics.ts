import { useQuery } from '@tanstack/react-query';
import { ApiAnalyticsRepository } from '../../infrastructure/repositories/ApiAnalyticsRepository';
import { GetAnalyticsSummaryUseCase } from '../use-cases/GetAnalyticsSummaryUseCase';

const repository = new ApiAnalyticsRepository();
const useCase = new GetAnalyticsSummaryUseCase(repository);

export function useAnalytics(month?: string) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['analytics', month],
    queryFn: () => useCase.execute(month),
  });

  return {
    categoryData: data?.getItems() ?? [],
    totalExpenses: data?.getTotalExpense() ?? 0,
    isLoading,
    isError,
  };
}
