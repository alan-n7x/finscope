import { useQuery } from '@tanstack/react-query';
import { ApiDashboardRepository } from '../../infrastructure/repositories/ApiDashboardRepository';
import { GetDashboardSummaryUseCase } from '../use-cases/GetDashboardSummaryUseCase';

const repository = new ApiDashboardRepository();
const getDashboardUseCase = new GetDashboardSummaryUseCase(repository);

export function useDashboard(month?: string) {
  return useQuery({
    queryKey: ['dashboard', month],
    queryFn: () => getDashboardUseCase.execute(month),
  });
}
