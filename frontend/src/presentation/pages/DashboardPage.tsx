import React, { useState } from 'react';
import { useDashboard } from '../../application/hooks/useDashboard';
import { useTransactions, useFilterOptions, useCreateTransaction } from '../../application/hooks/useTransactions';
import { KpiCardsGrid } from '../features/dashboard/KpiCardsGrid';
import { AccountsGrid } from '../features/dashboard/AccountsGrid';
import { TransactionTable } from '../features/transactions/TransactionTable';
import { NewTransactionModal } from '../features/transactions/NewTransactionModal';
import { DebtsSidebar } from '../features/debts/DebtsSidebar';
import { Button } from '../components/ui/Button';
import { Plus, Wallet } from 'lucide-react';
import type { CreateTransactionDTO } from '../../domain/repositories/ITransactionRepository';

export const DashboardPage: React.FC = () => {
  const [selectedMonth, setSelectedMonth] = useState('2026-08');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Application Hooks (React Query + Use Cases)
  const { data: dashboardData } = useDashboard(selectedMonth);
  const { data: filterOptions } = useFilterOptions();
  const { data: transactions = [], isLoading: isLoadingTx } = useTransactions({
    month: selectedMonth,
    category: selectedCategory,
    status: selectedStatus,
    search: searchQuery,
  });
  const createTxMutation = useCreateTransaction();

  const handleCreateTransaction = async (dto: CreateTransactionDTO) => {
    await createTxMutation.mutateAsync(dto);
    setToastMessage('✨ Lançamento gravado no OneDrive com sucesso!');
    setTimeout(() => setToastMessage(null), 4000);
  };

  return (
    <div className="app-layout">
      {/* Header */}
      <header className="app-header">
        <div className="brand">
          <div className="logo-icon">
            <Wallet size={24} />
          </div>
          <div>
            <h1>Finscope</h1>
            <p className="subtitle">Controle Financeiro Conectado ao OneDrive (React + Clean Arch)</p>
          </div>
        </div>

        <div className="header-actions">
          <div className="sync-badge" title="Planilha sincronizada via OneDrive">
            <span className="pulse-dot"></span>
            <span>OneDrive Sincronizado</span>
          </div>
          <Button onClick={() => setIsModalOpen(true)}>
            <Plus size={18} />
            Novo Lançamento
          </Button>
        </div>
      </header>

      {/* KPI Cards */}
      <KpiCardsGrid summary={dashboardData?.summary} />

      {/* Accounts Grid */}
      <AccountsGrid accounts={dashboardData?.summary?.accounts} />

      {/* Main Content Grid */}
      <div className="main-content-grid">
        <TransactionTable
          transactions={transactions}
          isLoading={isLoadingTx}
          filterOptions={filterOptions}
          selectedMonth={selectedMonth}
          onMonthChange={setSelectedMonth}
          selectedCategory={selectedCategory}
          onCategoryChange={setSelectedCategory}
          selectedStatus={selectedStatus}
          onStatusChange={setSelectedStatus}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
        />

        <DebtsSidebar debts={dashboardData?.debts || []} />
      </div>

      {/* New Transaction Modal */}
      <NewTransactionModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        filterOptions={filterOptions}
        onSubmit={handleCreateTransaction}
      />

      {/* Toast Notification */}
      {toastMessage && <div className="toast">{toastMessage}</div>}
    </div>
  );
};
