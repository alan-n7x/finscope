import React, { useState } from 'react';
import { useDashboard } from '../../application/hooks/useDashboard';
import { KpiCardsGrid } from '../features/dashboard/KpiCardsGrid';
import { AccountsGrid } from '../features/dashboard/AccountsGrid';
import { PeriodSelector, currentPeriod } from '../features/dashboard/PeriodSelector';
import { DailyLimitCard } from '../features/dashboard/DailyLimitCard';

export const DashboardPage: React.FC = () => {
  const [selectedPeriod, setSelectedPeriod] = useState(currentPeriod());
  const { data: dashboardData, isLoading, isFetching } = useDashboard(selectedPeriod);

  const loading = isLoading || isFetching;
  const summary = dashboardData?.summary;
  const isEmpty =
    !loading &&
    summary !== undefined &&
    (summary.income_month ?? 0) === 0 &&
    (summary.expense_month ?? 0) === 0;

  return (
    <div className="page-content">
      <div className="page-header">
        <div className="page-title-group">
          <h1 className="page-title">Visão Geral</h1>
          <p className="page-subtitle">Resumo financeiro do mês</p>
        </div>
        <PeriodSelector value={selectedPeriod} onChange={setSelectedPeriod} />
      </div>

      <KpiCardsGrid summary={summary} selectedPeriod={selectedPeriod} loading={loading} />

      {!isEmpty && <DailyLimitCard summary={summary} loading={loading} />}

      {isEmpty ? (
        <div className="empty-state">Nenhum lançamento neste mês.</div>
      ) : (
        <AccountsGrid accounts={summary?.accounts} loading={loading} />
      )}
    </div>
  );
};
