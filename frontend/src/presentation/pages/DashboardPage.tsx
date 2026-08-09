import React, { useState } from 'react';
import { useDashboard } from '../../application/hooks/useDashboard';
import { useTransactions, useFilterOptions, useCreateTransaction } from '../../application/hooks/useTransactions';
import { KpiCardsGrid } from '../features/dashboard/KpiCardsGrid';
import { AccountsGrid } from '../features/dashboard/AccountsGrid';
import { AnalyticsSection } from '../features/analytics/AnalyticsSection';
import { TransactionTable } from '../features/transactions/TransactionTable';
import { NewTransactionModal } from '../features/transactions/NewTransactionModal';
import { DebtsSidebar } from '../features/debts/DebtsSidebar';
import { Button } from '../components/ui/Button';
import { Plus, Wallet, FileSpreadsheet } from 'lucide-react';
import type { CreateTransactionDTO } from '../../domain/repositories/ITransactionRepository';

export const DashboardPage: React.FC = () => {
  const [selectedMonth, setSelectedMonth] = useState('2026-08');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

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
    setToastMessage('✅ Lançamento salvo na planilha com sucesso!');
    setTimeout(() => setToastMessage(null), 4000);
  };

  return (
    <div className="app-layout">
      {/* Header */}
      <header className="app-header">
        <div className="brand">
          <div className="logo-icon">
            <Wallet size={22} />
          </div>
          <div className="brand-text">
            <h1>Finscope</h1>
            <p className="subtitle">Controle Financeiro Pessoal</p>
          </div>
        </div>

        <div className="header-actions">
          {/* Badge informativo — sem afirmação falsa de OneDrive */}
          <div className="status-badge" title="Dados lidos da planilha local via API">
            <span className="status-dot"></span>
            <FileSpreadsheet size={14} />
            <span>Planilha Conectada</span>
          </div>
          <Button onClick={() => setIsModalOpen(true)}>
            <Plus size={16} />
            Novo Lançamento
          </Button>
        </div>
      </header>

      {/* KPI Cards */}
      <KpiCardsGrid summary={dashboardData?.summary} />

      {/* Accounts Grid */}
      <AccountsGrid accounts={dashboardData?.summary?.accounts} />

      {/* Analytics Charts */}
      <AnalyticsSection transactions={transactions} summary={dashboardData?.summary} />

      {/* Transactions + Debts */}
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

      {/* Toast */}
      {toastMessage && <div className="toast">{toastMessage}</div>}
    </div>
  );
};
