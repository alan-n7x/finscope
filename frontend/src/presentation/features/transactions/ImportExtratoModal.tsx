import React, { useRef, useState } from 'react';
import { UploadCloud, CheckCircle, AlertTriangle, XCircle } from 'lucide-react';
import { useUploadExtrato, useConfirmImport } from '../../../application/hooks/useImport';
import type { ImportTransaction, BalanceSnapshot } from '../../../application/hooks/useImport';
import { Modal } from '../../components/ui/Modal';
import { Button } from '../../components/ui/Button';

interface ImportExtratoModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ImportExtratoModal: React.FC<ImportExtratoModalProps> = ({ isOpen, onClose }) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<ImportTransaction[]>([]);
  const [accountGuess, setAccountGuess] = useState<string>('');
  const [snapshots, setSnapshots] = useState<BalanceSnapshot[]>([]);

  const uploadExtrato = useUploadExtrato();
  const confirmImport = useConfirmImport();

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const selected = e.target.files[0];
      try {
        const res = await uploadExtrato.mutateAsync(selected);
        setPreview(res.transactions);
        setAccountGuess(res.account_guess || 'Itaú - Conta corrente');
        setSnapshots(res.snapshots || []);
      } catch (err) {
        alert('Erro ao processar arquivo.');
      }
    }
  };

  const handleToggleStatus = (id: string) => {
    setPreview(prev => prev.map(t => {
      if (t.id === id) {
        const nextStatus = t.status === 'NEW' ? 'IGNORED' : t.status === 'IGNORED' ? 'MATCHED' : 'NEW';
        return { ...t, status: nextStatus };
      }
      return t;
    }));
  };

  const handleConfirm = async () => {
    // Assign guessed account to NEW items
    const toImport = preview.map(t => ({
      ...t,
      account: accountGuess
    }));
    
    try {
      await confirmImport.mutateAsync({ transactions: toImport, snapshots });
      alert('Importação concluída!');
      setPreview([]);
      setSnapshots([]);
      onClose();
    } catch (err) {
      alert('Erro ao confirmar importação.');
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Importar Extrato Bancário">
      <div className="import-modal-content">
        {!preview.length && (
          <div 
            className="upload-zone"
            onClick={() => fileInputRef.current?.click()}
          >
            <input 
              type="file" 
              ref={fileInputRef} 
              style={{ display: 'none' }} 
              accept=".ofx,.pdf" 
              onChange={handleFileChange} 
            />
            {uploadExtrato.isPending ? (
              <p>Analisando extrato...</p>
            ) : (
              <>
                <UploadCloud size={48} className="upload-icon" />
                <h3>Arraste o OFX ou PDF ou clique aqui</h3>
                <p>Suporta arquivos OFX genéricos ou PDF do Itaú.</p>
              </>
            )}
          </div>
        )}

        {preview.length > 0 && (
          <div className="preview-zone">
            <div className="preview-header">
              <h4>Revisão de Lançamentos</h4>
              <p>Conta identificada: <strong>{accountGuess}</strong></p>
            </div>
            
            <div className="preview-table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Ação</th>
                    <th>Data</th>
                    <th>Descrição</th>
                    <th>Valor</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.map(t => (
                    <tr key={t.id} className={`status-row status-${t.status.toLowerCase()}`}>
                      <td>
                        <button 
                          type="button"
                          className={`btn-status-toggle ${t.status.toLowerCase()}`}
                          onClick={() => handleToggleStatus(t.id)}
                        >
                          {t.status === 'NEW' && <CheckCircle size={18} />}
                          {t.status === 'MATCHED' && <AlertTriangle size={18} />}
                          {t.status === 'IGNORED' && <XCircle size={18} />}
                        </button>
                      </td>
                      <td>{t.date}</td>
                      <td>{t.description}</td>
                      <td style={{ color: t.type === 'Receita' ? '#10b981' : '#ef4444' }}>
                        {t.type === 'Receita' ? '+' : '-'} R$ {t.amount.toFixed(2)}
                      </td>
                      <td>
                        {t.status === 'NEW' && <span className="badge badge-new">Adicionar Novo</span>}
                        {t.status === 'MATCHED' && <span className="badge badge-matched">Já Conciliado</span>}
                        {t.status === 'IGNORED' && <span className="badge badge-ignored">Ignorar</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            
            <div className="preview-actions">
              <Button variant="secondary" onClick={() => setPreview([])}>Cancelar</Button>
              <Button 
                variant="primary" 
                onClick={handleConfirm}
                disabled={confirmImport.isPending}
              >
                {confirmImport.isPending ? 'Salvando...' : 'Confirmar Importação'}
              </Button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
};
