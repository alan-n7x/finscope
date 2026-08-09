import { Transaction } from '../../domain/entities/Transaction';
import { CategoryAnalytics } from '../../domain/value-objects/CategoryAnalytics';
import type { CategoryItemProps } from '../../domain/value-objects/CategoryAnalytics';

const CATEGORY_COLORS: Record<string, string> = {
  'Alimentação': '#ef4444',
  'Dívidas': '#f59e0b',
  'Carro': '#3b82f6',
  'Transporte': '#60a5fa',
  'Moradia': '#8b5cf6',
  'Telefone': '#ec4899',
  'Outros': '#94a3b8',
};

const DEFAULT_COLOR_PALETTE = [
  '#ef4444', '#f59e0b', '#3b82f6', '#8b5cf6',
  '#ec4899', '#10b981', '#06b6d4', '#64748b'
];

export class GetAnalyticsSummaryUseCase {
  executeCategoryDistribution(transactions: Transaction[]): CategoryAnalytics {
    const categoryTotals: Record<string, number> = {};
    let totalExpenses = 0;

    for (const tx of transactions) {
      if (tx.isExpense() && tx.isPaid()) {
        const cat = tx.category || 'Outros';
        categoryTotals[cat] = (categoryTotals[cat] || 0) + tx.amount;
        totalExpenses += tx.amount;
      }
    }

    const items: CategoryItemProps[] = Object.entries(categoryTotals)
      .map(([name, value], idx) => {
        const percentage = totalExpenses > 0 ? (value / totalExpenses) * 100 : 0;
        const color = CATEGORY_COLORS[name] || DEFAULT_COLOR_PALETTE[idx % DEFAULT_COLOR_PALETTE.length];
        return {
          name,
          value: Number(value.toFixed(2)),
          percentage: Number(percentage.toFixed(1)),
          color,
        };
      })
      .sort((a, b) => b.value - a.value);

    return new CategoryAnalytics(items);
  }
}
