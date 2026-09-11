import React from 'react';
import { CalendarDays, ChevronLeft, ChevronRight } from 'lucide-react';

interface PeriodSelectorProps {
  value: string;
  onChange: (period: string) => void;
}

export const currentPeriod = (): string => {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  return `${now.getFullYear()}-${month}`;
};

const shiftPeriod = (period: string, delta: number): string => {
  const [yearStr, monthStr] = period.split('-');
  const date = new Date(Number(yearStr), Number(monthStr) - 1 + delta, 1);
  const month = String(date.getMonth() + 1).padStart(2, '0');
  return `${date.getFullYear()}-${month}`;
};

export const PeriodSelector: React.FC<PeriodSelectorProps> = ({ value, onChange }) => {
  const max = currentPeriod();
  const isCurrent = value >= max;

  const displayLabel = (() => {
    const [yearStr, monthStr] = value.split('-');
    const formatted = new Intl.DateTimeFormat('pt-BR', { month: 'short', year: 'numeric' }).format(
      new Date(Number(yearStr), Number(monthStr) - 1, 1)
    );
    return formatted.replace('.', '');
  })();

  return (
    <div className="period-selector" title="Selecione o período de referência">
      <button
        type="button"
        className="period-nav-btn"
        aria-label="Mês anterior"
        onClick={() => onChange(shiftPeriod(value, -1))}
      >
        <ChevronLeft size={16} />
      </button>

      <label className="period-display" title="Clique para escolher mês e ano">
        <CalendarDays size={13} />
        <span>{displayLabel}</span>
        <input
          type="month"
          className="period-month-input"
          value={value}
          max={max}
          onChange={(e) => {
            if (e.target.value) onChange(e.target.value);
          }}
          aria-label="Selecionar mês e ano"
        />
      </label>

      <button
        type="button"
        className="period-nav-btn"
        aria-label="Próximo mês"
        disabled={isCurrent}
        onClick={() => onChange(shiftPeriod(value, 1))}
      >
        <ChevronRight size={16} />
      </button>

      {!isCurrent && (
        <button type="button" className="period-today-btn" onClick={() => onChange(max)}>
          Mês Atual
        </button>
      )}
    </div>
  );
};
