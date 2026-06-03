import { useState, useEffect } from 'react';
import './NotaDetailsModal.css';

export default function NotaDetailsModal({ notaId, onClose, onEdit }) {
  const [nota, setNota] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!notaId) return;
    const fetchNota = async () => {
      setLoading(true);
      try {
        const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        const res = await fetch(`${API_URL}/api/nota/${notaId}`);
        const json = await res.json();
        if (json.success) {
          setNota(json.nota);
        }
      } catch (err) {
        console.error("Erro ao buscar detalhes da nota:", err);
      }
      setLoading(false);
    };
    fetchNota();
  }, [notaId]);

  if (!notaId) return null;

  const formatMoney = (val) => {
    if (!val) return 'R$ 0,00';
    return Number(val).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>📄 Detalhes da Nota #{nota?.numero_nf || nota?.id}</h2>
          <button className="btn-close" onClick={onClose}>X</button>
        </div>

        {loading ? (
          <div className="loading-state">Carregando detalhes...</div>
        ) : nota ? (
          <div className="modal-body">
            
            <div className="status-banner" style={{ backgroundColor: nota.status === 'PAGO' ? 'var(--success)' : nota.status === 'CANCELADO' ? 'var(--error)' : 'var(--warning)', color: '#fff', padding: '8px', textAlign: 'center', fontWeight: 'bold', borderRadius: '8px', marginBottom: '16px' }}>
              STATUS: {nota.status}
            </div>

            <div className="details-section">
              <h3>🏢 Dados Básicos</h3>
              <div className="details-grid">
                <div><strong>Fornecedor:</strong> {nota.fornecedor}</div>
                <div><strong>CNPJ/CPF:</strong> {nota.cnpj}</div>
                <div><strong>Empresa/Filial:</strong> {nota.empresa} / {nota.filial}</div>
                <div><strong>Categoria:</strong> {nota.categoria}</div>
                <div><strong>Natureza:</strong> {nota.natureza}</div>
                <div><strong>Responsável:</strong> {nota.responsavel}</div>
                <div style={{gridColumn: 'span 2'}}><strong>Descrição:</strong> {nota.descricao}</div>
              </div>
            </div>

            <div className="details-section">
              <h3>💰 Valores e Datas</h3>
              <div className="details-grid">
                <div><strong>Emissão:</strong> {nota.dt_emissao}</div>
                <div><strong>Vencimento:</strong> {nota.dt_vencimento}</div>
                <div><strong>Valor Bruto:</strong> <span className="text-accent font-bold">{formatMoney(nota.valor_bruto)}</span></div>
                <div><strong>DIFAL:</strong> {formatMoney(nota.valor_difal)}</div>
              </div>
            </div>

            {nota.impostos && nota.impostos.length > 0 && (
              <div className="details-section">
                <h3>🏛️ Impostos Retidos</h3>
                <ul className="details-list">
                  {nota.impostos.map(imp => (
                    <li key={imp.id}><strong>{imp.tipo}:</strong> {imp.aliquota}% - {formatMoney(imp.valor)} (Venc: {imp.dt_venc_imp})</li>
                  ))}
                </ul>
              </div>
            )}

            {nota.rateio && nota.rateio.length > 0 && (
              <div className="details-section">
                <h3>🛒 Rateio (Centro de Custo)</h3>
                <ul className="details-list">
                  {nota.rateio.map(rat => (
                    <li key={rat.id}><strong>{rat.centro_custo}:</strong> {formatMoney(rat.valor)}</li>
                  ))}
                </ul>
              </div>
            )}
            
            {nota.itens && nota.itens.length > 0 && (
              <div className="details-section">
                <h3>📦 Itens / Serviços</h3>
                <ul className="details-list">
                  {nota.itens.map(item => (
                    <li key={item.id}>{item.descricao} - {formatMoney(item.valor_total)}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="details-section">
              <h3>💳 Pagamento</h3>
              <div className="details-grid">
                <div><strong>Forma Pgto:</strong> {nota.forma_pgto}</div>
                {nota.forma_pgto === 'PIX' && <div><strong>Chave PIX:</strong> {nota.pix_chave}</div>}
                {nota.forma_pgto === 'TED' && (
                  <div style={{gridColumn: 'span 2'}}>
                    <strong>Banco:</strong> {nota.banco_dest} | <strong>Ag:</strong> {nota.agencia_dest} | <strong>Conta:</strong> {nota.conta_dest} | <strong>CPF/CNPJ:</strong> {nota.cpf_cnpj_dest}
                  </div>
                )}
                <div style={{gridColumn: 'span 2'}}><strong>Cód. Barras:</strong> {nota.cod_barras || '-'}</div>
                <div style={{gridColumn: 'span 2'}}><strong>Chave Ref:</strong> {nota.chave_ref || '-'}</div>
                <div style={{gridColumn: 'span 2'}}><strong>Observação:</strong> {nota.observacao || '-'}</div>
              </div>
            </div>

            <div className="modal-footer">
              <button className="btn-editar" onClick={() => { onClose(); onEdit(nota.id); }}>✏️ Editar Nota</button>
            </div>

          </div>
        ) : (
          <div className="error-state">Nota não encontrada.</div>
        )}
      </div>
    </div>
  );
}
