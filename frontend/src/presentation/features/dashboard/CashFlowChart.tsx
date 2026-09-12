import React from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
  ReferenceDot,
} from 'recharts';
import type { CashFlowSeries } from '../../../domain/value-objects/CashFlow';
import { Card } from '../../components/ui/Card';

interface CashFlowChartProps {
  data?: CashFlowSeries;
  loading?: boolean;
}

export const CashFlowChart: React.FC<CashFlowChartProps> = ({ data, loading = false }) => {
  const formatCurrency = (val: number | null | undefined) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
      maximumFractionDigits: 0,
    }).format(val ?? 0);
  };

  if (loading && !data) {
    return (
      <section className="section-container" aria-busy="true" aria-label="Carregando saldo do mês">
        <Card>
          <div className="skeleton skeleton-text" />
          <div className="skeleton skeleton-chart" />
        </Card>
      </section>
    );
  }

  const days = data?.days ?? [];
  const chartData = days.map((d) => ({
    dia: d.day,
    Realizado: d.realized_balance,
    Projetado: d.projected_balance,
  }));

  const transitionDay = data?.transition_date ? Number(data.transition_date.split('-')[2]) : null;
  const lastDay = days.length > 0 ? days[days.length - 1] : null;
  const showTransition =
    transitionDay !== null && lastDay !== null && transitionDay < lastDay.day && (data?.has_projection ?? false);

  const ariaSummary = !data
    ? 'Sem dados de saldo.'
    : transitionDay === null
      ? `Sem dias confirmados no período. Projeção de ${formatCurrency(data.final_projected_balance)} ao fim do mês.`
      : `Saldo realizado até dia ${transitionDay} de ${formatCurrency(
          days[transitionDay - 1]?.realized_balance
        )}, projeção de ${formatCurrency(data.final_projected_balance)} ao fim do mês.`;

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const visible = payload.filter((entry: any) => entry.value !== null && entry.value !== undefined);
      if (visible.length === 0) return null;
      return (
        <div className="chart-tooltip">
          <p className="tooltip-title">Dia {label}</p>
          {visible.map((entry: any, index: number) => (
            <p key={index} style={{ color: entry.color, margin: '2px 0' }}>
              {entry.name}: {formatCurrency(entry.value)}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <section className="section-container">
      <div className="section-header" style={{ marginBottom: '14px' }}>
        <h2>Saldo ao longo do mês</h2>
      </div>
      <div className="chart-card glass-panel">
        <div className="chart-header">
          <h3>Realizado vs projetado</h3>
          <span className="chart-subtitle">
            Projeção fim do mês: {formatCurrency(data?.final_projected_balance)}
          </span>
        </div>

        <div style={{ width: '100%', height: 240 }} role="img" aria-label={ariaSummary}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
              <defs>
                <linearGradient id="cashRealized" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="cashProjected" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="dia" stroke="#94a3b8" fontSize={12} tickCount={8} />
              <YAxis stroke="#94a3b8" fontSize={12} tickFormatter={(val) => `R$${val}`} />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ paddingTop: '10px', fontSize: '0.8rem' }} />
              <Area
                type="monotone"
                dataKey="Realizado"
                stroke="#10b981"
                fill="url(#cashRealized)"
                strokeWidth={2}
                connectNulls={false}
              />
              <Area
                type="monotone"
                dataKey="Projetado"
                stroke="#f59e0b"
                fill="url(#cashProjected)"
                strokeWidth={2}
                strokeDasharray="6 4"
                connectNulls={false}
              />
              {showTransition && (
                <ReferenceLine
                  x={transitionDay}
                  stroke="#94a3b8"
                  strokeDasharray="3 3"
                  label={{ value: 'Hoje', fill: '#94a3b8', fontSize: 11, position: 'insideTopRight' }}
                />
              )}
              {lastDay?.projected_balance !== null &&
                lastDay?.projected_balance !== undefined &&
                (data?.has_projection ?? false) && (
                  <ReferenceDot
                    x={lastDay.day}
                    y={lastDay.projected_balance}
                    r={4}
                    fill="#f59e0b"
                    stroke="none"
                  />
                )}
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  );
};
