import React, { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import {
  LayoutDashboard,
  List,
  BarChart2,
  CreditCard,
  Plus,
  Wallet,
  Database,
  Menu,
  ChevronLeft,
} from 'lucide-react';
import { NewTransactionModal } from '../../features/transactions/NewTransactionModal';
import { useCreateTransaction } from '../../../application/hooks/useTransactions';
import { useFilterOptions } from '../../../application/hooks/useTransactions';
import type { CreateTransactionDTO } from '../../../domain/repositories/ITransactionRepository';

const navItems = [
  { to: '/',         icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/extrato',  icon: List,            label: 'Extrato'   },
  { to: '/analytics',icon: BarChart2,       label: 'Analytics' },
  { to: '/dividas',  icon: CreditCard,      label: 'Dívidas'   },
];

export const AppShell: React.FC = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const { data: filterOptions } = useFilterOptions();
  const createTx = useCreateTransaction();

  const handleCreate = async (dto: CreateTransactionDTO) => {
    await createTx.mutateAsync(dto);
    setToast('Lançamento salvo!');
    setTimeout(() => setToast(null), 4000);
  };

  const toggleSidebar = () => {
    setIsSidebarCollapsed(!isSidebarCollapsed);
  };

  return (
    <div className="shell">
      {/* ── Desktop/Tablet Sidebar ── */}
      <aside className={`nav-sidebar ${!isSidebarCollapsed ? 'nav-sidebar--expanded' : ''}`}>
        <div className="nav-brand">
          <div className="logo-icon">
            <Wallet size={20} />
          </div>
          <span className="nav-brand-label">Finscope</span>
          <button
            className="toggle-sidebar"
            onClick={toggleSidebar}
            aria-label={isSidebarCollapsed ? 'Abrir menu lateral' : 'Fechar menu lateral'}
          >
            {isSidebarCollapsed ? <Menu size={18} /> : <ChevronLeft size={18} />}
          </button>
        </div>

          <nav className="nav-items">
            {navItems.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  `nav-item ${isActive ? 'nav-item--active' : ''}`
                }
              >
                <Icon size={20} />
                <span className="nav-item-label">{label}</span>
              </NavLink>
            ))}
          </nav>

          <div className="nav-footer">
            <button
              className="nav-fab-sidebar"
              onClick={() => setIsModalOpen(true)}
            >
              <Plus size={18} />
              <span className="nav-item-label">Novo Lançamento</span>
            </button>
            <div className="nav-status">
              <Database size={14} />
              <span className="nav-item-label">PostgreSQL</span>
            </div>
          </div>
        </aside>

        {/* ── Main Content ── */}
        <main className="shell-main">
          <Outlet />
        </main>

      {/* ── Mobile Bottom Navigation Bar ── */}
      <nav className="bottom-nav">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `bottom-nav-item ${isActive ? 'bottom-nav-item--active' : ''}`
            }
          >
            <Icon size={22} />
            <span>{label}</span>
          </NavLink>
        ))}

        {/* FAB button in the center */}
        <button
          className="bottom-nav-fab"
          onClick={() => setIsModalOpen(true)}
          aria-label="Novo Lançamento"
        >
          <Plus size={24} />
        </button>
      </nav>

      {/* ── Modal ── */}
      <NewTransactionModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        filterOptions={filterOptions}
        onSubmit={handleCreate}
      />

      {/* ── Toast ── */}
      {toast && <div className="toast">{toast}</div>}
    </div>
  );
};
