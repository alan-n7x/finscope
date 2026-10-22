import React, { useState } from 'react';
import { Modal } from '../../components/ui/Modal';
import { Button } from '../../components/ui/Button';

interface UpdateBalanceModalProps {
  isOpen: boolean;
  accountName: string;
  currentBalance: number;
  onClose: () => void;
  onSubmit: (balance: number, date: string) => Promise<void>;
}

export const UpdateBalanceModal: React.FC<UpdateBalanceModalProps> = ({
  isOpen,
  accountName,
  currentBalance,
  onClose,
  onSubmit,
}) => {
  const [balance, setBalance] = useState(String(currentBalance ?? 0));
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const parsed = Number(balance.replace(',', '.'));
    if (!Number.isFinite(parsed)) return;

    setIsSubmitting(true);
    try {
      await onSubmit(parsed, date);
      onClose();
    } catch (err: any) {
      alert(`Erro: ${err.message || 'Falha ao atualizar saldo'}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`Saldo real — ${accountName}`}>
      <form onSubmit={handleSubmit} className="modal-form">
        <p className="form-hint">
          Informe o saldo que aparece no banco/app. Ele passa a ser a âncora do
          dashboard; lançamentos posteriores a esta data continuam somando.
        </p>

        <div className="form-row">
          <div className="form-group">
            <label>Saldo (R$)</label>
            <input
              type="number"
              step="0.01"
              placeholder="0,00"
              value={balance}
              onChange={(e) => setBalance(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label>Data do saldo</label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              required
            />
          </div>
        </div>

        <div className="modal-footer">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Salvando...' : 'Salvar saldo'}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
