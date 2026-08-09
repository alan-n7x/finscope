import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import type { CategoryItemProps } from '../../../domain/value-objects/CategoryAnalytics';

interface CategoryDonutChartProps {
  data: CategoryItemProps[];
  totalExpenses: number;
}

export const CategoryDonutChart: React.FC<CategoryDonutChartProps> = ({ data, totalExpenses }) => {
  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    }).format(val);
  };

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const item: CategoryItemProps = payload[0].payload;
      return (
        <div className="chart-tooltip">
          <p className="tooltip-title">{item.name}</p>
          <p className="tooltip-val">{formatCurrency(item.value)} ({item.percentage}%)</p>
        </div>
      );
    }
    return null;
  };

  if (!data || data.length === 0) {
    return (
      <div className="chart-card glass-panel">
        <h3>Gastos por Categoria</h3>
        <p className="loading-cell">Nenhum gasto confirmado no período.</p>
      </div>
    );
  }

  return (
    <div className="chart-card glass-panel">
      <div className="chart-header">
        <h3>Gastos por Categoria</h3>
        <span className="chart-subtitle">Total: {formatCurrency(totalExpenses)}</span>
      </div>

      <div className="donut-chart-container">
        <div className="donut-wrapper">
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={70}
                outerRadius={100}
                paddingAngle={4}
                dataKey="value"
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} stroke="rgba(15,23,42,0.8)" strokeWidth={2} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-legend">
          {data.map((item, idx) => (
            <div key={idx} className="legend-item">
              <span className="legend-color" style={{ backgroundColor: item.color }} />
              <span className="legend-name">{item.name}</span>
              <span className="legend-val">{item.percentage}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
