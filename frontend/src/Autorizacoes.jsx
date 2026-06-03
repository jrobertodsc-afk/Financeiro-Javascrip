import { useState, useEffect } from 'react';
import { UploadCloud, FileText, CheckCircle2, AlertCircle, History, Download, Edit3, LayoutTemplate } from 'lucide-react';
import './Autorizacoes.css';
import RelatorioModerno from './RelatorioModerno';

const CATEGORIAS_PADRAO = [
  "12101 - Tecidos", "12102 - Aviamentos", "12104 - Produtos Para Revenda",
  "12111 - Faccionista - Mão de Obra", "12201 - Salários", "12203 - Transportes",
  "12204 - Alimentação", "12205 - FGTS", "12208 - Domingos e Feriados Trabalhados",
  "21101 - Aluguel", "21104 - Energia Eletrica", "21111 - Serviços Advocatícios",
  "21120 - Sistemas e Softwares", "21206 - Material de Limpeza", "21209 - Uso e Consumo Lojas",
  "21502 - Manutenção - Elétrica", "21701 - Comunicação/Mídia Digital", 
  "21703 - Lookbook", "21704 - Marketing de Influência - Influencers",
  "21705 - Relacionamento com o Cliente", "21901 - IPTU",
  "22303 - ICMS Antecipação Parcial", "22304 - PIS (8109)", "22308 - Simples Nacional",
  "22309 - GNRE", "TRANSFERENCIA", "A CLASSIFICAR"
];

const RESPONSAVEIS_PADRAO = [
  "ADM/FINANCEIRO", "COMPRAS", "GERENTE ONLINE", "LOGISTICA",
  "MARKETING", "PRODUCAO", "RH", "SUPRIMENTOS"
];

