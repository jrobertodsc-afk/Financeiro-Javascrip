import { useState, useEffect } from 'react';
import './NotaDetailsModal.css';
import { FileText, ShieldAlert, Receipt, CheckCircle, Clock } from 'lucide-react';

export default function NotaDetailsModal({ notaId, onClose, onEdit }) {
  const [dossie, setDossie] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('dados');

  useEffect(() => {
    if (!notaId) return;
    const fetchDossie = async () => {
      setLoading(true);
      try {
        const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        const res = await fetch(`${API_URL}/api/notas/dossie/${notaId}`);
        const json = await res.json();
        if (json.success) {
          setDossie(json.dossie);
        }
      } catch (err) {
        console.error("Erro ao buscar dossiê da nota:", err);
      }
      setLoading(false);
    };
    fetchDossie();
  }, [notaId]);

  if (!notaId) return null;

  const formatMoney = (val) => {
    if (!val) return 'R$ 0,00';
    return Number(val).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  };

  const nota = dossie?.nota_principal;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-container glass-panel" onClick={e => e.stopPropagation()}>
        
        {/* Header Superior */}
        <div className="modal-header">
          <div className="header-title">
            <Receipt size={24} className="text-accent" />
            <h2>Dossiê Interno: Nota {nota?.numero_nf || nota?.id}</h2>
          </div>
          <button className="btn-close" onClick={onClose}>✕</button>
        </div>

        {loading ? (
          <div className="loading-state">Carregando inteligência fiscal...</div>
        ) : dossie && nota ? (
          <div className="modal-content">
            
            {/* Abas Superiores */}
            <div className="tabs-nav">
              <button className={`tab-btn ${activeTab === 'dados' ? 'active' : ''}`} onClick={() => setActiveTab('dados')}>
                🏢 Dados do Fornecedor
              </button>
              <button className={`tab-btn ${activeTab === 'itens' ? 'active' : ''}`} onClick={() => setActiveTab('itens')}>
                📦 Itens da Nota
              </button>
              <button className={`tab-btn ${activeTab === 'guias' ? 'active' : ''}`} onClick={() => setActiveTab('guias')}>
                🏛️ Guias de Impostos <span className="badge-count">{dossie.guias_geradas.length}</span>
              </button>
            </div>

            {/* Conteúdo das Abas */}
            <div className="tab-body">
              
              {/* ABA: DADOS */}
              {activeTab === 'dados' && (
                <div className="dossie-section">
                  <div className="status-hero">
                    <div className="hero-valor">
                      <span className="label">Valor Total</span>
                      <h3>{formatMoney(nota.valor_bruto)}</h3>
                    </div>
                    <div className={`hero-status status-${nota.status.toLowerCase()}`}>
                      {nota.status === 'PAGO' ? <CheckCircle size={20}/> : <Clock size={20}/>}
                      {nota.status}
                    </div>
                  </div>

                  <div className="info-grid">
                    <div className="info-card">
                      <span className="label">Fornecedor</span>
                      <strong>{nota.fornecedor}</strong>
                    </div>
                    <div className="info-card">
                      <span className="label">CNPJ/CPF</span>
                      <strong>{nota.cnpj}</strong>
                    </div>
                    <div className="info-card">
                      <span className="label">Data de Emissão</span>
                      <strong>{nota.dt_emissao}</strong>
                    </div>
                    <div className="info-card">
                      <span className="label">Vencimento Original</span>
                      <strong>{nota.dt_vencimento}</strong>
                    </div>
                    <div className="info-card full-width">
                      <span className="label">Descrição do Sistema</span>
                      <strong>{nota.descricao}</strong>
                    </div>
                  </div>
                </div>
              )}

              {/* ABA: ITENS */}
              {activeTab === 'itens' && (
                <div className="dossie-section">
                  {dossie.itens && dossie.itens.length > 0 ? (
                    <div className="table-responsive">
                      <table className="dossie-table">
                        <thead>
                          <tr>
                            <th>Descrição do Item</th>
                            <th>Valor Total</th>
                          </tr>
                        </thead>
                        <tbody>
                          {dossie.itens.map(item => (
                            <tr key={item.id}>
                              <td>{item.descricao}</td>
                              <td className="text-right font-bold">{formatMoney(item.valor_total)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="empty-state">Nenhum item discriminado na nota.</div>
                  )}
                </div>
              )}

              {/* ABA: GUIAS */}
              {activeTab === 'guias' && (
                <div className="dossie-section">
                  <div className="guias-summary">
                    <ShieldAlert size={28} className="text-warning" />
                    <div>
                      <h4>Provisões Fiscais Automáticas</h4>
                      <p>O Motor Fiscal identificou e gerou automaticamente as guias de pagamento abaixo vinculadas a esta nota.</p>
                    </div>
                    <div className="guias-total">
                      <span className="label">Total Impostos</span>
                      <strong className="text-danger">{formatMoney(dossie.valor_total_impostos)}</strong>
                    </div>
                  </div>

                  {dossie.guias_geradas && dossie.guias_geradas.length > 0 ? (
                    <div className="guias-cards">
                      {dossie.guias_geradas.map(guia => (
                        <div key={guia.id} className="guia-card">
                          <div className="guia-header">
                            <span className="guia-badge">{guia.fornecedor}</span>
                            <span className={`status-badge status-${guia.status.toLowerCase()}`}>{guia.status}</span>
                          </div>
                          <div className="guia-body">
                            <div className="guia-info">
                              <span className="label">Vencimento</span>
                              <strong>{guia.dt_vencimento}</strong>
                            </div>
                            <div className="guia-info text-right">
                              <span className="label">Valor a Pagar</span>
                              <strong className="text-danger">{formatMoney(guia.valor_bruto)}</strong>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="empty-state">Nenhum imposto retido ou provisionado para esta nota.</div>
                  )}
                </div>
              )}

            </div>
            
            <div className="modal-footer">
              <button className="btn-secondary" onClick={onClose}>Fechar</button>
              <button className="btn-primary" onClick={() => { onClose(); onEdit(nota.id); }}>✏️ Editar Nota Original</button>
            </div>

          </div>
        ) : (
          <div className="error-state">Falha ao carregar dossiê da nota.</div>
        )}
      </div>
    </div>
  );
}
