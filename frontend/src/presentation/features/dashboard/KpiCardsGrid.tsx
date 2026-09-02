import React from 'react';
import { FinancialSummary } from '../../../domain/value-objects/FinancialSummary';
import { Card } from '../../components/ui/Card';
import { TrendingUp, TrendingDown, Wallet } from 'lucide-react';

interface KpiCardsGridProps {
  summary?: FinancialSummary;
  selectedDate?: string;
}

export const KpiCardsGrid: React.FC<KpiCardsGridProps> = ({ summary, selectedDate }) => {
  const formatCurrency = (val?: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    }).format(val || 0);
  };

  const monthName = summary?.month || 'Mês Selecionado';

  const balanceFooter = selectedDate
    ? `Saldo em ${new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(selectedDate + 'T12:00:00'))}`
    : 'Soma dos saldos bancários';

  return (
    <section className="kpi-grid">
      <Card className="kpi-card">
        <div className="kpi-header">
          <span>Saldo Total em Conta</span>
          <div className="kpi-icon balance-icon">
            <Wallet size={20} className="text-blue-400" />
          </div>
        </div>
        <div className="kpi-value">{formatCurrency(summary?.total_balance)}</div>
        <div className="kpi-footer">{balanceFooter}</div>
      </Card>

      <Card className="kpi-card">
        <div className="kpi-header">
          <span>Receitas do Mês</span>
          <div className="kpi-icon income-icon">
            <TrendingUp size={20} className="text-emerald-400" />
          </div>
        </div>
        <div className="kpi-value positive">+{formatCurrency(summary?.income_month)}</div>
        <div className="kpi-footer">Entradas confirmadas em {monthName}</div>
      </Card>

      <Card className="kpi-card">
        <div className="kpi-header">
          <span>Despesas do Mês</span>
          <div className="kpi-icon expense-icon">
            <TrendingDown size={20} className="text-rose-400" />
          </div>
        </div>
        <div className="kpi-value negative">-{formatCurrency(summary?.expense_month)}</div>
        <div className="kpi-footer">Saídas confirmadas em {monthName}</div>
      </Card>

    </section>
  );
};
