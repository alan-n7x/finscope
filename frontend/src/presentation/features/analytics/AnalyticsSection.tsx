import React from 'react';
import { CategoryDonutChart } from './CategoryDonutChart';
import { MonthlyTrendChart } from './MonthlyTrendChart';
import { useAnalytics } from '../../../application/hooks/useAnalytics';
import { Transaction } from '../../../domain/entities/Transaction';
import { FinancialSummary } from '../../../domain/value-objects/FinancialSummary';

interface AnalyticsSectionProps {
  transactions: Transaction[];
  summary?: FinancialSummary;
}

export const AnalyticsSection: React.FC<AnalyticsSectionProps> = ({ transactions, summary }) => {
  const { categoryData, totalExpenses } = useAnalytics(transactions);

  return (
    <section className="analytics-section">
      <CategoryDonutChart data={categoryData} totalExpenses={totalExpenses} />
      <MonthlyTrendChart summary={summary} />
    </section>
  );
};
