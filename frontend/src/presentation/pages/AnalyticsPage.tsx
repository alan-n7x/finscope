import React, { useState } from 'react';
import { useDashboard } from '../../application/hooks/useDashboard';
import { AnalyticsSection } from '../features/analytics/AnalyticsSection';
import { PeriodSelector, currentPeriod } from '../features/dashboard/PeriodSelector';

export const AnalyticsPage: React.FC = () => {
  const [selectedMonth, setSelectedMonth] = useState(currentPeriod());
  const { data: dashboardData } = useDashboard(selectedMonth);

  return (
    <div className="page-content">
      <div className="page-header">
        <div className="page-title-group">
          <h1 className="page-title">Analytics</h1>
          <p className="page-subtitle">Gastos por categoria e tendências</p>
        </div>
        <PeriodSelector value={selectedMonth} onChange={setSelectedMonth} />
      </div>

      <AnalyticsSection month={selectedMonth} summary={dashboardData?.summary} />
    </div>
  );
};
