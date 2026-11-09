import React from 'react';
import { CategoryDonutChart } from './CategoryDonutChart';
import { MonthlyTrendChart } from './MonthlyTrendChart';
import { useAnalytics } from '../../../application/hooks/useAnalytics';
import { FinancialSummary } from '../../../domain/value-objects/FinancialSummary';

interface AnalyticsSectionProps {
  month: string;
  summary?: FinancialSummary;
}

export const AnalyticsSection: React.FC<AnalyticsSectionProps> = ({ month, summary }) => {
  const { categoryData, totalExpenses } = useAnalytics(month);

  return (
    <section className="analytics-section">
      <CategoryDonutChart data={categoryData} totalExpenses={totalExpenses} />
      <MonthlyTrendChart summary={summary} />
    </section>
  );
};
