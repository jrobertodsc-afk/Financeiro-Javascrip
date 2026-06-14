import React, { useState, useEffect } from 'react';
import { 
  Send, 
  Download, 
  RefreshCw, 
  Plus, 
  Settings, 
  CheckCircle2, 
  AlertTriangle, 
  Loader2, 
  Search, 
  Trash, 
  FileText,
  FileCheck,
  Building
} from 'lucide-react';
import './GnreSispag.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function GnreSispag() {
  const [activeSubTab, setActiveSubTab] = useState('guias'); // 'guias' | 'difal'
  const [guias, setGuias] = useState([]);
  const [notasDifal, setNotasDifal] = useState([]);
  const [loadingGuias, setLoadingGuias] = useState(false);
  const [loadingNotas, setLoadingNotas] = useState(false);
  const [simulado, setSimulado] = useState(true); // Modo simulado ligado por padrão
  const [ambiente, setAmbiente] = useState(2); // 2 = Homologação, 1 = Produção
  const [empresa, setEmpresa] = useState('LALUA');
  const [busca, setBusca] = useState('');
  
  // Seleção múltipla de guias
  const [selectedGuiaIds, setSelectedGuiaIds] = useState([]);
  
  // Modal de Nova Guia Manual
  const [modalNovaGuia, setModalNovaGuia] = useState(false);
  const [novaGuia, setNovaGuia] = useState({
    uf_favorecida: 'PE',
    cnpj_emitente: '10436619000105',
    codigo_receita: '100102',
    valor: '',
    data_vencimento: '',
    documento_origem: '',
    tipo_documento_origem: '10',
    chave_acesso_nfe: ''
  });

  // Modal de Download CNAB
  const [modalCnab, setModalCnab] = useState(false);
  const [cnabContent, setCnabContent] = useState('');
  const [cnabFilename, setCnabFilename] = useState('');

  // Status de operações em andamento
  const [transmitindo, setTransmitindo] = useState(false);
  const [consultando, setConsultando] = useState(false);
  const [gerandoCnab, setGerandoCnab] = useState(false);

  // Carrega Guias GNRE
  const fetchGuias = async () => {
    setLoadingGuias(true);
    try {
      const res = await fetch(`${API_URL}/api/gnre/guias?busca=${busca}`);
      const data = await res.json();
      if (data.success) {
        setGuias(data.guias);
      }
    } catch (err) {
      console.error("Erro ao buscar guias GNRE", err);
    }
    setLoadingGuias(false);
  };

  // Carrega Notas com DIFAL Pendente
  const fetchNotasDifal = async () => {
    setLoadingNotas(true);
    try {
      const res = await fetch(`${API_URL}/api/gnre/notas_difal`);
      const data = await res.json();
      if (data.success) {
        setNotasDifal(data.notas);
      }
    } catch (err) {
      console.error("Erro ao buscar notas DIFAL", err);
    }
    setLoadingNotas(false);
  };

  useEffect(() => {
    fetchGuias();
  }, [busca]);

  useEffect(() => {
    if (activeSubTab === 'difal') {
      fetchNotasDifal();
    }
  }, [activeSubTab]);

  // Transmitir guias selecionadas
  const handleTransmitir = async () => {
    if (selectedGuiaIds.length === 0) return;
    setTransmitindo(true);
    try {
      const res = await fetch(`${API_URL}/api/gnre/transmitir`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          numero_tx_list: selectedGuiaIds,
          empresa,
          ambiente,
          simulado
        })
      });
      const data = await res.json();
      if (data.success) {
        alert(data.mensagem || "Guias transmitidas com sucesso!");
        fetchGuias();
        setSelectedGuiaIds([]);
      } else {
        alert("Erro na transmissão: " + data.error);
      }
    } catch (err) {
      alert("Erro na requisição: " + err.message);
    }
    setTransmitindo(false);
  };

  // Consultar lote de guias pelo recibo
  const handleConsultarRecibo = async (recibo) => {
    if (!recibo) return;
    setConsultando(true);
    try {
      const res = await fetch(`${API_URL}/api/gnre/consultar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          numero_recibo: recibo,
          empresa,
          ambiente,
          simulado
        })
      });
      const data = await res.json();
      if (data.success) {
        alert(data.mensagem || "Consulta realizada com sucesso!");
        fetchGuias();
      } else {
        alert("Erro na consulta: " + data.error);
      }
    } catch (err) {
      alert("Erro na requisição: " + err.message);
    }
    setConsultando(false);
  };

  // Gerar remessa SISPAG (CNAB 240)
  const handleGerarSispag = async () => {
    if (selectedGuiaIds.length === 0) return;
    
    // Filtra para garantir que apenas guias com SUCESSO são incluídas
    const guiasSucesso = guias.filter(g => selectedGuiaIds.includes(g.numero_tx) && g.status === 'SUCESSO');
    if (guiasSucesso.length === 0) {
      alert("Nenhuma guia com status 'SUCESSO' selecionada. Apenas guias validadas podem ser enviadas ao banco.");
      return;
    }

    setGerandoCnab(true);
    try {
      const res = await fetch(`${API_URL}/api/gnre/gerar_remessa`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          numero_tx_list: guiasSucesso.map(g => g.numero_tx),
          dados_empresa: {
            cnpj: empresa === 'LALUA' ? '10436619000105' : '12345678000199', // CNPJ fictício se Solar
            razao_social: empresa === 'LALUA' ? 'BOAH COMERCIO VAREJISTA' : 'SOLAR DISTRIBUIDORA LTDA',
            agencia: '01234',
            conta: '0012345',
            dac: '6'
          }
        })
      });
      const data = await res.json();
      if (data.success) {
        setCnabContent(data.conteudo);
        setCnabFilename(data.arquivo);
        setModalCnab(true);
        fetchGuias();
        setSelectedGuiaIds([]);
      } else {
        alert("Erro ao gerar SISPAG: " + data.error);
      }
    } catch (err) {
      alert("Erro na requisição: " + err.message);
    }
    setGerandoCnab(false);
  };

  // Criar guia a partir da nota DIFAL
  const handleImportarNotaDifal = async (nota) => {
    try {
      const valor_difal = Number(nota.valor_difal || 0);
      if (valor_difal <= 0) return;

      const formatarData = (dataStr) => {
        // dataStr vém como DD/MM/YYYY -> converter para YYYY-MM-DD
        if (dataStr && dataStr.includes('/')) {
          const [dia, mes, ano] = dataStr.split('/');
          return `${ano}-${mes}-${dia}`;
        }
        return dataStr || '';
      };

      const res = await fetch(`${API_URL}/api/gnre/salvar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          nota_ref_tx: nota.numero_tx,
          uf_favorecida: nota.uf || 'PE',
          cnpj_emitente: '10436619000105', // Seu CNPJ
          codigo_receita: '100102', // DIFAL Consumidor Final
          valor: valor_difal,
          data_vencimento: formatarData(nota.dt_vencimento),
          documento_origem: nota.numero_nf || nota.numero_tx,
          tipo_documento_origem: '10',
          chave_acesso_nfe: nota.observacao?.match(/Sefaz: ([0-9]{44})/)?.[1] || ''
        })
      });
      const data = await res.json();
      if (data.success) {
        alert(`Guia criada com sucesso para a Nota ${nota.numero_nf || nota.numero_tx}!`);
        fetchNotasDifal();
        fetchGuias();
      } else {
        alert("Erro ao criar guia: " + data.error);
      }
    } catch (err) {
      alert("Erro na requisição: " + err.message);
    }
  };

  // Salvar Guia Manual
  const handleSalvarManual = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_URL}/api/gnre/salvar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(novaGuia)
      });
      const data = await res.json();
      if (data.success) {
        alert("Guia manual criada com sucesso!");
        setModalNovaGuia(false);
        fetchGuias();
        // Limpa
        setNovaGuia({
          uf_favorecida: 'PE',
          cnpj_emitente: '10436619000105',
          codigo_receita: '100102',
          valor: '',
          data_vencimento: '',
          documento_origem: '',
          tipo_documento_origem: '10',
          chave_acesso_nfe: ''
        });
      } else {
        alert("Erro ao criar guia: " + data.error);
      }
    } catch (err) {
      alert("Erro na requisição: " + err.message);
    }
  };

  // Baixa de arquivo CNAB
  const downloadCnabFile = () => {
    const element = document.createElement("a");
    const file = new Blob([cnabContent], {type: 'text/plain'});
    element.href = URL.createObjectURL(file);
    element.download = cnabFilename;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  // Helpers de Métricas
  const totalGuias = guias.length;
  const guiasSucesso = guias.filter(g => g.status === 'SUCESSO').length;
  const guiasPendentes = guias.filter(g => g.status === 'PENDENTE').length;
  const valorTotalAcumulado = guias
    .filter(g => g.status === 'SUCESSO' || g.status === 'PAGO')
    .reduce((sum, g) => sum + Number(g.valor || 0), 0);

  const toggleSelectGuia = (id) => {
    if (selectedGuiaIds.includes(id)) {
      setSelectedGuiaIds(selectedGuiaIds.filter(x => x !== id));
    } else {
      setSelectedGuiaIds([...selectedGuiaIds, id]);
    }
  };

  const toggleSelectAll = () => {
    if (selectedGuiaIds.length === guias.length) {
      setSelectedGuiaIds([]);
    } else {
      setSelectedGuiaIds(guias.map(g => g.numero_tx));
    }
  };

  return (
    <div className="gnre-container">
      
      {/* SUMMARY DASHBOARD METRICS */}
      <div className="gnre-metrics">
        <div className="metric-card">
          <span className="metric-label">Total de Guias</span>
          <span className="metric-value">{totalGuias}</span>
        </div>
        <div className="metric-card success">
          <span className="metric-label">Validadas com Sucesso</span>
          <span className="metric-value">{guiasSucesso}</span>
        </div>
        <div className="metric-card warning">
          <span className="metric-label">Aguardando Transmissão</span>
          <span className="metric-value">{guiasPendentes}</span>
        </div>
        <div className="metric-card value">
          <span className="metric-label">Total Validado</span>
          <span className="metric-value">
            {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(valorTotalAcumulado)}
          </span>
        </div>
      </div>

      {/* SETTINGS AND ACTIONS BAR */}
      <div className="gnre-actions-bar">
        <div className="search-box">
          <Search size={18} />
          <input 
            type="text" 
            placeholder="Buscar por doc. origem, CNPJ ou TX..." 
            value={busca} 
            onChange={e => setBusca(e.target.value)} 
          />
        </div>

        <div className="gnre-settings-panel">
          <div className="setting-item">
            <Building size={16} />
            <select value={empresa} onChange={e => setEmpresa(e.target.value)}>
              <option value="LALUA">Lalua Matriz</option>
              <option value="SOLAR">Solar Matriz</option>
            </select>
          </div>
          
          <div className="setting-item">
            <Settings size={16} />
            <select value={ambiente} onChange={e => setAmbiente(Number(e.target.value))}>
              <option value={2}>Homologação</option>
              <option value={1}>Produção</option>
            </select>
          </div>

          <div className="setting-item toggle">
            <label className="switch">
              <input 
                type="checkbox" 
                checked={simulado} 
                onChange={e => setSimulado(e.target.checked)} 
              />
              <span className="slider round"></span>
            </label>
            <span className="toggle-label">Modo Simulação</span>
          </div>

          <button className="btn-primary" onClick={() => setModalNovaGuia(true)}>
            <Plus size={16} />
            Nova Guia
          </button>
        </div>
      </div>

      {/* TABS CONTAINER */}
      <div className="gnre-tabs-container">
        <div className="tab-buttons">
          <button 
            className={`tab-btn ${activeSubTab === 'guias' ? 'active' : ''}`}
            onClick={() => setActiveSubTab('guias')}
          >
            <FileText size={16} />
            Fila de Guias
          </button>
          <button 
            className={`tab-btn ${activeSubTab === 'difal' ? 'active' : ''}`}
            onClick={() => setActiveSubTab('difal')}
          >
            <FileCheck size={16} />
            Lançamentos DIFAL Pendentes
          </button>
        </div>

        {/* TAB 1: FILA DE GUIAS */}
        {activeSubTab === 'guias' && (
          <div className="tab-pane">
            <div className="pane-header-actions">
              <span className="selected-count">
                {selectedGuiaIds.length} guias selecionadas
              </span>
              
              <div className="action-buttons">
                <button 
                  className="btn-action transmit" 
                  disabled={selectedGuiaIds.length === 0 || transmitindo}
                  onClick={handleTransmitir}
                >
                  {transmitindo ? <Loader2 className="spinner" size={16} /> : <Send size={16} />}
                  Transmitir SEFAZ
                </button>

                <button 
                  className="btn-action cnab" 
                  disabled={selectedGuiaIds.length === 0 || gerandoCnab}
                  onClick={handleGerarSispag}
                >
                  {gerandoCnab ? <Loader2 className="spinner" size={16} /> : <Download size={16} />}
                  Gerar SISPAG (CNAB)
                </button>

                <button className="btn-action refresh" onClick={fetchGuias}>
                  <RefreshCw size={16} />
                </button>
              </div>
            </div>

            {loadingGuias ? (
              <div className="loading-state">
                <Loader2 className="spinner" size={32} />
                <span>Carregando guias GNRE...</span>
              </div>
            ) : guias.length === 0 ? (
              <div className="empty-state">
                <FileText size={48} />
                <span>Nenhuma guia GNRE encontrada.</span>
              </div>
            ) : (
              <table className="gnre-table">
                <thead>
                  <tr>
                    <th style={{ width: '40px' }}>
                      <input 
                        type="checkbox" 
                        checked={selectedGuiaIds.length === guias.length && guias.length > 0} 
                        onChange={toggleSelectAll} 
                      />
                    </th>
                    <th>Doc Origem</th>
                    <th>Favorecido</th>
                    <th>Receita</th>
                    <th>Valor</th>
                    <th>Vencimento</th>
                    <th>Status</th>
                    <th>Recibo / Detalhes</th>
                    <th style={{ textAlign: 'center' }}>Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {guias.map((guia) => (
                    <tr key={guia.numero_tx} className={`status-${guia.status.toLowerCase()}`}>
                      <td>
                        <input 
                          type="checkbox" 
                          checked={selectedGuiaIds.includes(guia.numero_tx)} 
                          onChange={() => toggleSelectGuia(guia.numero_tx)} 
                        />
                      </td>
                      <td>
                        <span className="doc-id" title={guia.numero_tx}>
                          {guia.documento_origem || guia.numero_tx}
                        </span>
                      </td>
                      <td><span className="uf-badge">{guia.uf_favorecida}</span></td>
                      <td>{guia.codigo_receita}</td>
                      <td className="valor-col">
                        {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(guia.valor)}
                      </td>
                      <td>{guia.data_vencimento ? guia.data_vencimento.split('-').reverse().join('/') : ''}</td>
                      <td>
                        <span className={`status-badge ${guia.status.toLowerCase()}`}>
                          {guia.status}
                        </span>
                      </td>
                      <td>
                        <div className="recibo-details">
                          {guia.numero_recibo ? (
                            <span className="recibo-code">Recibo: {guia.numero_recibo}</span>
                          ) : (
                            <span className="text-muted">Aguardando lote</span>
                          )}
                          {guia.motivo_rejeicao && (
                            <span className="rejeicao-text" title={guia.motivo_rejeicao}>
                              {guia.motivo_rejeicao}
                            </span>
                          )}
                        </div>
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        {guia.status === 'TRANSMITIDO' && (
                          <button 
                            className="btn-row-action" 
                            title="Consultar Resultado SEFAZ"
                            onClick={() => handleConsultarRecibo(guia.numero_recibo)}
                          >
                            <RefreshCw size={14} />
                            Consultar
                          </button>
                        )}
                        {guia.status === 'SUCESSO' && (
                          <span className="checked-indicator" title="Pronta para pagamento">
                            <CheckCircle2 size={16} />
                          </span>
                        )}
                        {guia.status === 'PAGO' && (
                          <span className="paid-indicator" title="Remessa CNAB gerada">
                            CNAB Ok
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* TAB 2: LANÇAMENTOS DIFAL PENDENTES */}
        {activeSubTab === 'difal' && (
          <div className="tab-pane">
            <div className="pane-header-actions">
              <span>Importe notas fiscais lançadas no ERP que possuem ICMS DIFAL calculado.</span>
              <button className="btn-action refresh" onClick={fetchNotasDifal}>
                <RefreshCw size={16} />
              </button>
            </div>

            {loadingNotas ? (
              <div className="loading-state">
                <Loader2 className="spinner" size={32} />
                <span>Buscando lançamentos...</span>
              </div>
            ) : notasDifal.length === 0 ? (
              <div className="empty-state">
                <FileCheck size={48} />
                <span>Nenhuma nota pendente com DIFAL localizada no sistema.</span>
              </div>
            ) : (
              <table className="gnre-table">
                <thead>
                  <tr>
                    <th>NF / ID Lançamento</th>
                    <th>Fornecedor</th>
                    <th>Empresa</th>
                    <th>Vencimento</th>
                    <th>Valor Nota</th>
                    <th>DIFAL Calculado</th>
                    <th style={{ textAlign: 'center' }}>Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {notasDifal.map((nota) => (
                    <tr key={nota.numero_tx}>
                      <td>
                        <strong>NF {nota.numero_nf || 'LOTE'}</strong>
                        <div className="tx-ref">{nota.numero_tx}</div>
                      </td>
                      <td>{nota.fornecedor}</td>
                      <td>{nota.empresa}</td>
                      <td>{nota.dt_vencimento}</td>
                      <td>
                        {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(nota.valor_bruto)}
                      </td>
                      <td className="difal-valor">
                        {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(nota.valor_difal)}
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <button 
                          className="btn-import-row"
                          onClick={() => handleImportarNotaDifal(nota)}
                        >
                          <Plus size={14} />
                          Gerar Guia GNRE
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>

      {/* MODAL: NOVA GUIA MANUAL */}
      {modalNovaGuia && (
        <div className="gnre-modal-overlay">
          <div className="gnre-modal">
            <div className="modal-header">
              <h3>Cadastrar Guia GNRE Manual</h3>
              <button className="close-btn" onClick={() => setModalNovaGuia(false)}>&times;</button>
            </div>
            <form onSubmit={handleSalvarManual}>
              <div className="form-grid">
                <div className="form-group">
                  <label>UF Favorecida (Destino)</label>
                  <input 
                    type="text" 
                    maxLength={2} 
                    value={novaGuia.uf_favorecida} 
                    onChange={e => setNovaGuia({...novaGuia, uf_favorecida: e.target.value.toUpperCase()})}
                    required 
                  />
                </div>

                <div className="form-group">
                  <label>CNPJ Emitente</label>
                  <input 
                    type="text" 
                    value={novaGuia.cnpj_emitente} 
                    onChange={e => setNovaGuia({...novaGuia, cnpj_emitente: e.target.value})}
                    required 
                  />
                </div>

                <div className="form-group">
                  <label>Código Receita</label>
                  <input 
                    type="text" 
                    value={novaGuia.codigo_receita} 
                    onChange={e => setNovaGuia({...novaGuia, codigo_receita: e.target.value})}
                    required 
                  />
                </div>

                <div className="form-group">
                  <label>Valor da Guia (R$)</label>
                  <input 
                    type="number" 
                    step="0.01" 
                    value={novaGuia.valor} 
                    onChange={e => setNovaGuia({...novaGuia, valor: e.target.value})}
                    required 
                  />
                </div>

                <div className="form-group">
                  <label>Data de Vencimento</label>
                  <input 
                    type="date" 
                    value={novaGuia.data_vencimento} 
                    onChange={e => setNovaGuia({...novaGuia, data_vencimento: e.target.value})}
                    required 
                  />
                </div>

                <div className="form-group">
                  <label>Documento de Origem (Nº Nota)</label>
                  <input 
                    type="text" 
                    value={novaGuia.documento_origem} 
                    onChange={e => setNovaGuia({...novaGuia, documento_origem: e.target.value})}
                  />
                </div>

                <div className="form-group full-width">
                  <label>Chave de Acesso NF-e (44 dígitos)</label>
                  <input 
                    type="text" 
                    maxLength={44}
                    value={novaGuia.chave_acesso_nfe} 
                    onChange={e => setNovaGuia({...novaGuia, chave_acesso_nfe: e.target.value})}
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn-secondary" onClick={() => setModalNovaGuia(false)}>Cancelar</button>
                <button type="submit" className="btn-primary">Salvar Guia</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: DOWNLOAD CNAB REMESSA */}
      {modalCnab && (
        <div className="gnre-modal-overlay">
          <div className="gnre-modal cnab-modal">
            <div className="modal-header">
              <h3>Arquivo Remessa SISPAG Gerado com Sucesso!</h3>
              <button className="close-btn" onClick={() => setModalCnab(false)}>&times;</button>
            </div>
            <div className="cnab-info-box">
              <CheckCircle2 size={32} className="success-icon" />
              <div>
                <strong>Arquivo: {cnabFilename}</strong>
                <p>O arquivo CNAB 240 (Segmento O) foi salvo com sucesso na pasta de saídas do sistema.</p>
              </div>
            </div>
            
            <textarea 
              className="cnab-preview" 
              readOnly 
              value={cnabContent}
            />

            <div className="modal-footer">
              <button type="button" className="btn-secondary" onClick={() => setModalCnab(false)}>Fechar</button>
              <button type="button" className="btn-primary" onClick={downloadCnabFile}>
                <Download size={16} />
                Baixar Arquivo
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
