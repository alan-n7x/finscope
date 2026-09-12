import React from 'react';
import { FinancialSummary } from '../../../domain/value-objects/FinancialSummary';
import { Card } from '../../components/ui/Card';

interface DailyLimitCardProps {
  summary?: FinancialSummary;
  loading?: boolean;
}

const STATUS_META: Record<string, { label: string; className: string }> = {
  NORMAL: { label: 'Dentro do limite', className: 'badge-status-paid' },
  WARNING: { label: 'Atenção', className: 'badge-status-pending' },
  EXCEEDED: { label: 'Estourado', className: 'badge-type-despesa' },
};

export const DailyLimitCard: React.FC<DailyLimitCardProps> = ({ summary, loading = false }) => {
  const formatCurrency = (val?: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    }).format(val || 0);
  };

  if (loading && !summary) {
    return (
      <section className="section-container" aria-busy="true" aria-label="Carregando limite diário">
        <Card className="kpi-card">
          <div className="skeleton skeleton-text" />
          <div className="skeleton skeleton-value" />
          <div className="skeleton skeleton-bar" />
        </Card>
      </section>
    );
  }

  const recommended = summary?.recommended_per_day ?? 0;
  const spent = summary?.spent_today ?? 0;
  const remaining = summary?.remaining_today ?? 0;
  const days = summary?.days_remaining ?? 0;
  const status = summary?.status ?? 'NORMAL';
  const meta = STATUS_META[status] ?? STATUS_META.NORMAL;

  const progress = recommended > 0 ? Math.min(spent / recommended, 1) : spent > 0 ? 1 : 0;
  const barClass =
    status === 'EXCEEDED' ? 'daily-bar-fill exceeded' : status === 'WARNING' ? 'daily-bar-fill warning' : 'daily-bar-fill';

  return (
    <section className="section-container">
      <Card className="kpi-card card-interactive">
        <div className="kpi-header">
          <span>Limite Diário Recomendado</span>
          <span className={`badge ${meta.className}`}>{meta.label}</span>
        </div>
        <div className="kpi-value">{formatCurrency(recommended)}/dia</div>
        <div className="daily-bar" role="progressbar" aria-valuenow={Math.round(progress * 100)} aria-valuemin={0} aria-valuemax={100} aria-label="Progresso do gasto de hoje">
          <div className={barClass} style={{ width: `${Math.round(progress * 100)}%` }} />
        </div>
        <div className="kpi-footer">
          Gasto hoje: {formatCurrency(spent)} · Restam hoje: {formatCurrency(remaining)} · {days} {days === 1 ? 'dia restante' : 'dias restantes'}
        </div>
      </Card>
    </section>
  );
};
