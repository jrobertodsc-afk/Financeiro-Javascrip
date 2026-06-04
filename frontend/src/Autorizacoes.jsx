import { useState, useEffect } from 'react';
import { UploadCloud, FileText, CheckCircle2, AlertCircle, History, Download, Edit3, LayoutTemplate, Save, X } from 'lucide-react';
import './Autorizacoes.css';
import RelatorioModerno from './RelatorioModerno';

const CATEGORIAS_PADRAO = [
  "111 - Custo Fixo - Desenvolvimento de Produto (Estilo)", "112 - Custo Fixo - Produção/Atelier",
  "21101 - Aluguel", "21102 - Condomínio", "21103 - Água E Esgoto", "21104 - Energia Elétrica",
  "21105 - Ar Condicionado", "21106 - Fundo de Promoção/Reserva", "21107 - Reembolso de Despesas Operacionais (Transporte, Alimentação Etc)",
  "21108 - Sindicato E Associacoes", "21109 - Seguros Loja/Imovel", "21110 - Gráficos Em Geral",
  "21111 - Serviços Advocatícios", "21112 - Serviços Contábeis", "21113 - Consultorias e Auditorias",
  "21114 - Telefonia Fixa/Internet", "21115 - Telefonia Móvel", "21117 - Seguro Geral",
  "21118 - Correios, Cartórios E Periódicos", "21119 - Consulta SPC / Serasa", "21120 - Sistemas e Softwares",
  "21121 - Domínios, Email e Site", "21201 - Copa e Cozinha", "21202 - Dedetização",
  "21203 - Recarga de Extintores", "21204 - Material de Escritório", "21205 - Material de Informática (Recargas e Tonners)",
  "21206 - Material de Limpeza", "21207 - Despesas com EPI", "21208 - Prestações de Serviços Operacionais",
  "21209 - Uso e Consumo Lojas (Copos, Comandas Etc)", "21301 - Combustível e Motoboy", "21302 - Estacionamento/Pedágio",
  "21303 - Licenciamento e Multas/IPVA Moto/Carro", "21304 - Manutenção - Moto/Carro", "21305 - Seguros - Moto/Carro",
  "21306 - Táxi/Uber (100030*2 por mês)", "12202 - Salários - Meis/PJ", "21401 - Salários", "21402 - Salários - Sócio/PJ",
  "21403 - Pró-labore", "21404 - Transportes", "21405 - Alimentação", "21406 - FGTS",
  "21407 - INSS", "21408 - IRRF - Imposto de Renda PJ (Verificar %)", "21409 - Férias",
  "21410 - Rescisão", "21411 - Multa de FGTS", "21412 - Domingos e Feriados Trabalhados",
  "21413 - Cursos e Treinamentos", "21414 - Exames Clínicos (Dem/Adm/Ret)", "21415 - Despesas com Estágio",
  "21416 - 13º salário", "21417 - Sindicatos", "21418 - Faltas", "21419 - Fardamento",
  "21420 - ISS Substituto Tributario", "21501 - Manutenção - Predial", "21502 - Manutenção - Elétrica",
  "21503 - Manutenção - Informática", "21504 - Manutenção - Máquinas e Equipamentos", "21505 - Manutenção - Refrigeração/Ar-condicionado",
  "21506 - Manutenção - Mobiliário/Decoração", "21601 - Tarifas Bancárias", "21602 - Aluguel de Maquinetas",
  "21603 - Taxa de Juros Cartões/Pix/Boletos", "21701 - Comunicação/Mídia Digital - Despesas Operacionais (Facebook/Insta...)", "21702 - Relacionamento com o Cliente - Ações (Distribuição de Mimos/Sorteios/Etc)",
  "21703 - Marketing de Influência - Blogueiras/Influencers (Tons/Permutas)", "21704 - Lookbook (1 Por Ano)", "21705 - Editorial para Campanha (4 Por Ano)",
  "21706 - Visual Merchandising - Decoração, Ambientação, Vitrines", "21707 - Material Gráfico", "21801 - Endomarketing",
  "21901 - IPTU", "21902 - Taxas Municipais", "21903 - Taxas Estaduais", "31101 - Tecidos",
  "31102 - Aviamentos", "31103 - Insumos Gerais (produção)", "31104 - Produtos Revenda",
  "31105 - Embalagens", "31106 - Sacolas", "31107 - Etiquetas - Viagem/Acessórios",
  "31108 - Lacres", "31109 - Prestação de Serviço - Corte", "31110 - Faccionista - Conserto",
  "31111 - Faccionista - Mão de Obra", "31112 - Frete/Transporte - Produção", "31113 - Faccionista - Confecção de Pilotos",
  "32101 - Bonificação / Premiação", "32102 - Comissões", "32201 - Entregas On-line",
  "32202 - Entregas Atacado", "32203 - Plataforma de Vendas On-Line", "32204 - Devolução de Vendas",
  "32205 - Aluguel Percentual", "32206 - Embalagens (Sacolas, Envelopes e Papel Seda)", "32207 - Ações Comerciais",
  "32601 - Juros Cheque Especial / IOF", "32602 - Juros por Atraso de Pagamentos", "32701 - Contrato de Mutuo - Débito",
  "33301 - ICMS", "33302 - ICMS Substituição Tributária", "33303 - ICMS Antecipacao Parcial",
  "33304 - PIS (0620)", "33305 - COFINS (2172)", "33306 - IRPJ (2089)",
  "33307 - CSLL (2372)", "33308 - Simples Nacional", "33309 - DARE",
  "33401 - Investimento - Predial", "33402 - Investimento - Informática", "33403 - Investimento - Elétrica",
  "33404 - Investimento - Máquinas e Equipamentos", "33405 - Investimento - Refrigeração/Ar-condicionado", "33406 - Investimento - Mobiliário/Decoração",
  "33407 - Investimento - Consultorias e Prestações de Serviços", "33408 - Investimento - Marcas e Patentes", "33409 - Investimento - Novas Unidades (Custos com novas lojas Boah)",
  "33410 - Investimento - Novas Unidades (Custos com novas lojas Solar)", "33501 - Retirada de Sócios",
  "TRANSFERENCIA", "A CLASSIFICAR"
];

