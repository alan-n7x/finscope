import React from 'react';
import { Account } from '../../../domain/entities/Account';

interface AccountsGridProps {
  accounts?: Account[];
  loading?: boolean;
}

export const AccountsGrid: React.FC<AccountsGridProps> = ({ accounts = [], loading = false }) => {
  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    }).format(val || 0);
  };

  if (loading && accounts.length === 0) {
    return (
      <section className="section-container" aria-busy="true" aria-label="Carregando contas">
        <div className="section-header" style={{ marginBottom: '14px' }}>
          <h2>Minhas Contas</h2>
        </div>
        <div className="accounts-grid">
          {[0, 1, 2].map((idx) => (
            <div key={idx} className="account-card">
              <div className="skeleton skeleton-text" />
              <div className="skeleton skeleton-value" />
            </div>
          ))}
        </div>
      </section>
    );
  }

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
