import React, { useState } from 'react';
import { Button } from '../../components/ui/Button';
import type {
  FilterOptions,
  CreateTransactionDTO,
} from '../../../domain/repositories/ITransactionRepository';

export interface TransactionFormValues {
  date: string;
  type: string;
  category: string;
  description: string;
  amount: string;
  account: string;
  payment_method: string;
  paid: boolean;
  essential: boolean;
  obs: string;
}

interface TransactionFormProps {
  filterOptions?: FilterOptions;
  initialValues?: Partial<TransactionFormValues>;
  submitLabel?: string;
  onSubmit: (dto: CreateTransactionDTO) => Promise<void>;
  onCancel: () => void;
}

function withCurrent(options: string[] | undefined, current: string): string[] {
  const list = options ?? [];
  return current && !list.includes(current) ? [current, ...list] : list;
}

export const TransactionForm: React.FC<TransactionFormProps> = ({
  filterOptions,
  initialValues,
  submitLabel = 'Salvar Lançamento',
  onSubmit,
  onCancel,
}) => {
  const today = new Date().toISOString().split('T')[0];
  const [date, setDate] = useState(initialValues?.date ?? today);
  const [type, setType] = useState(initialValues?.type ?? 'Despesa');
  const [category, setCategory] = useState(
    initialValues?.category ?? filterOptions?.categories[0] ?? 'Outros'
  );
  const [description, setDescription] = useState(initialValues?.description ?? '');
  const [amount, setAmount] = useState(initialValues?.amount ?? '');
  const [account, setAccount] = useState(
    initialValues?.account ?? filterOptions?.accounts[0] ?? 'Itaú - Conta corrente'
  );
  const [paymentMethod, setPaymentMethod] = useState(
    initialValues?.payment_method ?? filterOptions?.payment_methods[0] ?? 'Pix'
  );
  const [paid, setPaid] = useState(initialValues?.paid ?? true);
  const [essential, setEssential] = useState(initialValues?.essential ?? false);
  const [obs, setObs] = useState(initialValues?.obs ?? '');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const categoryOptions = withCurrent(filterOptions?.categories, category);
  const accountOptions = withCurrent(filterOptions?.accounts, account);
  const paymentMethodOptions = withCurrent(filterOptions?.payment_methods, paymentMethod);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!amount || parseFloat(amount) <= 0) return;

    setIsSubmitting(true);
    try {
      await onSubmit({
        date,
        type,
        category: category || filterOptions?.categories[0] || 'Outros',
        description,
        payment_method: paymentMethod || filterOptions?.payment_methods[0] || 'Pix',
        amount: parseFloat(amount),
        essential,
        paid,
        obs,
        account: account || filterOptions?.accounts[0] || 'Itaú - Conta corrente',
      });
    } catch (err: any) {
      alert(`Erro: ${err.message || 'Falha ao salvar lançamento'}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="modal-form">
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
          <label>Tipo</label>
          <select
            className="custom-select"
            value={type}
            onChange={(e) => setType(e.target.value)}
            required
          >
            <option value="Despesa">Despesa</option>
            <option value="Receita">Receita</option>
            <option value="Transferência">Transferência</option>
          </select>
        </div>
      </div>

      <div className="form-group">
        <label>Descrição</label>
        <input
          type="text"
          placeholder="Ex: Supermercado, Aluguel, Pix"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          required
        />
      </div>

      <div className="form-row">
        <div className="form-group">
          <label>Valor (R$)</label>
          <input
            type="number"
            step="0.01"
            min="0.01"
            placeholder="0,00"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            required
          />
        </div>
        <div className="form-group">
          <label>Categoria</label>
          <select
            className="custom-select"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            required
          >
            {categoryOptions.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
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
            required
          >
            {accountOptions.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label>Forma de Pagamento</label>
          <select
            className="custom-select"
            value={paymentMethod}
            onChange={(e) => setPaymentMethod(e.target.value)}
            required
          >
            {paymentMethodOptions.map((pm) => (
              <option key={pm} value={pm}>
                {pm}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="form-row checkboxes-row">
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={paid}
            onChange={(e) => setPaid(e.target.checked)}
          />
          <span>Já foi pago / confirmado?</span>
        </label>
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={essential}
            onChange={(e) => setEssential(e.target.checked)}
          />
          <span>Gasto essencial?</span>
        </label>
      </div>

      <div className="form-group">
        <label>Observação (Opcional)</label>
        <input
          type="text"
          placeholder="Anotações adicionais..."
          value={obs}
          onChange={(e) => setObs(e.target.value)}
        />
      </div>

      <div className="modal-footer">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancelar
        </Button>
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Salvando...' : submitLabel}
        </Button>
      </div>
    </form>
  );
};
