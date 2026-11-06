import React, { useState } from 'react';
import { useTransactions, useFilterOptions } from '../../application/hooks/useTransactions';
import { TransactionTable } from '../features/transactions/TransactionTable';
import { ImportExtratoModal } from '../features/transactions/ImportExtratoModal';
import { EditTransactionModal } from '../features/transactions/EditTransactionModal';
import { DownloadCloud } from 'lucide-react';
import type { Transaction } from '../../domain/entities/Transaction';

export const ExtratoPage: React.FC = () => {
  const [selectedMonth, setSelectedMonth] = useState('2026-08');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [editingTransaction, setEditingTransaction] = useState<Transaction | null>(null);

  const { data: filterOptions } = useFilterOptions();
  const { data: transactions = [], isLoading } = useTransactions({
    month: selectedMonth,
    category: selectedCategory,
    status: selectedStatus,
    search: searchQuery,
  });

  return (
    <div className="page-content">
      <div className="page-header" style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
        <div className="page-title-group">
          <h1 className="page-title">Extrato</h1>
          <p className="page-subtitle">Todos os seus lançamentos</p>
        </div>
        <button 
          className="btn btn-outline" 
          onClick={() => setIsImportModalOpen(true)}
          style={{ display: 'flex', gap: '8px', alignItems: 'center' }}
        >
          <DownloadCloud size={20} />
          <span>Importar Extrato</span>
        </button>
      </div>

      <TransactionTable
        transactions={transactions}
        isLoading={isLoading}
        filterOptions={filterOptions}
        selectedMonth={selectedMonth}
        onMonthChange={setSelectedMonth}
        selectedCategory={selectedCategory}
        onCategoryChange={setSelectedCategory}
        selectedStatus={selectedStatus}
        onStatusChange={setSelectedStatus}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        onEdit={setEditingTransaction}
      />
      
      <ImportExtratoModal 
        isOpen={isImportModalOpen} 
        onClose={() => setIsImportModalOpen(false)} 
      />

      <EditTransactionModal
        isOpen={Boolean(editingTransaction)}
        transaction={editingTransaction}
        onClose={() => setEditingTransaction(null)}
        filterOptions={filterOptions}
      />
    </div>
  );
};
