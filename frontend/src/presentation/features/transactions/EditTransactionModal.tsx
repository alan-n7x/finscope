import React from 'react';
import { Modal } from '../../components/ui/Modal';
import { TransactionForm } from './TransactionForm';
import { useTransaction, useUpdateTransaction } from '../../../application/hooks/useTransactions';
import type { Transaction } from '../../../domain/entities/Transaction';
import type {
  FilterOptions,
  CreateTransactionDTO,
} from '../../../domain/repositories/ITransactionRepository';

interface EditTransactionModalProps {
  isOpen: boolean;
  transaction: Transaction | null;
  onClose: () => void;
  filterOptions?: FilterOptions;
}

export const EditTransactionModal: React.FC<EditTransactionModalProps> = ({
  isOpen,
  transaction,
  onClose,
  filterOptions,
}) => {
  const { data: current, isLoading, isError } = useTransaction(
    transaction?.id,
    transaction ?? undefined
  );
  const updateTx = useUpdateTransaction();

  const handleSubmit = async (dto: CreateTransactionDTO) => {
    if (!transaction) return;
    await updateTx.mutateAsync({ id: transaction.id, dto });
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Editar Lançamento">
      {isLoading && !current ? (
        <div className="modal-state">Carregando lançamento...</div>
      ) : isError || !current ? (
        <div className="modal-state modal-state--error">
          Não foi possível carregar o lançamento.
        </div>
      ) : (
        <TransactionForm
          // O estado do formulário só é inicializado no mount; a key força
          // reinicializar se o lançamento em edição mudar com o modal aberto.
          key={current.id}
          filterOptions={filterOptions}
          initialValues={{
            date: current.date,
            type: current.type,
            category: current.category,
            description: current.description,
            amount: String(current.amount),
            account: current.account,
            payment_method: current.payment_method,
            paid: current.isPaid(),
            essential: current.essential === 'Sim',
            obs: current.obs ?? '',
          }}
          submitLabel="Salvar Alterações"
          onSubmit={handleSubmit}
          onCancel={onClose}
        />
      )}
    </Modal>
  );
};
