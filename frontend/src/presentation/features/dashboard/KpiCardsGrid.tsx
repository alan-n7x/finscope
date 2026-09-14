import React from 'react';
import { FinancialSummary } from '../../../domain/value-objects/FinancialSummary';
import { Card } from '../../components/ui/Card';
import { TrendingUp, TrendingDown, Wallet } from 'lucide-react';

interface KpiCardsGridProps {
  summary?: FinancialSummary;
  selectedPeriod?: string;
  loading?: boolean;
}

export const KpiCardsGrid: React.FC<KpiCardsGridProps> = ({ summary, selectedPeriod, loading = false }) => {
  const formatCurrency = (val?: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    }).format(val || 0);
  };

  const monthName = summary?.month || 'Mês Selecionado';

  const balanceFooter = selectedPeriod
    ? (() => {
        const [yearStr, monthStr] = selectedPeriod.split('-');
        const formatted = new Intl.DateTimeFormat('pt-BR', {
          month: 'long',
          year: 'numeric',
        }).format(new Date(Number(yearStr), Number(monthStr) - 1, 1));
        return `Saldo ao final de ${formatted}`;
      })()
    : 'Soma dos saldos bancários';

  if (loading && !summary) {
    return (
      <section className="kpi-grid" aria-busy="true" aria-label="Carregando resumo">
        {[0, 1, 2].map((idx) => (
          <Card key={idx} className="kpi-card">
            <div className="skeleton skeleton-text" />
            <div className="skeleton skeleton-value" />
            <div className="skeleton skeleton-text" />
          </Card>
        ))}
      </section>
    );
  }

  return (
    <section className="kpi-grid" aria-busy={loading}>
      <Card className="kpi-card card-hover">
        <div className="kpi-header">
          <span>Saldo Total em Conta</span>
          <div className="kpi-icon balance-icon">
            <Wallet size={20} className="text-blue-400" />
          </div>
        </div>
        <div className="kpi-value">{formatCurrency(summary?.total_balance)}</div>
        <div className="kpi-footer">{balanceFooter}</div>
      </Card>

      <Card className="kpi-card card-hover">
        <div className="kpi-header">
          <span>Receitas do Mês</span>
          <div className="kpi-icon income-icon">
            <TrendingUp size={20} className="text-emerald-400" />
          </div>
        </div>
        <div className="kpi-value positive">+{formatCurrency(summary?.income_month)}</div>
        <div className="kpi-footer">Entradas confirmadas em {monthName}</div>
      </Card>

      <Card className="kpi-card card-hover">
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
