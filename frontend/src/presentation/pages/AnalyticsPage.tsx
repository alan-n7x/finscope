import React, { useState } from 'react';
import { useTransactions } from '../../application/hooks/useTransactions';
import { useDashboard } from '../../application/hooks/useDashboard';
import { AnalyticsSection } from '../features/analytics/AnalyticsSection';

export const AnalyticsPage: React.FC = () => {
  const [selectedMonth] = useState('2026-08');
  const { data: dashboardData } = useDashboard(selectedMonth);
  const { data: transactions = [] } = useTransactions({ month: selectedMonth });

  return (
    <div className="page-content">
      <div className="page-header">
        <div className="page-title-group">
          <h1 className="page-title">Analytics</h1>
          <p className="page-subtitle">Gastos por categoria e tendências</p>
        </div>
        <span className="month-pill">{selectedMonth}</span>
      </div>

      <AnalyticsSection transactions={transactions} summary={dashboardData?.summary} />
    </div>
  );
};
