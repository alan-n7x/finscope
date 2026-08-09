import React, { useState } from 'react';
import { useDashboard } from '../../application/hooks/useDashboard';
import { DebtsSidebar } from '../features/debts/DebtsSidebar';

export const DiviasPage: React.FC = () => {
  const [selectedMonth] = useState('2026-08');
  const { data: dashboardData } = useDashboard(selectedMonth);

  return (
    <div className="page-content">
      <div className="page-header">
        <div className="page-title-group">
          <h1 className="page-title">Dívidas & Compromissos</h1>
          <p className="page-subtitle">Parcelas e vencimentos em aberto</p>
        </div>
      </div>

      <DebtsSidebar debts={dashboardData?.debts || []} fullPage />
    </div>
  );
};
