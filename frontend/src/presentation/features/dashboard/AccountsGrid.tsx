import React from 'react';
import { Account } from '../../../domain/entities/Account';

interface AccountsGridProps {
  accounts?: Account[];
}

export const AccountsGrid: React.FC<AccountsGridProps> = ({ accounts = [] }) => {
  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    }).format(val || 0);
  };

  return (
    <section className="section-container">
      <div className="section-header" style={{ marginBottom: '14px' }}>
        <h2>Minhas Contas</h2>
      </div>
      <div className="accounts-grid">
        {accounts.map((acc, idx) => (
          <div key={idx} className="account-card">
            <span className="account-name">
              {acc.name} ({acc.type})
            </span>
            <span className="account-balance">{formatCurrency(acc.balance)}</span>
          </div>
        ))}
      </div>
    </section>
  );
};
