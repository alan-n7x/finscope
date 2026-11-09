import type {
  AnalyticsSummaryDTO,
  IAnalyticsRepository,
} from '../../domain/repositories/IAnalyticsRepository';
import { HttpClient } from '../http/httpClient';

export class ApiAnalyticsRepository implements IAnalyticsRepository {
  async getSummary(month?: string): Promise<AnalyticsSummaryDTO> {
    const query = month ? `?month=${encodeURIComponent(month)}` : '';
    return HttpClient.get<AnalyticsSummaryDTO>(`/api/analytics/summary${query}`);
  }
}
