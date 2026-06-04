import { useState, useEffect } from 'react';
import { FileText, X } from 'lucide-react';
import './Pagamentos.css';

export default function Pagamentos({ onEditNota, onViewNota }) {
  const [notas, setNotas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [empresaFiltro, setEmpresaFiltro] = useState('');
  const [termoBusca, setTermoBusca] = useState('');
  
  // Seleção múltipla
  const [selectedIds, setSelectedIds] = useState([]);
  
  // Modal de Data de Pagamento
  const [modalDataAberto, setModalDataAberto] = useState(false);
  const [dataPagamento, setDataPagamento] = useState(new Date().toISOString().split('T')[0]);
  const [baixaType, setBaixaType] = useState(null); // 'individual' ou 'lote'
  const [notaAtualId, setNotaAtualId] = useState(null);
  const [fornecedorAtual, setFornecedorAtual] = useState('');

  // OFX
  const [showOfxModal, setShowOfxModal] = useState(false);
  const [ofxLoading, setOfxLoading] = useState(false);
  const [ofxResult, setOfxResult] = useState(null);

  const fetchNotas = async () => {
    setLoading(true);
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const url = empresaFiltro 
        ? `${API_URL}/api/notas/pendentes?empresa=${empresaFiltro}` 
        : `${API_URL}/api/notas/pendentes`;
        
      const res = await fetch(url);
      const json = await res.json();
      if (json.success) {
        setNotas(json.notas);
        setSelectedIds([]); // Limpa a seleção ao recarregar
      }
    } catch (err) {
      console.error("Erro ao buscar notas", err);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchNotas();
  }, [empresaFiltro]);

  const openBaixaModal = (id, fornecedor) => {
    setBaixaType('individual');
    setNotaAtualId(id);
    setFornecedorAtual(fornecedor);
    setDataPagamento(new Date().toISOString().split('T')[0]); // Hoje por padrão
    setModalDataAberto(true);
  };

  const openBaixaLoteModal = () => {
    setBaixaType('lote');
    setDataPagamento(new Date().toISOString().split('T')[0]);
    setModalDataAberto(true);
  };

  const confirmarBaixa = async () => {
    setModalDataAberto(false);
    
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      let url = '';
      let body = {};

      if (baixaType === 'individual') {
        url = `${API_URL}/api/notas/dar_baixa`;
        body = { id: notaAtualId, novo_status: 'PAGO', data_pagamento: dataPagamento };
      } else {
        url = `${API_URL}/api/notas/dar_baixa_lote`;
        body = { ids: selectedIds, novo_status: 'PAGO', data_pagamento: dataPagamento };
      }

      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      const json = await res.json();
      
      if (json.success) {
        fetchNotas();
      } else {
        alert("Erro ao dar baixa: " + json.error);
      }
    } catch (err) {
      alert("Erro de conexão.");
    }
  };

  const cancelarNota = async (id, fornecedor) => {
    const confirmar = window.confirm(`Deseja CANCELAR a nota de ${fornecedor}?`);
    if (!confirmar) return;

    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const res = await fetch(`${API_URL}/api/notas/dar_baixa`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, novo_status: 'CANCELADO' })
      });
      const json = await res.json();
      
      if (json.success) {
        fetchNotas();
      } else {
        alert("Erro ao cancelar: " + json.error);
      }
    } catch (err) {
      alert("Erro de conexão.");
    }
  };

  const formatMoney = (val) => {
    if (!val) return 'R$ 0,00';
    return Number(val).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  };

  const notasFiltradas = notas.filter(n => {
    if (!termoBusca) return true;
    const termo = termoBusca.toLowerCase();
    const fornecedor = (n.fornecedor || '').toLowerCase();
    const descricao = (n.descricao || '').toLowerCase();
    const dataVenc = (n.dt_vencimento || '').toLowerCase();
    return fornecedor.includes(termo) || descricao.includes(termo) || dataVenc.includes(termo);
  });

  const totalSelecionado = notasFiltradas
    .filter(n => selectedIds.includes(n.id))
    .reduce((acc, curr) => acc + Number(curr.valor_bruto || 0), 0);

  const handleSelectAll = (e) => {
    if (e.target.checked) {
      setSelectedIds(notasFiltradas.map(n => n.id));
    } else {
      setSelectedIds([]);
    }
  };

  const handleSelectRow = (id) => {
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter(i => i !== id));
    } else {
      setSelectedIds([...selectedIds, id]);
    }
  };

  const handleUploadOfx = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setOfxLoading(true);
    setOfxResult(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://localhost:8000/api/conciliacao/ofx", {
        method: "POST",
        body: formData
      });
      const data = await res.json();
      if (data.success) {
        setOfxResult(data);
        fetchNotas(); // Update list after match
      } else {
        alert("Erro no processamento do OFX: " + data.error);
      }
    } catch (err) {
      alert("Erro ao enviar OFX.");
    } finally {
      setOfxLoading(false);
      e.target.value = null; // reset
    }
  };

  return (
    <>
      <div className="pagamentos-container glass-panel">
        <div className="pagamentos-header">
          <div>
            <h2>💸 Pagamentos Pendentes</h2>
            <p className="text-muted">Lista de despesas e notas lançadas aguardando pagamento.</p>
          </div>
          
          <div className="filtros">
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <label>Filtrar por Empresa:</label>
              <select value={empresaFiltro} onChange={e => setEmpresaFiltro(e.target.value)}>
                <option value="">TODAS</option>
                <option value="LALUA">LALUA</option>
                <option value="SOLAR">SOLAR</option>
              </select>
            </div>
            
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <label>Buscar (Data, ISS...):</label>
              <input 
                type="text" 
                placeholder="Digite para filtrar..." 
                value={termoBusca} 
                onChange={e => setTermoBusca(e.target.value)}
                className="input-field"
                style={{ width: '200px' }}
              />
            </div>
            
            <button onClick={() => setShowOfxModal(true)} className="btn-gerar-moderno" style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <FileText size={18} /> Conciliar OFX
            </button>
            <button onClick={fetchNotas} className="btn-refresh">🔄 Atualizar</button>
          </div>
        </div>

        <div className="table-responsive">
          {loading ? (
            <div className="loading-state">Carregando notas...</div>
          ) : notasFiltradas.length === 0 ? (
            <div className="empty-state">Nenhum pagamento encontrado para este filtro. 🎉</div>
          ) : (
            <table className="pagamentos-table">
              <thead>
                <tr>
                  <th style={{ width: '40px', textAlign: 'center' }}>
                    <input 
                      type="checkbox" 
                      checked={notasFiltradas.length > 0 && selectedIds.length === notasFiltradas.length}
                      onChange={handleSelectAll}
                      style={{ cursor: 'pointer' }}
                    />
                  </th>
                  <th>Vencimento</th>
                  <th>Fornecedor</th>
                  <th>Empresa / Filial</th>
                  <th>Descrição</th>
                  <th className="text-right">Valor</th>
                  <th className="text-center">Ações</th>
                </tr>
              </thead>
              <tbody>
                {notasFiltradas.map(nota => {
                  const vencSplit = nota.dt_vencimento ? nota.dt_vencimento.split('/') : [];
                  let isAtrasada = false;
                  if (vencSplit.length === 3) {
                    const dataVenc = new Date(`${vencSplit[2]}-${vencSplit[1]}-${vencSplit[0]}T00:00:00`);
                    const hoje = new Date();
                    hoje.setHours(0,0,0,0);
                    if (dataVenc < hoje) isAtrasada = true;
                  }

                  return (
                    <tr key={nota.id} className={selectedIds.includes(nota.id) ? 'row-selected' : ''}>
                      <td style={{ textAlign: 'center' }}>
                        <input 
                          type="checkbox" 
                          checked={selectedIds.includes(nota.id)}
                          onChange={() => handleSelectRow(nota.id)}
                          style={{ cursor: 'pointer' }}
                        />
                      </td>
                      <td>
                        <span className={`badge ${isAtrasada ? 'badge-danger' : 'badge-neutral'}`}>
                          {nota.dt_vencimento || '-'}
                        </span>
                      </td>
                      <td className="font-bold">{nota.fornecedor}</td>
                      <td>
                        <div style={{fontSize: '12px', color: 'var(--text-muted)'}}>{nota.empresa}</div>
                        <div>{nota.filial}</div>
                      </td>
                      <td>{nota.descricao}</td>
                      <td className="text-right text-accent font-bold">
                        {formatMoney(nota.valor_bruto)}
                      </td>
                      <td className="actions-cell">
                        <button 
                          className="btn-details" 
                          onClick={() => onViewNota(nota.id)}
                          title="Ver Detalhes"
                          style={{ marginRight: '8px', padding: '6px 12px', background: 'var(--surface-raised)', border: '1px solid var(--border-color)', borderRadius: '4px', cursor: 'pointer', color: '#fff' }}
                        >
                          👁️ Detalhes
                        </button>
                        <button 
                          className="btn-baixa" 
                          onClick={() => openBaixaModal(nota.id, nota.fornecedor)}
                          title="Registrar Pagamento"
                        >
                          ✅ Dar Baixa
                        </button>
                        <button 
                          className="btn-cancel" 
                          onClick={() => cancelarNota(nota.id, nota.fornecedor)}
                          title="Cancelar Nota"
                        >
                          ❌
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>

        {selectedIds.length > 0 && (
          <div className="floating-batch-bar glass-panel">
            <div className="batch-info">
              <span className="batch-count">{selectedIds.length} itens selecionados</span>
              <span className="batch-total">Total: <strong>{formatMoney(totalSelecionado)}</strong></span>
            </div>
            <button className="btn-batch-baixa" onClick={openBaixaLoteModal}>
              ✅ Dar Baixa em Lote
            </button>
          </div>
        )}
      </div>

      {showOfxModal && (
        <div className="modal-overlay">
          <div className="modal-content glass-panel" style={{ maxWidth: '600px' }}>
            <div className="modal-header">
              <h3>Conciliação Bancária Automática (OFX)</h3>
              <button className="close-btn" onClick={() => { setShowOfxModal(false); setOfxResult(null); }}>
                <X size={20} />
              </button>
            </div>
            <div className="modal-body">
              {!ofxResult ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                  <p>Faça o upload do extrato bancário no formato <b>.ofx</b> gerado pelo seu banco. O sistema cruzará as saídas pelo <b>valor exato</b> e fará a baixa automática das notas correspondentes.</p>
                  
                  <div className="upload-zone" style={{ minHeight: '150px' }}>
                    <input 
                      type="file" 
                      id="ofx-upload" 
                      accept=".ofx" 
                      onChange={handleUploadOfx} 
                      disabled={ofxLoading}
                    />
                    <label htmlFor="ofx-upload" className={ofxLoading ? "disabled" : ""}>
                      <FileText size={36} className="upload-icon" />
                      <h4>{ofxLoading ? "Processando e Conciliando..." : "Clique para selecionar o OFX"}</h4>
                    </label>
                  </div>
                </div>
              ) : (
                <div className="ofx-results">
                  <div className="summary-cards" style={{ display: 'flex', gap: '15px', marginBottom: '20px' }}>
                    <div className="summary-card highlight" style={{ flex: 1 }}>
                      <h4>✅ Baixas Automáticas</h4>
                      <h2>{ofxResult.matched.length}</h2>
                    </div>
                    <div className="summary-card" style={{ flex: 1 }}>
                      <h4>❌ Não Encontrados</h4>
                      <h2>{ofxResult.unmatched.length}</h2>
                    </div>
                  </div>

                  {ofxResult.matched.length > 0 && (
                    <div style={{ marginBottom: '20px' }}>
                      <h4 style={{ color: 'var(--success-color)' }}>Pagamentos Sincronizados com Sucesso</h4>
                      <ul style={{ maxHeight: '150px', overflowY: 'auto', fontSize: '0.9rem', paddingLeft: '20px' }}>
                        {ofxResult.matched.map(m => (
                          <li key={m.tx_id}>
                            <b>{m.tx_data}</b> - {formatMoney(m.tx_valor)} - Bateu com: {m.nota_fornecedor}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {ofxResult.unmatched.length > 0 && (
                    <div>
                      <h4 style={{ color: 'var(--danger-color)' }}>Saídas sem Nota Correspondente</h4>
                      <p className="text-muted" style={{ fontSize: '0.8rem' }}>Estes valores saíram do banco mas não havia nota pendente com este valor exato.</p>
                      <ul style={{ maxHeight: '150px', overflowY: 'auto', fontSize: '0.9rem', paddingLeft: '20px' }}>
                        {ofxResult.unmatched.map(u => (
                          <li key={u.tx_id}>
                            <b>{u.tx_data}</b> - {formatMoney(u.tx_valor)} <i>({u.tx_memo})</i>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {modalDataAberto && (
        <div className="modal-overlay">
          <div className="modal-content date-modal">
            <h3>📅 Confirmar Pagamento</h3>
            {baixaType === 'lote' ? (
              <p>Dar baixa em <strong>{selectedIds.length} notas</strong> totalizando <strong>{formatMoney(totalSelecionado)}</strong>.</p>
            ) : (
              <p>Confirmar pagamento para <strong>{fornecedorAtual}</strong>?</p>
            )}
            
            <div className="form-group" style={{ marginTop: '20px' }}>
              <label>Data de Efetivação do Pagamento:</label>
              <input 
                type="date" 
                value={dataPagamento} 
                onChange={e => setDataPagamento(e.target.value)}
                className="input-field"
              />
            </div>

            <div className="modal-actions" style={{ marginTop: '30px', display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button className="btn-cancelar" onClick={() => setModalDataAberto(false)}>Cancelar</button>
              <button className="btn-save" onClick={confirmarBaixa}>Confirmar Baixa</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
