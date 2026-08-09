import React, { useState } from 'react';
import { useDashboard } from '../../application/hooks/useDashboard';
import { KpiCardsGrid } from '../features/dashboard/KpiCardsGrid';
import { AccountsGrid } from '../features/dashboard/AccountsGrid';

export const DashboardPage: React.FC = () => {
  const [selectedMonth] = useState('2026-08');
  const { data: dashboardData } = useDashboard(selectedMonth);

  return (
    <div className="page-content">
      <div className="page-header">
        <div className="page-title-group">
          <h1 className="page-title">Visão Geral</h1>
          <p className="page-subtitle">Resumo financeiro do mês</p>
        </div>
        <span className="month-pill">{selectedMonth}</span>
      </div>

      <KpiCardsGrid summary={dashboardData?.summary} />

      <AccountsGrid accounts={dashboardData?.summary?.accounts} />
    </div>
  );
};
