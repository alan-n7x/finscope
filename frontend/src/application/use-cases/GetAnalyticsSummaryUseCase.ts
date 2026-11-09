import type { IAnalyticsRepository } from '../../domain/repositories/IAnalyticsRepository';
import { CategoryAnalytics } from '../../domain/value-objects/CategoryAnalytics';
import type { CategoryItemProps } from '../../domain/value-objects/CategoryAnalytics';

const CATEGORY_COLORS: Record<string, string> = {
  'Alimentação': '#ef4444',
  'Assinaturas': '#8b5cf6',
  'Carro': '#3b82f6',
  'Dívidas': '#f59e0b',
  'Estorno / Reembolso': '#06b6d4',
  'Outros': '#94a3b8',
  'Salário': '#10b981',
  'Telefone': '#ec4899',
  'Transferência interna': '#64748b',
  'Transporte': '#60a5fa',
  'Moradia': '#8b5cf6',
};

const DEFAULT_COLOR_PALETTE = [
  '#ef4444', '#f59e0b', '#3b82f6', '#8b5cf6',
  '#ec4899', '#10b981', '#06b6d4', '#64748b'
];

export class GetAnalyticsSummaryUseCase {
  private repository: IAnalyticsRepository;

  constructor(repository: IAnalyticsRepository) {
    this.repository = repository;
  }

  async execute(month?: string): Promise<CategoryAnalytics> {
    const summary = await this.repository.getSummary(month);

    const items: CategoryItemProps[] = summary.categories.map((category, idx) => ({
      name: category.name,
      value: category.value,
      percentage: category.percentage,
      color:
        CATEGORY_COLORS[category.name] ||
        DEFAULT_COLOR_PALETTE[idx % DEFAULT_COLOR_PALETTE.length],
    }));

    return new CategoryAnalytics(items, summary.total_expenses);
  }
}
