import React, { useState } from 'react';
import { useDashboard } from '../../application/hooks/useDashboard';
import { KpiCardsGrid } from '../features/dashboard/KpiCardsGrid';
import { AccountsGrid } from '../features/dashboard/AccountsGrid';
import { Calendar } from 'lucide-react';

const todayISO = () => new Date().toISOString().split('T')[0];

export const DashboardPage: React.FC = () => {
  const [selectedDate, setSelectedDate] = useState(todayISO());
  const { data: dashboardData } = useDashboard(undefined, selectedDate);

  // Formata a data selecionada para exibicao amigavel
  const displayDate = selectedDate
    ? new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' }).format(
        new Date(selectedDate + 'T12:00:00')
      )
    : 'Hoje';

  return (
    <div className="page-content">
      <div className="page-header">
        <div className="page-title-group">
          <h1 className="page-title">Visão Geral</h1>
          <p className="page-subtitle">Resumo financeiro do mês</p>
        </div>
        <label className="date-picker-pill" title="Selecione uma data de referência">
          <Calendar size={13} />
          <span>{displayDate}</span>
          <input
            id="dashboard-date-picker"
            type="date"
            value={selectedDate}
            max={todayISO()}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="date-picker-input"
          />
        </label>
      </div>

      <KpiCardsGrid summary={dashboardData?.summary} selectedDate={selectedDate} />

      <AccountsGrid accounts={dashboardData?.summary?.accounts} />
    </div>
  );
};
