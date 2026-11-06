import React from 'react';
import { Modal } from '../../components/ui/Modal';
import { TransactionForm } from './TransactionForm';
import type {
  FilterOptions,
  CreateTransactionDTO,
} from '../../../domain/repositories/ITransactionRepository';

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
  const handleSubmit = async (dto: CreateTransactionDTO) => {
    await onSubmit(dto);
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Novo Lançamento">
      <TransactionForm
        filterOptions={filterOptions}
        onSubmit={handleSubmit}
        onCancel={onClose}
      />
    </Modal>
  );
};
