import React from 'react';
import { Debt } from '../../../domain/entities/Debt';
import { Badge } from '../../components/ui/Badge';

interface DebtsSidebarProps {
  debts: Debt[];
}

export const DebtsSidebar: React.FC<DebtsSidebarProps> = ({ debts }) => {
  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    }).format(val || 0);
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '';
    const parts = dateStr.split('-');
    if (parts.length === 3) return `${parts[2]}/${parts[1]}/${parts[0]}`;
    return dateStr;
  };

  return (
    <aside className="sidebar-section glass-panel">
      <div className="section-header">
        <h2>Dívidas & Compromissos</h2>
      </div>
      <div className="debts-list">
        {debts.length === 0 ? (
          <p className="subtitle">Nenhuma dívida em aberto.</p>
        ) : (
          debts.map((d, idx) => (
            <div key={idx} className="debt-card">
              <div className="debt-header">
                <span className="debt-title">{d.creditor}</span>
                <Badge variant={d.status === 'Ativa' ? 'expense' : 'pending'}>
                  {d.status}
                </Badge>
              </div>
              <div className="debt-balance">{formatCurrency(d.balance)}</div>
              <div className="debt-meta">
                <span>Parcela: {formatCurrency(d.installment)}/mês</span>
                <span>Vencimento: {formatDate(d.due_date)}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </aside>
  );
};
