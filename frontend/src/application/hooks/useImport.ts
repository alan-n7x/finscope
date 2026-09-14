import { useMutation, useQueryClient } from '@tanstack/react-query';

export interface ImportTransaction {
  id: string;
  date: string;
  type: string;
  description: string;
  amount: number;
  status: 'NEW' | 'MATCHED' | 'IGNORED';
  category?: string;
  account?: string;
  similarity_score?: number;
}

export interface BalanceSnapshot {
  date: string;
  balance: number;
}

export interface ImportPreviewResponse {
  transactions: ImportTransaction[];
  account_guess?: string;
  snapshots?: BalanceSnapshot[];
}

export const useUploadExtrato = () => {
  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      
      const res = await fetch('/api/transactions/import/upload', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        throw new Error('Falha ao processar arquivo');
      }

      const data: ImportPreviewResponse = await res.json();
      return data;
    },
  });
};

export const useConfirmImport = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { transactions: ImportTransaction[]; snapshots?: BalanceSnapshot[] }) => {
      const res = await fetch('/api/transactions/import/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      
      if (!res.ok) {
        throw new Error('Falha ao confirmar importação');
      }

      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
};
