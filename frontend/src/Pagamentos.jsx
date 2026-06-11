import React, { useState, useEffect } from 'react';
import { FileText, X, ChevronRight } from 'lucide-react';
import './Pagamentos.css';

export default function Pagamentos({ onEditNota, onViewNota }) {
  const [notas, setNotas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [empresaFiltro, setEmpresaFiltro] = useState('');
  const [termoBusca, setTermoBusca] = useState('');
  
  // Expanded rows (Nota IDs)
  const [expandedNotas, setExpandedNotas] = useState([]);
  
  // Seleção múltipla de PARCELAS
  const [selectedParcelaIds, setSelectedParcelaIds] = useState([]);
  const [totalSelecionado, setTotalSelecionado] = useState(0);
  
  // Modal de Data de Pagamento / Baixa
  const [modalDataAberto, setModalDataAberto] = useState(false);
  const [dataPagamento, setDataPagamento] = useState('');
  const [valorPago, setValorPago] = useState(''); // Para baixa parcial
  const [baixaType, setBaixaType] = useState(null); // 'individual' ou 'lote'
  
  const [parcelaAtual, setParcelaAtual] = useState(null); // Objeto da parcela sendo paga
  const [fornecedorAtual, setFornecedorAtual] = useState('');
  
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
        setSelectedParcelaIds([]);
        setTotalSelecionado(0);
      }
    } catch (err) {
      console.error("Erro ao buscar notas", err);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchNotas();
  }, [empresaFiltro]);

  // Recalcular total selecionado sempre que a seleção mudar
  useEffect(() => {
    let sum = 0;
    notas.forEach(nota => {
      nota.parcelas?.forEach(p => {
        if (selectedParcelaIds.includes(p.id)) {
          sum += Number(p.valor || 0);
        }
      });
    });
    setTotalSelecionado(sum);
  }, [selectedParcelaIds, notas]);

  const toggleExpand = (notaId) => {
    if (expandedNotas.includes(notaId)) {
      setExpandedNotas(expandedNotas.filter(id => id !== notaId));
    } else {
      setExpandedNotas([...expandedNotas, notaId]);
    }
  };

  const handleSelectParcela = (parcelaId) => {
    if (selectedParcelaIds.includes(parcelaId)) {
      setSelectedParcelaIds(selectedParcelaIds.filter(id => id !== parcelaId));
    } else {
      setSelectedParcelaIds([...selectedParcelaIds, parcelaId]);
    }
  };

  const openBaixaModal = (parcela, fornecedor) => {
    setBaixaType('individual');
    setParcelaAtual(parcela);
    setFornecedorAtual(fornecedor);
    setDataPagamento(new Date().toISOString().split('T')[0]); // Hoje por padrão
    setValorPago(parcela.valor); // Sugere o valor total da parcela
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
        url = `${API_URL}/api/parcelas/dar_baixa`;
        body = { 
          parcela_id: parcelaAtual.id, 
          valor_pago: Number(valorPago),
          data_pagamento: dataPagamento 
        };
      } else {
        url = `${API_URL}/api/parcelas/dar_baixa_lote`;
        // Monta o payload do lote com o valor integral de cada parcela selecionada
        const parcelasPayload = [];
        notas.forEach(nota => {
          nota.parcelas?.forEach(p => {
            if (selectedParcelaIds.includes(p.id)) {
              parcelasPayload.push({
                parcela_id: p.id,
                valor_pago: Number(p.valor),
                data_pagamento: dataPagamento
              });
            }
          });
        });
        body = { parcelas: parcelasPayload };
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

  const cancelarNota = async (notaId, fornecedor) => {
    if (!window.confirm(`Tem certeza que deseja cancelar a nota de ${fornecedor}?`)) return;
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const res = await fetch(`${API_URL}/api/notas/dar_baixa`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: notaId, novo_status: 'CANCELADO' })
      });
      const json = await res.json();
      if (json.success) fetchNotas();
      else alert("Erro ao cancelar: " + json.error);
    } catch (err) {
      alert("Erro de conexão.");
    }
  };

  const [dataFiltro, setDataFiltro] = useState('');
  const [categoriaFiltro, setCategoriaFiltro] = useState('');
  const [fornecedorFiltro, setFornecedorFiltro] = useState('');
  const [sortConfig, setSortConfig] = useState({ key: 'fornecedor', direction: 'asc' });

  const formatMoney = (val) => {
    if (!val) return 'R$ 0,00';
    return Number(val).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  };

  // Extract unique categories and suppliers from fetched notes for the dropdowns
  const categoriasUnicas = [...new Set(notas.map(n => n.categoria).filter(Boolean))].sort();
  const fornecedoresUnicos = [...new Set(notas.map(n => n.fornecedor).filter(Boolean))].sort();

  const notasFiltradas = notas.filter(n => {
    // Busca Livre
    if (termoBusca) {
      const termo = termoBusca.toLowerCase();
      const forn = (n.fornecedor || '').toLowerCase();
      const desc = (n.descricao || '').toLowerCase();
      if (!forn.includes(termo) && !desc.includes(termo)) return false;
    }
    // Categoria
    if (categoriaFiltro && n.categoria !== categoriaFiltro) return false;
    // Fornecedor
    if (fornecedorFiltro && n.fornecedor !== fornecedorFiltro) return false;
    // Data de Vencimento
    if (dataFiltro) {
      // Formata data do input (YYYY-MM-DD) para comparar com DD/MM/YYYY
      const [year, month, day] = dataFiltro.split('-');
      const dataBr = `${day}/${month}/${year}`;
      
      // Verifica se a nota ou alguma de suas parcelas vence nesta data
      const vencNota = n.dt_vencimento === dataBr;
      const vencParcela = n.parcelas?.some(p => p.dt_vencimento === dataBr);
      if (!vencNota && !vencParcela) return false;
    }

    return true;
  });

  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') direction = 'desc';
    setSortConfig({ key, direction });
  };

  const notasOrdenadas = [...notasFiltradas].sort((a, b) => {
    if (!sortConfig.key) return 0;
    
    let valA = a[sortConfig.key];
    let valB = b[sortConfig.key];

    if (sortConfig.key === 'valor_total') {
      valA = Number(valA || 0);
      valB = Number(valB || 0);
    } else {
      valA = String(valA || '').toLowerCase();
      valB = String(valB || '').toLowerCase();
    }

    if (valA < valB) return sortConfig.direction === 'asc' ? -1 : 1;
    if (valA > valB) return sortConfig.direction === 'asc' ? 1 : -1;
    return 0;
  });

  const isAllSelected = notasOrdenadas.length > 0 && notasOrdenadas.every(nota => 
    nota.parcelas?.every(p => selectedParcelaIds.includes(p.id))
  );

  const handleSelectAll = (e) => {
    if (e.target.checked) {
      const allIds = [];
      notasOrdenadas.forEach(nota => {
        nota.parcelas?.forEach(p => allIds.push(p.id));
      });
      setSelectedParcelaIds(allIds);
    } else {
      setSelectedParcelaIds([]);
    }
  };

  const openCancelarLote = async () => {
    if (!window.confirm(`Tem certeza que deseja EXCLUIR/CANCELAR as notas de todas as parcelas selecionadas?\nEssa ação não pode ser desfeita.`)) return;
    
    const notasToCancel = new Set();
    notas.forEach(nota => {
      nota.parcelas?.forEach(p => {
        if (selectedParcelaIds.includes(p.id)) notasToCancel.add(nota.id);
      });
    });

    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      for (let notaId of notasToCancel) {
        await fetch(`${API_URL}/api/notas/dar_baixa`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id: notaId, novo_status: 'CANCELADO' })
        });
      }
      setSelectedParcelaIds([]);
      fetchNotas();
    } catch (err) {
      alert("Erro de conexão ao cancelar.");
    }
  };

  return (
    <>
      <div className="pagamentos-container glass-panel">
        <div className="pagamentos-header">
          <div>
            <h2>💸 Contas a Pagar (Pendentes)</h2>
            <p className="text-muted">Expanda as notas para pagar as parcelas (vencimentos).</p>
          </div>
          
          <div className="filtros" style={{ gap: '12px' }}>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <label>Empresa:</label>
              <select className="input-field" value={empresaFiltro} onChange={e => setEmpresaFiltro(e.target.value)}>
                <option value="">TODAS</option>
                <option value="LALUA">LALUA</option>
                <option value="SOLAR">SOLAR</option>
              </select>
            </div>
            
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <label>Vencimento:</label>
              <input 
                type="date" 
                className="input-field" 
                value={dataFiltro}
                onChange={e => setDataFiltro(e.target.value)}
              />
            </div>

            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <label>Categoria:</label>
              <select className="input-field" value={categoriaFiltro} onChange={e => setCategoriaFiltro(e.target.value)}>
                <option value="">Todas</option>
                {categoriasUnicas.map(cat => <option key={cat} value={cat}>{cat}</option>)}
              </select>
            </div>

            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <label>Fornecedor:</label>
              <select className="input-field" value={fornecedorFiltro} onChange={e => setFornecedorFiltro(e.target.value)}>
                <option value="">Todos</option>
                {fornecedoresUnicos.map(f => <option key={f} value={f}>{f}</option>)}
              </select>
            </div>
            
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <label>Busca Livre:</label>
              <input 
                type="text" 
                placeholder="Descrição, NFe..." 
                value={termoBusca} 
                onChange={e => setTermoBusca(e.target.value)}
                className="input-field"
                style={{ width: '130px' }}
              />
            </div>
            
            <button onClick={fetchNotas} className="btn-refresh">🔄 Atualizar</button>
          </div>
        </div>

        <div className="table-responsive">
          {loading ? (
            <div className="loading-state">Carregando vencimentos...</div>
          ) : notasFiltradas.length === 0 ? (
            <div className="empty-state">Nenhum vencimento pendente ou encontrado nos filtros! 🎉</div>
          ) : (
            <table className="pagamentos-table">
              <thead>
                <tr>
                  <th style={{ width: '40px', textAlign: 'center' }}>
                    <input 
                      type="checkbox" 
                      checked={isAllSelected} 
                      onChange={handleSelectAll} 
                      style={{ cursor: 'pointer', transform: 'scale(1.2)' }} 
                      title="Selecionar Todas as Parcelas Filtradas" 
                    />
                  </th>
                  <th onClick={() => handleSort('fornecedor')} style={{cursor:'pointer'}}>Fornecedor {sortConfig.key==='fornecedor' ? (sortConfig.direction==='asc'?'↑':'↓'):''}</th>
                  <th onClick={() => handleSort('empresa')} style={{cursor:'pointer'}}>Empresa {sortConfig.key==='empresa' ? (sortConfig.direction==='asc'?'↑':'↓'):''}</th>
                  <th onClick={() => handleSort('numero_nf')} style={{cursor:'pointer'}}>NFe {sortConfig.key==='numero_nf' ? (sortConfig.direction==='asc'?'↑':'↓'):''}</th>
                  <th onClick={() => handleSort('descricao')} style={{cursor:'pointer'}}>Descrição {sortConfig.key==='descricao' ? (sortConfig.direction==='asc'?'↑':'↓'):''}</th>
                  <th onClick={() => handleSort('valor_total')} className="text-right" style={{cursor:'pointer'}}>Total da Nota {sortConfig.key==='valor_total' ? (sortConfig.direction==='asc'?'↑':'↓'):''}</th>
                  <th className="text-center">Ações</th>
                </tr>
              </thead>
              <tbody>
                {notasOrdenadas.map(nota => {
                  const isExpanded = expandedNotas.includes(nota.id);
                  const numParcelas = nota.parcelas?.length || 0;
                  
                  return (
                    <React.Fragment key={nota.id}>
                      <tr className="master-row" onClick={() => toggleExpand(nota.id)}>
                        <td className="text-center">
                          <ChevronRight 
                            size={20} 
                            className={`chevron ${isExpanded ? 'open' : ''}`}
                            color="var(--accent-color)" 
                          />
                        </td>
                        <td className="font-bold">{nota.fornecedor}</td>
                        <td>
                          <div style={{fontSize: '12px', color: 'var(--text-muted)'}}>{nota.empresa}</div>
                          <div>{nota.filial}</div>
                        </td>
                        <td><span className="badge badge-neutral">{nota.numero_nf || '-'}</span></td>
                        <td>{nota.descricao}</td>
                        <td className="text-right text-accent font-bold">
                          {formatMoney(nota.valor_bruto)}
                          <div style={{fontSize: '11px', color: 'var(--text-muted)'}}>{numParcelas} Parcela(s)</div>
                        </td>
                        <td className="actions-cell text-center" onClick={e => e.stopPropagation()}>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '12px' }}>
                            <label style={{ display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer', background: 'rgba(255,255,255,0.05)', padding: '6px 10px', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.1)' }}>
                              <input 
                                type="checkbox" 
                                style={{ cursor: 'pointer', transform: 'scale(1.2)' }}
                                checked={numParcelas > 0 && nota.parcelas.every(p => selectedParcelaIds.includes(p.id))}
                                onChange={(e) => {
                                  const isChecked = e.target.checked;
                                  const ids = nota.parcelas?.map(p => p.id) || [];
                                  if (isChecked) {
                                    const newIds = ids.filter(id => !selectedParcelaIds.includes(id));
                                    setSelectedParcelaIds(prev => [...prev, ...newIds]);
                                  } else {
                                    setSelectedParcelaIds(prev => prev.filter(id => !ids.includes(id)));
                                  }
                                }}
                              />
                              <span style={{ fontSize: '12px', fontWeight: 'bold' }}>Selecionar</span>
                            </label>

                            <button 
                              className="btn-details" 
                              onClick={() => onViewNota(nota.id)}
                              style={{ padding: '6px 12px', background: 'var(--surface-raised)', border: '1px solid var(--border-color)', borderRadius: '4px', cursor: 'pointer', color: '#fff' }}
                            >
                              👁️ Ver Nota
                            </button>
                            <button 
                              className="btn-cancel" 
                              onClick={() => cancelarNota(nota.id, nota.fornecedor)}
                              title="Cancelar Nota Individualmente"
                              style={{ background: 'transparent', border: 'none', cursor: 'pointer', opacity: '0.6', fontSize: '1.2rem', padding: '4px' }}
                            >
                              ❌
                            </button>
                          </div>
                        </td>
                      </tr>
                      
                      {/* Parcelas Expandidas */}
                      {isExpanded && nota.parcelas && nota.parcelas.filter(p => p.status !== 'PAGO').map((parcela, idx) => {
                        const vencSplit = parcela.dt_vencimento ? parcela.dt_vencimento.split('/') : [];
                        let isAtrasada = false;
                        if (vencSplit.length === 3) {
                          const dataVenc = new Date(`${vencSplit[2]}-${vencSplit[1]}-${vencSplit[0]}T00:00:00`);
                          const hoje = new Date();
                          hoje.setHours(0,0,0,0);
                          if (dataVenc < hoje) isAtrasada = true;
                        }

                        return (
                          <tr key={parcela.id || `mock_${idx}`} className={`parcela-row ${selectedParcelaIds.includes(parcela.id) ? 'row-selected' : ''}`}>
                            <td className="text-center" style={{ borderLeft: '3px solid var(--accent-color)' }}>
                              <input 
                                type="checkbox" 
                                checked={selectedParcelaIds.includes(parcela.id)}
                                onChange={() => handleSelectParcela(parcela.id)}
                                style={{ cursor: 'pointer' }}
                              />
                            </td>
                            <td colSpan="4" style={{ paddingLeft: '20px' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                <span className={`badge ${isAtrasada ? 'badge-danger' : 'badge-neutral'}`}>
                                  {parcela.dt_vencimento || '-'}
                                </span>
                                <span>Parcela {parcela.parcela} de {numParcelas}</span>
                              </div>
                            </td>
                            <td className="text-right font-bold">
                              {formatMoney(parcela.valor)}
                            </td>
                            <td className="text-center">
                              <button 
                                className="btn-baixa" 
                                onClick={() => openBaixaModal(parcela, nota.fornecedor)}
                              >
                                ✅ Pagar Parcela
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </React.Fragment>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>

        {selectedParcelaIds.length > 0 && (
          <div className="floating-batch-bar glass-panel">
            <div className="batch-info">
              <span className="batch-count">{selectedParcelaIds.length} parcelas selecionadas</span>
              <span className="batch-total">Total: <strong>{formatMoney(totalSelecionado)}</strong></span>
            </div>
            <div style={{ display: 'flex', gap: '12px' }}>
              <button className="btn-batch-baixa" onClick={openBaixaLoteModal} style={{ background: 'linear-gradient(135deg, #10b981, #059669)', color: 'white' }}>
                ✅ Pagar Seleção
              </button>
              <button className="btn-batch-baixa" onClick={openCancelarLote} style={{ background: 'rgba(239, 68, 68, 0.2)', color: '#ef4444', border: '1px solid rgba(239, 68, 68, 0.3)', boxShadow: 'none' }}>
                ❌ Excluir Seleção
              </button>
            </div>
          </div>
        )}
      </div>

      {modalDataAberto && (
        <div className="modal-overlay">
          <div className="modal-content glass-panel">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h3 style={{ margin: 0 }}>📅 Confirmar Pagamento</h3>
              <button style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer' }} onClick={() => setModalDataAberto(false)}>
                <X size={24} />
              </button>
            </div>
            
            {baixaType === 'lote' ? (
              <div style={{ marginBottom: '20px' }}>
                <p>Dar baixa em <strong>{selectedParcelaIds.length} parcelas</strong> totalizando <strong>{formatMoney(totalSelecionado)}</strong>.</p>
                <div className="badge badge-warning" style={{ marginTop: '10px' }}>Nota: Em lote, as baixas são integrais.</div>
              </div>
            ) : (
              <div style={{ marginBottom: '20px' }}>
                <p>Fornecedor: <strong>{fornecedorAtual}</strong></p>
                <p>Vencimento: <strong>{parcelaAtual?.dt_vencimento}</strong> (Parcela {parcelaAtual?.parcela})</p>
                <div style={{ marginTop: '15px' }}>
                  <label style={{ display: 'block', marginBottom: '5px', color: 'var(--text-muted)' }}>Valor Pago (R$):</label>
                  <input 
                    type="number" 
                    step="0.01"
                    value={valorPago} 
                    onChange={e => setValorPago(e.target.value)}
                    className="input-field"
                    style={{ fontSize: '1.2rem', fontWeight: 'bold', color: 'var(--accent-color)' }}
                  />
                  {Number(valorPago) < Number(parcelaAtual?.valor) && (
                    <div style={{ marginTop: '8px', fontSize: '0.85rem', color: '#f59e0b' }}>
                      ⚠️ <strong>Atenção:</strong> Pagamento inferior ao valor total ({formatMoney(parcelaAtual?.valor)}). O saldo será transformado em uma nova parcela pendente (Baixa Parcial).
                    </div>
                  )}
                </div>
              </div>
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
              <button className="btn-save" onClick={confirmarBaixa}>Confimar Baixa</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
