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
} from 'recharts';
import type { CashFlowSeries } from '../../../domain/value-objects/CashFlow';
import { Card } from '../../components/ui/Card';

interface CashFlowChartProps {
  data?: CashFlowSeries;
  loading?: boolean;
}

export const CashFlowChart: React.FC<CashFlowChartProps> = ({ data, loading = false }) => {
  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
      maximumFractionDigits: 0,
    }).format(val);
  };

  if (loading && !data) {
    return (
      <section className="section-container" aria-busy="true" aria-label="Carregando fluxo de caixa">
        <Card>
          <div className="skeleton skeleton-text" />
          <div className="skeleton skeleton-chart" />
        </Card>
      </section>
    );
  }

  const chartData = (data?.days ?? []).map((d) => ({
    dia: d.day,
    Entradas: d.cumulative_income,
    Saídas: d.cumulative_expense,
  }));

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const day = data?.days.find((d) => d.day === label);
      return (
        <div className="chart-tooltip">
          <p className="tooltip-title">Dia {label}</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} style={{ color: entry.color, margin: '2px 0' }}>
              {entry.name}: {formatCurrency(entry.value)}
            </p>
          ))}
          {day && (
            <p style={{ color: '#94a3b8', margin: '2px 0' }}>
              Líquido: {formatCurrency(day.net)}
            </p>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <section className="section-container">
      <div className="section-header" style={{ marginBottom: '14px' }}>
        <h2>Fluxo de Caixa</h2>
      </div>
      <div className="chart-card glass-panel">
        <div className="chart-header">
          <h3>Entradas vs Saídas acumuladas</h3>
          <span className="chart-subtitle">Evolução diária em R$</span>
        </div>

        <div style={{ width: '100%', height: 240 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
              <defs>
                <linearGradient id="cashIncome" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="cashExpense" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#f43f5e" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="dia" stroke="#94a3b8" fontSize={12} tickCount={8} />
              <YAxis stroke="#94a3b8" fontSize={12} tickFormatter={(val) => `R$${val}`} />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ paddingTop: '10px', fontSize: '0.8rem' }} />
              <Area type="monotone" dataKey="Entradas" stroke="#10b981" fill="url(#cashIncome)" strokeWidth={2} />
              <Area type="monotone" dataKey="Saídas" stroke="#f43f5e" fill="url(#cashExpense)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  );
};
