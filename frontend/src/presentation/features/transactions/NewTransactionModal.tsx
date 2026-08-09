import React, { useState } from 'react';
import { Modal } from '../../components/ui/Modal';
import { Button } from '../../components/ui/Button';
import type { FilterOptions, CreateTransactionDTO } from '../../../domain/repositories/ITransactionRepository';

interface NewTransactionModalProps {
  isOpen: boolean;
  onClose: () => void;
  filterOptions?: FilterOptions;
  onSubmit: (dto: CreateTransactionDTO) => Promise<void>;
}

export const NewTransactionModal: React.FC<NewTransactionModalProps> = ({
  isOpen,
  onClose,
  filterOptions,
  onSubmit,
}) => {
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [type, setType] = useState('Despesa');
  const [category, setCategory] = useState(filterOptions?.categories[0] || 'Outros');
  const [description, setDescription] = useState('');
  const [amount, setAmount] = useState('');
  const [account, setAccount] = useState(filterOptions?.accounts[0] || 'Itaú - Conta corrente');
  const [paymentMethod, setPaymentMethod] = useState(filterOptions?.payment_methods[0] || 'Pix');
  const [paid, setPaid] = useState(true);
  const [essential, setEssential] = useState(false);
  const [obs, setObs] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

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
      onClose();
      setDescription('');
      setAmount('');
      setObs('');
    } catch (err: any) {
      alert(`Erro: ${err.message || 'Falha ao salvar lançamento'}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Novo Lançamento">
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
              {filterOptions?.categories.map((c) => (
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
              {filterOptions?.accounts.map((a) => (
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
              {filterOptions?.payment_methods.map((pm) => (
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
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Salvando...' : 'Salvar no OneDrive'}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