const RESPONSAVEIS_PADRAO = [
  "ADM/FINANCEIRO", "COMPRAS", "GERENTE ONLINE", "LOGISTICA",
  "MARKETING", "PRODUCAO", "RH", "SUPRIMENTOS", "GERÊNCIA LOJA"
];

export default function Autorizacoes() {
  const [pagamentos, setPagamentos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('importacao');
  const [historico, setHistorico] = useState([]);
  
  const [showRelatorioModerno, setShowRelatorioModerno] = useState(false);
  const [saldos, setSaldos] = useState({ 'Itaú': '', 'Bradesco': '', 'Banco do Brasil': '' });

  // Lote para o sistema
  const [showLoteModal, setShowLoteModal] = useState(false);
  const [loteEmpresa, setLoteEmpresa] = useState('LALUA');
  const [loteFilial, setLoteFilial] = useState('LALUA MATRIZ');

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

  const handleLancarLote = async () => {
    setLoading(true);
    try {
      // 1. Treina a base primeiro para salvar aprendizado
      await treinarCategorias();

      // 2. Envia para a API de lote
      const res = await fetch("http://localhost:8000/api/notas/importar_lote", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          empresa: loteEmpresa,
          filial: loteFilial,
          pagamentos: pagamentos.map(p => ({
            cnpj: p.cnpj || "00.000.000/0000-00",
            nome: p.favorecido || p.nome || "",
            responsavel: p.responsavel,
            categoria: p.categoria,
            descricao: p.descricao || "",
            valor: p.valor || 0,
            data: p.data // DD/MM/YYYY
          }))
        })
      });

      const data = await res.json();
      if (data.success) {
        setPagamentos([]);
        setShowLoteModal(false);
        alert("Lote lançado com sucesso na aba Pagamentos Pendentes!");
      } else {
        throw new Error(data.error || "Erro ao lançar lote");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

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
                  <button className="btn-gerar-moderno" onClick={() => setShowLoteModal(true)}>
                    <Save size={20} />
                    Lançar no Sistema
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

              {showLoteModal && (
                <div className="modal-overlay">
                  <div className="modal-content glass-panel" style={{ maxWidth: '400px' }}>
                    <div className="modal-header">
                      <h3>Lançar Lote no Sistema</h3>
                      <button className="close-btn" onClick={() => setShowLoteModal(false)}>
                        <X size={20} />
                      </button>
                    </div>
                    <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                      <p className="text-muted">Todos os {pagamentos.length} registros serão inseridos como "Pendentes" e ficarão disponíveis na aba de Baixas para edição ou conciliação.</p>
                      
                      <div className="form-group">
                        <label>Empresa Padrão</label>
                        <select className="input-field" value={loteEmpresa} onChange={e => {
                          setLoteEmpresa(e.target.value);
                          setLoteFilial(e.target.value === 'LALUA' ? 'LALUA MATRIZ' : 'SOLAR MATRIZ');
                        }}>
                          <option value="LALUA">LALUA</option>
                          <option value="SOLAR">SOLAR</option>
                        </select>
                      </div>

                      <div className="form-group">
                        <label>Filial Padrão</label>
                        <select className="input-field" value={loteFilial} onChange={e => setLoteFilial(e.target.value)}>
                          {loteEmpresa === 'LALUA' ? (
                            <>
                              <option>LALUA MATRIZ</option>
                              <option>BOAH BARRA</option>
                              <option>PASEO</option>
                              <option>VILAS</option>
                              <option>SDB</option>
                              <option>HORTO</option>
                              <option>ONLINE</option>
                            </>
                          ) : (
                            <>
                              <option>SOLAR MATRIZ</option>
                              <option>ALAMEDA</option>
                            </>
                          )}
                        </select>
                      </div>

                      <button className="btn-gerar-pdf" onClick={handleLancarLote} style={{ width: '100%' }} disabled={loading}>
                        {loading ? <span className="spinner"></span> : <CheckCircle2 size={18} />}
                        {loading ? ' Lançando...' : ' Confirmar Lançamento'}
                      </button>
                    </div>
                  </div>
                </div>
              )}

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
