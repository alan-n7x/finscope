import { useMemo } from 'react';
import { Transaction } from '../../domain/entities/Transaction';
import { GetAnalyticsSummaryUseCase } from '../use-cases/GetAnalyticsSummaryUseCase';

const useCase = new GetAnalyticsSummaryUseCase();

export function useAnalytics(transactions: Transaction[]) {
  const categoryAnalytics = useMemo(() => {
    return useCase.executeCategoryDistribution(transactions);
  }, [transactions]);

  return {
    categoryData: categoryAnalytics.getItems(),
    totalExpenses: categoryAnalytics.getTotalExpense(),
  };
}
