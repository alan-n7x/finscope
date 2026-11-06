import React from 'react';
import { Transaction } from '../../../domain/entities/Transaction';
import { Badge } from '../../components/ui/Badge';
import { Search, Pencil } from 'lucide-react';
import type { FilterOptions } from '../../../domain/repositories/ITransactionRepository';

interface TransactionTableProps {
  transactions: Transaction[];
  isLoading: boolean;
  filterOptions?: FilterOptions;
  selectedMonth: string;
  onMonthChange: (month: string) => void;
  selectedCategory: string;
  onCategoryChange: (cat: string) => void;
  selectedStatus: string;
  onStatusChange: (status: string) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  onEdit?: (transaction: Transaction) => void;
}

export const TransactionTable: React.FC<TransactionTableProps> = ({
  transactions,
  isLoading,
  filterOptions,
  selectedMonth,
  onMonthChange,
  selectedCategory,
  onCategoryChange,
  selectedStatus,
  onStatusChange,
  searchQuery,
  onSearchChange,
  onEdit,
}) => {
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
    <section className="transactions-section glass-panel card-hover">
      <div className="section-header-wrap">
        <h2>Extrato de Lançamentos</h2>
        <div className="filters-bar">
          <div className="search-box">
            <Search size={16} />
            <input
              type="text"
              placeholder="Buscar lançamento..."
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
            />
          </div>

          <div className="filters-row">
            <select
              className="custom-select"
              value={selectedMonth}
              onChange={(e) => onMonthChange(e.target.value)}
            >
              <option value="">Todos Meses</option>
              {filterOptions?.months.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>

            <select
              className="custom-select"
              value={selectedCategory}
              onChange={(e) => onCategoryChange(e.target.value)}
            >
              <option value="">Categorias</option>
              {filterOptions?.categories.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>

            <select
              className="custom-select"
              value={selectedStatus}
              onChange={(e) => onStatusChange(e.target.value)}
            >
              <option value="">Status</option>
              <option value="sim">Pagos</option>
              <option value="não">Pendentes</option>
            </select>
          </div>
        </div>
      </div>

      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th>Data</th>
              <th>Tipo</th>
              <th>Descrição</th>
              <th>Categoria</th>
              <th>Conta</th>
              <th>Forma</th>
              <th>Valor</th>
              <th>Status</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={9} className="loading-cell">
                  Carregando lançamentos...
                </td>
              </tr>
            ) : transactions.length === 0 ? (
              <tr>
                <td colSpan={9} className="loading-cell">
                  Nenhum lançamento encontrado.
                </td>
              </tr>
            ) : (
              transactions.map((tx) => {
                let variant: 'income' | 'expense' | 'transfer' = 'expense';
                let amountClass = 'amount-expense';
                let prefix = '-';

                if (tx.isIncome()) {
                  variant = 'income';
                  amountClass = 'amount-income';
                  prefix = '+';
                } else if (tx.type === 'Transferência') {
                  variant = 'transfer';
                  amountClass = 'amount-transfer';
                  prefix = '';
                }

                return (
                  <tr
                    key={tx.id}
                    className={onEdit ? 'transaction-row' : undefined}
                    onClick={onEdit ? () => onEdit(tx) : undefined}
                  >
                    <td>{formatDate(tx.date)}</td>
                    <td>
                      <Badge variant={variant}>{tx.type}</Badge>
                    </td>
                    <td>
                      <strong>{tx.description}</strong>
                    </td>
                    <td>{tx.category}</td>
                    <td>{tx.account}</td>
                    <td>{tx.payment_method}</td>
                    <td className={amountClass}>
                      {prefix}
                      {formatCurrency(tx.amount)}
                    </td>
                    <td>
                      <Badge variant={tx.isPaid() ? 'paid' : 'pending'}>
                        {tx.isPaid() ? 'Pago' : 'Pendente'}
                      </Badge>
                    </td>
                    <td>
                      {onEdit && (
                        <button
                          type="button"
                          className="row-action"
                          title="Editar lançamento"
                          aria-label={`Editar ${tx.description}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            onEdit(tx);
                          }}
                        >
                          <Pencil size={15} />
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
};
