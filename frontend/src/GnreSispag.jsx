import React, { useState, useEffect, useRef } from 'react';
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
  Building,
  Upload,
  Terminal as TerminalIcon,
  FileArchive,
  FileDown,
  Calendar,
  X,
  Trash2,
  CheckCircle
} from 'lucide-react';
import './GnreSispag.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function GnreSispag() {
  const [activeSubTab, setActiveSubTab] = useState('processamento'); // 'processamento' | 'guias' | 'difal'
  const [guias, setGuias] = useState([]);
  const [notasDifal, setNotasDifal] = useState([]);
  const [loadingGuias, setLoadingGuias] = useState(false);
  const [loadingNotas, setLoadingNotas] = useState(false);
  const [simulado, setSimulado] = useState(true);
  const [ambiente, setAmbiente] = useState(2); // 2 = Homologação, 1 = Produção
  const [empresa, setEmpresa] = useState('LALUA');
  const [busca, setBusca] = useState('');
  
  // Seleção múltipla para a aba de Fila de Guias
  const [selectedGuiaIds, setSelectedGuiaIds] = useState([]);

  // Estados do Novo Painel de Processamento
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [paymentDate, setPaymentDate] = useState('');
  const [logs, setLogs] = useState([]);
  const [progress, setProgress] = useState(0);
  const [processing, setProcessing] = useState(false);
  
  // Histórico de Lotes
  const [lotes, setLotes] = useState([]);
  const [selectedLote, setSelectedLote] = useState(null);
  const [loadingLotes, setLoadingLotes] = useState(false);
  const [buscaLotes, setBuscaLotes] = useState('');

  // Modais de suporte
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

  const [modalCnab, setModalCnab] = useState(false);
  const [cnabContent, setCnabContent] = useState('');
  const [cnabFilename, setCnabFilename] = useState('');

  const [transmitindo, setTransmitindo] = useState(false);
  const [consultando, setConsultando] = useState(false);
  const [gerandoCnab, setGerandoCnab] = useState(false);

  const terminalEndRef = useRef(null);

  // Auto-scroll do terminal de logs
  useEffect(() => {
    if (terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  // Carrega os dados iniciais
  useEffect(() => {
    fetchLotes();
    fetchGuias();
    fetchNotasDifal();
  }, []);

  useEffect(() => {
    fetchGuias();
  }, [busca]);

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

  const fetchLotes = async () => {
    setLoadingLotes(true);
    try {
      const res = await fetch(`${API_URL}/api/gnre/lotes`);
      const data = await res.json();
      if (data.success) {
        setLotes(data.lotes);
      }
    } catch (err) {
      console.error("Erro ao buscar lotes GNRE:", err);
    }
    setLoadingLotes(false);
  };

  const fetchLoteDetails = async (loteId) => {
    try {
      const res = await fetch(`${API_URL}/api/gnre/lotes/${loteId}`);
      const data = await res.json();
      if (data.success) {
        setSelectedLote(data.lote);
      }
    } catch (err) {
      console.error("Erro ao buscar detalhes do lote:", err);
    }
  };

  // Drag and Drop Handlers
  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files) {
      const filesArray = Array.from(e.dataTransfer.files).filter(f => f.name.toLowerCase().endsWith('.xml'));
      setSelectedFiles(prev => [...prev, ...filesArray]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files) {
      const filesArray = Array.from(e.target.files).filter(f => f.name.toLowerCase().endsWith('.xml'));
      setSelectedFiles(prev => [...prev, ...filesArray]);
    }
  };

  const handleRemoveFile = (index) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  // Processamento do Lote de XMLs (Streaming SSE)
  const handleProcessarLote = async (localOnly = false) => {
    if (!localOnly && selectedFiles.length === 0) {
      alert("Por favor, adicione pelo menos um arquivo XML.");
      return;
    }

    setProcessing(true);
    setLogs([]);
    setProgress(0);

    const formData = new FormData();
    if (!localOnly) {
      selectedFiles.forEach((file) => {
        formData.append("files", file);
      });
    }
    formData.append("payment_date", paymentDate);
    formData.append("simulado", simulado ? "true" : "false");
    formData.append("ambiente", String(ambiente));
    formData.append("empresa", empresa);
    formData.append("processar_pasta_local", localOnly ? "true" : "false");

    try {
      setLogs(prev => [...prev, "[SISTEMA] Iniciando fluxo de comunicação..."]);
      const response = await fetch(`${API_URL}/api/gnre/processar_lote_xmls`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error(`Erro na API (${response.status})`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop();

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const dataStr = line.slice(6).trim();
            if (!dataStr) continue;

            try {
              const data = JSON.parse(dataStr);
              if (data.status === "done") {
                setProcessing(false);
                fetchLotes();
                fetchGuias();
                if (data.success && data.lote_id) {
                  fetchLoteDetails(data.lote_id);
                }
              } else {
                if (data.progress !== undefined) {
                  setProgress(data.progress);
                }
                setLogs(prev => [...prev, data.message]);
              }
            } catch (err) {
              console.error("Erro ao fazer parse da linha do stream", err);
            }
          }
        }
      }
      setSelectedFiles([]);
    } catch (err) {
      setLogs(prev => [...prev, `[ERRO CRÍTICO] Falha no processamento: ${err.message}`]);
      setProcessing(false);
    }
  };

  // Downloads de arquivos do lote selecionado
  const handleDownloadZipLote = (loteId) => {
    window.open(`${API_URL}/api/gnre/lotes/${loteId}/zip`, '_blank');
  };

  const handleDownloadCnabLote = (loteId) => {
    window.open(`${API_URL}/api/gnre/lotes/${loteId}/cnab`, '_blank');
  };

  // Funções da Aba Fila de Guias (Originais)
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

  const handleGerarSispag = async () => {
    if (selectedGuiaIds.length === 0) return;
    
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
            cnpj: empresa === 'LALUA' ? '10436619000105' : '12345678000199',
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

  const handleImportarNotaDifal = async (nota) => {
    try {
      const valor_difal = Number(nota.valor_difal || 0);
      if (valor_difal <= 0) return;

      const formatarData = (dataStr) => {
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
          uf_favorecida: nota.filial?.includes("PE") || nota.observacao?.includes("PE") ? "PE" : "PE",
          cnpj_emitente: '10436619000105',
          codigo_receita: '100102',
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

  const downloadCnabFile = () => {
    const element = document.createElement("a");
    const file = new Blob([cnabContent], {type: 'text/plain'});
    element.href = URL.createObjectURL(file);
    element.download = cnabFilename;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  // Métricas Globais
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

  // Filtragem de Lotes
  const lotesFiltrados = lotes.filter(l => 
    l.lote_id.toLowerCase().includes(buscaLotes.toLowerCase()) ||
    l.ambiente.toLowerCase().includes(buscaLotes.toLowerCase()) ||
    l.status.toLowerCase().includes(buscaLotes.toLowerCase())
  );

  return (
    <div className="gnre-container">
      
      {/* SUMMARY DASHBOARD METRICS */}
      <div className="gnre-metrics">
        <div className="metric-card">
          <span className="metric-label">Lotes Processados</span>
          <span className="metric-value">{lotes.length}</span>
        </div>
        <div className="metric-card success">
          <span className="metric-label">Guias Validadas</span>
          <span className="metric-value">{guiasSucesso}</span>
        </div>
        <div className="metric-card warning">
          <span className="metric-label">Pendentes de Envio</span>
          <span className="metric-value">{guiasPendentes}</span>
        </div>
        <div className="metric-card value">
          <span className="metric-label">Total Validado</span>
          <span className="metric-value">
            {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(valorTotalAcumulado)}
          </span>
        </div>
      </div>

      {/* TOP ACTIONS BAR */}
      <div className="gnre-actions-bar">
        <div className="search-box">
          <Search size={18} />
          <input 
            type="text" 
            placeholder="Buscar guias, CNPJ ou TX..." 
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
            Nova Guia Manual
          </button>
        </div>
      </div>

      {/* TABS CONTAINER */}
      <div className="gnre-tabs-container">
        <div className="tab-buttons">
          <button 
            className={`tab-btn ${activeSubTab === 'processamento' ? 'active' : ''}`}
            onClick={() => setActiveSubTab('processamento')}
          >
            <TerminalIcon size={16} />
            Painel de Lotes (Lote XML)
          </button>
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
            DIFAL Pendente
          </button>
        </div>

        {/* TAB 1: PAINEL DE PROCESSAMENTO EM LOTE */}
        {activeSubTab === 'processamento' && (
          <div className="tab-pane">
            <div className="batch-layout">
              {/* LEFT COLUMN: CONTROL & LOGGER */}
              <div className="batch-control-panel">
                <div className="panel-title">
                  <h4>Configuração e Execução de Lote</h4>
                </div>

                {/* Drag and Drop Zone */}
                <div 
                  className="drag-drop-zone"
                  onDragOver={handleDragOver}
                  onDrop={handleDrop}
                >
                  <Upload size={36} className="upload-icon" />
                  <p className="primary-text">Arraste e solte seus XMLs de NFe aqui</p>
                  <p className="secondary-text">ou clique para selecionar arquivos do seu computador</p>
                  <input 
                    type="file" 
                    multiple 
                    accept=".xml" 
                    onChange={handleFileChange} 
                    id="file-upload-input"
                    style={{ display: 'none' }}
                  />
                  <label htmlFor="file-upload-input" className="btn-browse">Selecionar Arquivos</label>
                </div>

                {/* Selected Files List */}
                {selectedFiles.length > 0 && (
                  <div className="selected-files-container">
                    <h5>Arquivos Selecionados ({selectedFiles.length})</h5>
                    <div className="file-chips-grid">
                      {selectedFiles.map((file, idx) => (
                        <div key={idx} className="file-chip">
                          <span className="file-name" title={file.name}>{file.name}</span>
                          <button onClick={() => handleRemoveFile(idx)} className="btn-remove-chip">
                            <X size={12} />
                          </button>
                        </div>
                      ))}
                    </div>
                    <button onClick={() => setSelectedFiles([])} className="btn-clear-files">
                      <Trash2 size={12} /> Limpar Todos
                    </button>
                  </div>
                )}

                {/* Datepicker and Action Buttons */}
                <div className="execution-settings-row">
                  <div className="form-group inline">
                    <label><Calendar size={14} /> Data de Pagamento</label>
                    <input 
                      type="date" 
                      value={paymentDate} 
                      onChange={e => setPaymentDate(e.target.value)} 
                    />
                  </div>

                  <div className="action-buttons-group">
                    <button 
                      className="btn-execute-batch" 
                      onClick={() => handleProcessarLote(false)}
                      disabled={selectedFiles.length === 0 || processing}
                    >
                      {processing ? <Loader2 className="spinner" size={16} /> : <Send size={16} />}
                      Processar XMLs Selecionados
                    </button>
                    <button 
                      className="btn-execute-local"
                      onClick={() => handleProcessarLote(true)}
                      disabled={processing}
                    >
                      {processing ? <Loader2 className="spinner" size={16} /> : <FolderIcon />}
                      Processar Pasta Local (xml_nfe)
                    </button>
                  </div>
                </div>

                {/* Logging Terminal */}
                <div className="terminal-container">
                  <div className="terminal-header">
                    <div className="terminal-buttons">
                      <span className="dot red"></span>
                      <span className="dot yellow"></span>
                      <span className="dot green"></span>
                    </div>
                    <span className="terminal-title">console_gnre_sefaz.sh</span>
                    <button onClick={() => setLogs([])} className="btn-clear-terminal">Limpar Console</button>
                  </div>
                  
                  {/* Progress Bar */}
                  {processing && (
                    <div className="progress-bar-wrapper">
                      <div className="progress-bar-fill" style={{ width: `${progress}%` }}></div>
                      <span className="progress-percentage">{progress}%</span>
                    </div>
                  )}

                  <div className="terminal-body">
                    {logs.length === 0 ? (
                      <span className="terminal-empty-text">Aguardando execução de lote...</span>
                    ) : (
                      logs.map((log, i) => {
                        let colorClass = "";
                        if (log.includes("[ERRO]") || log.includes("REJEITADA") || log.includes("critico")) colorClass = "log-error";
                        else if (log.includes("[AVISO]")) colorClass = "log-warning";
                        else if (log.includes("SUCESSO") || log.includes("sucesso")) colorClass = "log-success";
                        return (
                          <div key={i} className={`terminal-line ${colorClass}`}>
                            {log}
                          </div>
                        );
                      })
                    )}
                    <div ref={terminalEndRef} />
                  </div>
                </div>
              </div>

              {/* RIGHT COLUMN: HISTORY & DETAILS */}
              <div className="batch-history-panel">
                <div className="panel-title flex-between">
                  <h4>Histórico de Lotes Enviados</h4>
                  <div className="search-box-small">
                    <Search size={14} />
                    <input 
                      type="text" 
                      placeholder="Buscar lote..." 
                      value={buscaLotes}
                      onChange={e => setBuscaLotes(e.target.value)}
                    />
                  </div>
                </div>

                {loadingLotes ? (
                  <div className="loading-state-small">
                    <Loader2 className="spinner" size={20} />
                    <span>Carregando histórico...</span>
                  </div>
                ) : lotesFiltrados.length === 0 ? (
                  <div className="empty-state-small">
                    <span>Nenhum lote enviado encontrado.</span>
                  </div>
                ) : (
                  <div className="lotes-list-container">
                    <table className="lotes-table">
                      <thead>
                        <tr>
                          <th>Lote ID</th>
                          <th>Data/Hora</th>
                          <th>Ambiente</th>
                          <th>Status</th>
                          <th style={{ textAlign: 'center' }}>Ação</th>
                        </tr>
                      </thead>
                      <tbody>
                        {lotesFiltrados.map((l) => (
                          <tr 
                            key={l.lote_id} 
                            onClick={() => fetchLoteDetails(l.lote_id)}
                            className={`lote-row ${selectedLote?.lote_id === l.lote_id ? 'active' : ''}`}
                          >
                            <td><strong>{l.lote_id}</strong></td>
                            <td>{l.data_hora}</td>
                            <td>
                              <span className={`env-badge ${l.ambiente}`}>
                                {l.ambiente}
                              </span>
                            </td>
                            <td>
                              <span className={`status-badge ${l.status.toLowerCase()}`}>
                                {l.status}
                              </span>
                            </td>
                            <td style={{ textAlign: 'center' }}>
                              <button className="btn-ver-lote">Ver Detalhes</button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Selected Lote Details */}
                {selectedLote && (
                  <div className="lote-details-card animate-slide-up">
                    <div className="details-header">
                      <h5>Detalhes do Lote: <span>{selectedLote.lote_id}</span></h5>
                      <span className="details-time">{selectedLote.data_hora}</span>
                    </div>

                    <div className="details-meta-grid">
                      <div>
                        <strong>Ambiente:</strong> {selectedLote.ambiente}
                      </div>
                      <div>
                        <strong>Status:</strong> {selectedLote.status}
                      </div>
                      <div>
                        <strong>Recibo Geral:</strong> {selectedLote.recibos || 'Não gerado'}
                      </div>
                    </div>

                    {/* Download buttons */}
                    {selectedLote.status === 'Sucesso' && (
                      <div className="details-action-buttons">
                        <button 
                          className="btn-details-download zip"
                          onClick={() => handleDownloadZipLote(selectedLote.lote_id)}
                        >
                          <FileArchive size={14} /> Download ZIP das Guias
                        </button>
                        <button 
                          className="btn-details-download cnab"
                          onClick={() => handleDownloadCnabLote(selectedLote.lote_id)}
                        >
                          <FileDown size={14} /> Download Remessa SISPAG
                        </button>
                      </div>
                    )}

                    {/* Guides in Lote List */}
                    <div className="lote-guias-list">
                      <h6>Guias Geradas no Lote</h6>
                      <table className="lote-guias-table">
                        <thead>
                          <tr>
                            <th>NF</th>
                            <th>Emitente</th>
                            <th>UF</th>
                            <th>Valor</th>
                            <th>Status</th>
                            <th>Guia PDF</th>
                          </tr>
                        </thead>
                        <tbody>
                          {JSON.parse(selectedLote.xml_guias || "[]").map((g, idx) => (
                            <tr key={idx}>
                              <td>NF {g.documento_origem}</td>
                              <td>{g.cnpj_emitente}</td>
                              <td><span className="uf-badge">{g.uf_favorecida}</span></td>
                              <td>{new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(g.valor)}</td>
                              <td>
                                <span className={`status-badge-small ${g.status.toLowerCase()}`}>
                                  {g.status}
                                </span>
                              </td>
                              <td>
                                {g.status === 'SUCESSO' && (
                                  <button 
                                    className="btn-row-pdf"
                                    onClick={() => {
                                      window.open(`${API_URL}/api/gnre/pdf/${g.nota_ref_tx}`, '_blank');
                                    }}
                                  >
                                    PDF
                                  </button>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: FILA DE GUIAS (MANUAIS / INDIVIDUAIS) */}
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
                        {(guia.status === 'SUCESSO' || guia.status === 'PAGO') && (
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                            {guia.status === 'SUCESSO' ? (
                              <span className="checked-indicator" title="Pronta para pagamento">
                                <CheckCircle2 size={16} />
                              </span>
                            ) : (
                              <span className="paid-indicator" title="Remessa CNAB gerada">
                                CNAB Ok
                              </span>
                            )}
                            <button 
                              className="btn-row-action pdf" 
                              title="Download da Guia em PDF"
                              onClick={() => {
                                window.open(`${API_URL}/api/gnre/pdf/${guia.numero_tx}`, '_blank');
                              }}
                            >
                              PDF
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* TAB 3: LANÇAMENTOS DIFAL PENDENTES */}
        {activeSubTab === 'difal' && (
          <div className="tab-pane">
            <div className="pane-header-actions">
              <span>Importe notas fiscais lançadas no ERP que possuem ICMS DIFAL calculated.</span>
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

function FolderIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2z"></path>
    </svg>
  );
}
