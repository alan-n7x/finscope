import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCreateTransaction } from '../../application/hooks/useTransactions';
import { useFilterOptions } from '../../application/hooks/useTransactions';
import { ArrowLeft, Check } from 'lucide-react';
import type { CreateTransactionDTO } from '../../domain/repositories/ITransactionRepository';

export const LancarPage: React.FC = () => {
  const navigate = useNavigate();
  const { data: filterOptions } = useFilterOptions();
  const createTx = useCreateTransaction();

  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [type, setType] = useState<'Despesa' | 'Receita' | 'Transferência'>('Despesa');
  const [category, setCategory] = useState('');
  const [description, setDescription] = useState('');
  const [amount, setAmount] = useState('');
  const [account, setAccount] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('');
  const [paid, setPaid] = useState(true);
  const [essential, setEssential] = useState(false);
  const [obs, setObs] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);

  const typeColors: Record<string, string> = {
    Despesa:      '#ef4444',
    Receita:      '#10b981',
    Transferência: '#3b82f6',
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!amount || parseFloat(amount) <= 0) return;
    setIsSubmitting(true);
    try {
      const dto: CreateTransactionDTO = {
        date,
        type,
        category: category || filterOptions?.categories[0] || 'Outros',
        description,
        payment_method: paymentMethod || filterOptions?.payment_methods[0] || 'Pix',
        amount: parseFloat(amount),
        essential,
        paid,
        obs,
        account: account || filterOptions?.accounts[0] || '',
      };
      await createTx.mutateAsync(dto);
      setSuccess(true);
      setTimeout(() => navigate('/extrato'), 1500);
    } catch (err: any) {
      alert(`Erro: ${err.message || 'Falha ao salvar lançamento'}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="page-content">
      {/* Header */}
      <div className="lancar-header">
        <button className="btn-back" onClick={() => navigate(-1)}>
          <ArrowLeft size={20} />
        </button>
        <div>
          <h1 className="page-title">Novo Lançamento</h1>
          <p className="page-subtitle">Registre uma receita ou despesa</p>
        </div>
      </div>

      {/* Type Switcher */}
      <div className="type-switcher">
        {(['Despesa', 'Receita', 'Transferência'] as const).map((t) => (
          <button
            key={t}
            type="button"
            className={`type-btn ${type === t ? 'type-btn--active' : ''}`}
            style={type === t ? { background: typeColors[t], color: '#fff', borderColor: typeColors[t] } : {}}
            onClick={() => setType(t)}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="lancar-form glass-panel">
        {/* Amount — destaque visual */}
        <div className="amount-input-wrap">
          <span className="amount-prefix">R$</span>
          <input
            className="amount-input-big"
            type="number"
            step="0.01"
            min="0.01"
            placeholder="0,00"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            required
            autoFocus
          />
        </div>

        <div className="form-grid">
          <div className="form-group">
            <label>Descrição</label>
            <input
              type="text"
              placeholder="Ex: Supermercado, Aluguel, Pix..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              required
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Data</label>
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label>Categoria</label>
              <select
                className="custom-select"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              >
                {filterOptions?.categories.map((c: string) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Conta</label>
              <select
                className="custom-select"
                value={account}
                onChange={(e) => setAccount(e.target.value)}
              >
                {filterOptions?.accounts.map((a: string) => (
                  <option key={a} value={a}>{a}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Forma de Pagamento</label>
              <select
                className="custom-select"
                value={paymentMethod}
                onChange={(e) => setPaymentMethod(e.target.value)}
              >
                {filterOptions?.payment_methods.map((pm: string) => (
                  <option key={pm} value={pm}>{pm}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-group">
            <label>Observação (opcional)</label>
            <input
              type="text"
              placeholder="Anotações adicionais..."
              value={obs}
              onChange={(e) => setObs(e.target.value)}
            />
          </div>

          <div className="checkboxes-row">
            <label className="checkbox-label">
              <input type="checkbox" checked={paid} onChange={(e) => setPaid(e.target.checked)} />
              <span>Já pago / confirmado</span>
            </label>
            <label className="checkbox-label">
              <input type="checkbox" checked={essential} onChange={(e) => setEssential(e.target.checked)} />
              <span>Gasto essencial</span>
            </label>
          </div>
        </div>

        <button
          type="submit"
          className="btn-submit-lancar"
          disabled={isSubmitting || success}
          style={{ background: success ? '#10b981' : typeColors[type] }}
        >
          {success ? (
            <><Check size={20} /> Salvo! Redirecionando...</>
          ) : isSubmitting ? (
            'Salvando...'
          ) : (
            `Salvar ${type}`
          )}
        </button>
      </form>
    </div>
  );
};