export default function Autorizacoes() {
  const [pagamentos, setPagamentos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('importacao');
  const [historico, setHistorico] = useState([]);
  
  const [showRelatorioModerno, setShowRelatorioModerno] = useState(false);
  const [saldos, setSaldos] = useState({ 'Itaú': '', 'Bradesco': '', 'Banco do Brasil': '' });

  useEffect(() => {
    if (activeTab === 'historico') {
      fetchHistorico();
    }
  }, [activeTab]);

  const fetchHistorico = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/historico_autorizacoes");
      const data = await res.json();
      setHistorico(data.arquivos || []);
    } catch (err) {
      console.error(err);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setLoading(true);
    setError(null);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("http://localhost:8000/api/importar_itau", {
        method: "POST",
        body: formData,
      });
      if (!response.ok) throw new Error("Falha ao processar arquivo");
      const data = await response.json();
      setPagamentos(data.pagamentos || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFieldChange = (index, field, value) => {
    const newPagamentos = [...pagamentos];
    newPagamentos[index][field] = value;
    newPagamentos[index].modificado = true; // Marca que o usuário editou
    setPagamentos(newPagamentos);
  };

  const treinarCategorias = async () => {
    // Treina apenas as que foram modificadas pelo usuário
    const modificados = pagamentos.filter(p => p.modificado);
    for (const p of modificados) {
      try {
        await fetch("http://localhost:8000/api/treinar_categorizacao", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            cnpj: p.cnpj || "00.000.000/0000-00",
            nome: p.favorecido || p.nome || "",
            responsavel: p.responsavel,
            categoria: p.categoria,
            descricao: p.descricao || ""
          })
        });
      } catch (e) {
        console.error("Erro ao treinar", e);
      }
    }
  };

  const handleGerarPdf = async () => {
    if (pagamentos.length === 0) return;
    
    setLoading(true);
    try {
      // 1. Treina a base com as edições do usuário
      await treinarCategorias();

      // 2. Gera o PDF
      const response = await fetch("http://localhost:8000/api/gerar_pdf_autorizacao", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pagamentos })
      });
      
      if (!response.ok) throw new Error("Erro ao gerar PDF");
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      
      let filename = "AUTORIZACAO_PAGAMENTOS.pdf";
      const disposition = response.headers.get("Content-Disposition");
      if (disposition && disposition.indexOf('filename=') !== -1) {
          filename = disposition.split('filename=')[1].replace(/"/g, '');
      }
      a.download = filename;
      
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleGerarModerno = async () => {
    // 1. Treina a base com as edições do usuário
    await treinarCategorias();

    // 2. Salva o snapshot no backend para o histórico
    try {
      await fetch("http://localhost:8000/api/salvar_historico_moderno", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pagamentos, saldos })
      });
    } catch (e) {
      console.error("Erro ao salvar histórico moderno", e);
    }

    // 3. Abre a visualização
    setShowRelatorioModerno(true);
  };

  const downloadHistorico = async (filename) => {
    if (filename.endsWith('.json')) {
      // É um snapshot moderno, então vamos visualizar
      try {
        const res = await fetch(`http://localhost:8000/api/download_autorizacao/${filename}`);
        const data = await res.json();
        if (data.pagamentos) {
          setPagamentos(data.pagamentos);
          setSaldos(data.saldos || { 'Itaú': '', 'Bradesco': '', 'Banco do Brasil': '' });
          setShowRelatorioModerno(true);
        }
      } catch (err) {
        setError("Erro ao abrir histórico moderno.");
      }
    } else {
      window.open(`http://localhost:8000/api/download_autorizacao/${filename}`, '_blank');
    }
  };

  const valorTotal = pagamentos.reduce((acc, p) => acc + (p.valor || 0), 0);

  if (showRelatorioModerno) {
    return <RelatorioModerno pagamentos={pagamentos} saldos={saldos} onClose={() => setShowRelatorioModerno(false)} />;
  }

  return (
    <div className="autorizacoes-container fade-in">
      <datalist id="datalist-categorias">
        {CATEGORIAS_PADRAO.map(c => <option key={c} value={c} />)}
      </datalist>
      <datalist id="datalist-responsaveis">
        {RESPONSAVEIS_PADRAO.map(r => <option key={r} value={r} />)}
      </datalist>

      <div className="aut-header">
        <div>
          <h2>Autorizações de Pagamento</h2>
          <p>Importe o extrato, ajuste as categorias (que o sistema aprenderá) e gere o PDF.</p>
        </div>
        
        <div className="aut-tabs">
          <button 
            className={`aut-tab-btn ${activeTab === 'importacao' ? 'active' : ''}`}
            onClick={() => setActiveTab('importacao')}
          >
            <UploadCloud size={18} />
            Importação
          </button>
          <button 
            className={`aut-tab-btn ${activeTab === 'historico' ? 'active' : ''}`}
            onClick={() => setActiveTab('historico')}
          >
            <History size={18} />
            Histórico
          </button>
        </div>
      </div>

      {error && (
        <div className="aut-error">
          <AlertCircle size={20} />
          {error}
        </div>
      )}

      {activeTab === 'importacao' && (
        <>
          {pagamentos.length === 0 ? (
            <div className="upload-zone">
              <input 
                type="file" 
                id="file-upload" 
                accept=".xls,.xlsx" 
                onChange={handleFileUpload} 
              />
              <label htmlFor="file-upload" className={loading ? "disabled" : ""}>
                <UploadCloud size={48} className="upload-icon" />
                <h3>Clique ou arraste o XLS do Itaú</h3>
                <p>O sistema lembrará de todas as edições feitas na tabela para a próxima vez.</p>
                {loading && <div className="loading-bar">Processando...</div>}
              </label>
            </div>
          ) : (
            <div className="aut-content">
              <div className="posicao-caixa-panel">
                <h3>Posição de Caixa (Opcional para o Relatório)</h3>
                <div className="saldos-inputs">
                  {Object.keys(saldos).map(banco => (
                    <div key={banco} className="saldo-input-group">
                      <label>{banco}</label>
                      <input 
                        type="number" 
                        placeholder="R$ 0,00"
                        value={saldos[banco]}
                        onChange={(e) => setSaldos({...saldos, [banco]: e.target.value})}
                      />
                    </div>
                  ))}
                </div>
              </div>

              <div className="aut-summary">
                <div className="summary-card">
                  <span className="summary-title">Total de Registros</span>
                  <span className="summary-value">{pagamentos.length}</span>
                </div>
                <div className="summary-card highlight">
                  <span className="summary-title">Valor Total a Pagar</span>
                  <span className="summary-value">
                    {valorTotal.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                  </span>
                </div>
                <div className="summary-actions">
                  <button className="btn-limpar" onClick={() => setPagamentos([])}>
                    Nova Importação
                  </button>
                  <button className="btn-gerar-moderno" onClick={handleGerarModerno}>
                    <LayoutTemplate size={20} />
                    Relatório Moderno
                  </button>
                  <button className="btn-gerar-pdf" onClick={handleGerarPdf} disabled={loading}>
                    {loading ? <span className="spinner"></span> : <CheckCircle2 size={20} />}
                    Treinar e Gerar PDF
                  </button>
                </div>
              </div>

              <div className="aut-table-container">
                <table className="aut-table">
                  <thead>
                    <tr>
                      <th>Favorecido</th>
                      <th>CNPJ</th>
                      <th>Data</th>
                      <th>Categoria Sugerida</th>
                      <th>Responsável</th>
                      <th>Descrição</th>
                      <th className="col-valor">Valor</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pagamentos.map((p, i) => (
                      <tr key={i} className={p.modificado ? "tr-modificado" : ""}>
                        <td className="fw-500">{p.favorecido || p.nome}</td>
                        <td className="text-muted">{p.cnpj}</td>
                        <td>{p.data}</td>
                        <td>
                          <div className="editable-cell">
                            <input 
                              type="text" 
                              list="datalist-categorias"
                              value={p.categoria}
                              onChange={(e) => handleFieldChange(i, 'categoria', e.target.value)}
                              className="input-editable"
                            />
                            <Edit3 size={14} className="edit-icon" />
                          </div>
                        </td>
                        <td>
                          <div className="editable-cell">
                            <input 
                              type="text" 
                              list="datalist-responsaveis"
                              value={p.responsavel}
                              onChange={(e) => handleFieldChange(i, 'responsavel', e.target.value)}
                              className="input-editable"
                            />
                            <Edit3 size={14} className="edit-icon" />
                          </div>
                        </td>
                        <td>
                          <div className="editable-cell">
                            <input 
                              type="text" 
                              value={p.descricao || ""}
                              placeholder="Adicione notas..."
                              onChange={(e) => handleFieldChange(i, 'descricao', e.target.value)}
                              className="input-editable"
                            />
                            <Edit3 size={14} className="edit-icon" />
                          </div>
                        </td>
                        <td className="col-valor fw-600">
                          {(p.valor || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {activeTab === 'historico' && (
        <div className="historico-container">
          <h3>Relatórios Gerados Recentemente</h3>
          {historico.length === 0 ? (
            <p className="text-muted">Nenhum relatório encontrado no histórico.</p>
          ) : (
            <ul className="historico-list">
              {historico.map((arq, idx) => (
                <li key={idx} className="historico-item">
                  <div className="historico-info">
                    {arq.tipo === 'moderno' ? <LayoutTemplate size={24} className="historico-icon" /> : <FileText size={24} className="historico-icon" />}
                    <div>
                      <div className="historico-nome">{arq.nome}</div>
                      <div className="historico-data">
                        {new Date(arq.data * 1000).toLocaleString('pt-BR')} • {(arq.tamanho / 1024).toFixed(1)} KB
                      </div>
                    </div>
                  </div>
                  <button className="btn-download" onClick={() => downloadHistorico(arq.nome)}>
                    {arq.tipo === 'moderno' ? (
                      <><LayoutTemplate size={18} /> Visualizar Relatório</>
                    ) : (
                      <><Download size={18} /> Baixar PDF</>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
