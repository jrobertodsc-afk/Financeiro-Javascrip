import React, { useState, useEffect } from 'react';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { Download, Filter, FileSpreadsheet, LayoutDashboard, Calculator } from 'lucide-react';
import * as XLSX from 'xlsx';
import './Relatorios.css';

export default function Relatorios() {
  const [activeTab, setActiveTab] = useState('graficos'); // graficos, geral, tributos
  const [loading, setLoading] = useState(false);

  // Filtros Globais
  const [filtros, setFiltros] = useState({
    empresa: '',
    status: '',
    tipoData: 'vencimento', // emissao, vencimento, pagamento
    dtInicio: '',
    dtFim: ''
  });

  // Dados
  const [rateioData, setRateioData] = useState([]);
  const [categoriaData, setCategoriaData] = useState([]);
  const [notasData, setNotasData] = useState([]);
  const [tributosData, setTributosData] = useState([]);

  const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];
  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  const buildQueryString = () => {
    const params = new URLSearchParams();
    if (filtros.empresa) params.append('empresa', filtros.empresa);
    if (filtros.status) params.append('status', filtros.status);
    if (filtros.dtInicio) params.append('dt_inicio', filtros.dtInicio);
    if (filtros.dtFim) params.append('dt_fim', filtros.dtFim);
    
    // Tratamento do tipo de data
    if (filtros.tipoData === 'pagamento') {
      params.append('tipo_data', 'vencimento'); // Assumimos vencimento para notas pagas
      params.set('status', 'PAGO'); // Força status PAGO
    } else {
      params.append('tipo_data', filtros.tipoData);
    }
    
    return params.toString();
  };

  const fetchGraficos = async (query) => {
    try {
      const [resRateio, resCat] = await Promise.all([
        fetch(`${API_URL}/api/relatorios/rateio?${query}`),
        fetch(`${API_URL}/api/notas/busca?${query}`)
      ]);
      const jsonRateio = await resRateio.json();
      const jsonCat = await resCat.json();
      
      if (jsonRateio.success) setRateioData(jsonRateio.rateio);
      
      if (jsonCat.success) {
        const catMap = {};
        jsonCat.notas.forEach(n => {
          const cat = n.categoria || 'Sem Categoria';
          catMap[cat] = (catMap[cat] || 0) + parseFloat(n.valor_bruto || 0);
        });
        const catArr = Object.entries(catMap)
          .map(([name, value]) => ({ name, value }))
          .sort((a, b) => b.value - a.value);
        setCategoriaData(catArr);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchRelatorioGeral = async (query) => {
    try {
      const res = await fetch(`${API_URL}/api/relatorios/avancado?${query}`);
      const json = await res.json();
      if (json.success) setNotasData(json.notas);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchTributos = async (query) => {
    try {
      const res = await fetch(`${API_URL}/api/relatorios/tributos?${query}`);
      const json = await res.json();
      if (json.success) setTributosData(json.tributos);
    } catch (e) {
      console.error(e);
    }
  };

  const handleApplyFilters = async () => {
    setLoading(true);
    const qs = buildQueryString();
    if (activeTab === 'graficos') await fetchGraficos(qs);
    else if (activeTab === 'geral') await fetchRelatorioGeral(qs);
    else if (activeTab === 'tributos') await fetchTributos(qs);
    setLoading(false);
  };

  // Carrega ao mudar de aba
  useEffect(() => {
    handleApplyFilters();
  }, [activeTab]);

  const formatMoney = (val) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val || 0);

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div className="custom-tooltip" style={{ backgroundColor: '#1e293b', padding: '10px', borderRadius: '8px', border: '1px solid #334155' }}>
          <p style={{ color: '#fff', margin: 0, fontWeight: 500 }}>{`${payload[0].name || payload[0].payload.centro_custo}`}</p>
          <p style={{ color: '#10b981', margin: 0, fontWeight: 'bold' }}>{formatMoney(payload[0].value)}</p>
        </div>
      );
    }
    return null;
  };

  const exportarExcelGeral = () => {
    if (notasData.length === 0) return alert('Sem dados para exportar!');
    const exportData = notasData.map(n => ({
      "ID": n.id,
      "Empresa": n.empresa,
      "Filial": n.filial,
      "Fornecedor": n.fornecedor,
      "CNPJ": n.cnpj,
      "Emissão": n.dt_emissao,
      "Vencimento": n.dt_vencimento,
      "Categoria": n.categoria,
      "Valor Bruto": n.valor_bruto,
      "Valor Líquido": n.valor_liquido,
      "Status": n.status,
      "Responsável": n.responsavel,
      "Descrição": n.descricao
    }));
    
    const ws = XLSX.utils.json_to_sheet(exportData);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Relatorio_Geral");
    XLSX.writeFile(wb, `Relatorio_Financeiro_${new Date().getTime()}.xlsx`);
  };

  const exportarExcelTributos = () => {
    if (tributosData.length === 0) return alert('Sem dados para exportar!');
    const exportData = tributosData.map(t => ({
      "ID da Nota Original": t.nota_id,
      "Fornecedor (NF)": t.fornecedor_origem,
      "Nº NF": t.numero_nf,
      "Data Emissão NF": t.dt_emissao,
      "Tipo Imposto": t.imposto_tipo,
      "Valor Imposto": t.imposto_valor,
      "Vencimento Guia": t.imposto_vencimento,
      "Status Pagamento": t.status_pagamento
    }));
    
    const ws = XLSX.utils.json_to_sheet(exportData);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Relatorio_Tributos");
    XLSX.writeFile(wb, `Relatorio_Tributos_${new Date().getTime()}.xlsx`);
  };

  return (
    <div className="relatorios-container">
      <div className="relatorios-header">
        <div>
          <h2>📊 Central de Relatórios</h2>
          <p className="text-muted">Análises gerenciais, extração de dados e detalhamento de impostos.</p>
        </div>
        
        {/* Painel de Filtros Global */}
        <div className="filtros-globais glass-panel" style={{ display: 'flex', gap: '15px', padding: '15px', borderRadius: '12px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div className="form-group" style={{ margin: 0 }}>
            <label style={{ fontSize: '12px', color: '#94a3b8' }}>Empresa</label>
            <select className="input-field" value={filtros.empresa} onChange={e => setFiltros({...filtros, empresa: e.target.value})} style={{ minWidth: '130px' }}>
              <option value="">Todas</option>
              <option value="LALUA">LALUA</option>
              <option value="SOLAR">SOLAR</option>
            </select>
          </div>
          
          <div className="form-group" style={{ margin: 0 }}>
            <label style={{ fontSize: '12px', color: '#94a3b8' }}>Status</label>
            <select className="input-field" value={filtros.status} onChange={e => setFiltros({...filtros, status: e.target.value})} style={{ minWidth: '130px' }}>
              <option value="">Todos</option>
              <option value="PENDENTE">Pendentes</option>
              <option value="PAGO">Pagos</option>
              <option value="CANCELADO">Cancelados</option>
            </select>
          </div>

          <div className="form-group" style={{ margin: 0 }}>
            <label style={{ fontSize: '12px', color: '#94a3b8' }}>Filtrar Data Por</label>
            <select className="input-field" value={filtros.tipoData} onChange={e => setFiltros({...filtros, tipoData: e.target.value})} style={{ minWidth: '140px' }}>
              <option value="vencimento">Vencimento</option>
              <option value="emissao">Emissão</option>
              <option value="pagamento">Data Pagamento (Baixadas)</option>
            </select>
          </div>

          <div className="form-group" style={{ margin: 0 }}>
            <label style={{ fontSize: '12px', color: '#94a3b8' }}>Início</label>
            <input type="date" className="input-field" value={filtros.dtInicio} onChange={e => setFiltros({...filtros, dtInicio: e.target.value})} />
          </div>

          <div className="form-group" style={{ margin: 0 }}>
            <label style={{ fontSize: '12px', color: '#94a3b8' }}>Fim</label>
            <input type="date" className="input-field" value={filtros.dtFim} onChange={e => setFiltros({...filtros, dtFim: e.target.value})} />
          </div>

          <button onClick={handleApplyFilters} className="btn-primary" disabled={loading} style={{ height: '42px', padding: '0 20px' }}>
            <Filter size={18} /> Filtrar
          </button>
        </div>
      </div>

      {/* Navegação de Abas */}
      <div className="tabs-nav">
        <button className={`tab-btn ${activeTab === 'graficos' ? 'active' : ''}`} onClick={() => setActiveTab('graficos')}>
          <LayoutDashboard size={18} /> Dashboard Visual
        </button>
        <button className={`tab-btn ${activeTab === 'geral' ? 'active' : ''}`} onClick={() => setActiveTab('geral')}>
          <FileSpreadsheet size={18} /> Relatório Financeiro Geral
        </button>
        <button className={`tab-btn ${activeTab === 'tributos' ? 'active' : ''}`} onClick={() => setActiveTab('tributos')}>
          <Calculator size={18} /> Impostos e NF-e Relacionadas
        </button>
      </div>

      <div className="tab-content" style={{ padding: 0, border: 'none' }}>
        {loading ? (
          <div className="loading-state">
            <span className="spinner" style={{ width: '40px', height: '40px', borderWidth: '4px' }}></span>
            <p>Processando relatório...</p>
          </div>
        ) : (
          <>
            {/* ABA 1: GRÁFICOS */}
            {activeTab === 'graficos' && (
              <div className="charts-grid">
                <div className="chart-card metric-card">
                  <h3 className="chart-title">Despesas por Categoria</h3>
                  <div className="chart-wrapper">
                    {categoriaData.length === 0 ? (
                      <div className="empty-state">Sem dados para os filtros selecionados.</div>
                    ) : (
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie data={categoriaData} cx="50%" cy="50%" innerRadius={80} outerRadius={120} paddingAngle={2} dataKey="value">
                            {categoriaData.map((entry, index) => <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />)}
                          </Pie>
                          <Tooltip content={<CustomTooltip />} />
                          <Legend verticalAlign="bottom" wrapperStyle={{ paddingTop: '20px' }} />
                        </PieChart>
                      </ResponsiveContainer>
                    )}
                  </div>
                </div>

                <div className="chart-card metric-card">
                  <h3 className="chart-title">Gastos por Centro de Custo (Rateio)</h3>
                  <div className="chart-wrapper">
                    {rateioData.length === 0 ? (
                      <div className="empty-state">Nenhum rateio registrado para os filtros selecionados.</div>
                    ) : (
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={rateioData} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                          <XAxis type="number" hide />
                          <YAxis dataKey="centro_custo" type="category" width={120} tick={{ fill: 'var(--text-muted)', fontSize: 12 }} />
                          <Tooltip content={<CustomTooltip />} cursor={{fill: 'rgba(255,255,255,0.05)'}} />
                          <Bar dataKey="total" radius={[0, 4, 4, 0]}>
                            {rateioData.map((entry, index) => <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />)}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* ABA 2: RELATÓRIO GERAL */}
            {activeTab === 'geral' && (
              <div className="table-container glass-panel" style={{ padding: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                  <h3 style={{ margin: 0, color: 'var(--text-color)' }}>Listagem Geral ({notasData.length} registros)</h3>
                  <button className="btn-success" onClick={exportarExcelGeral} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Download size={18} /> Exportar Excel
                  </button>
                </div>
                
                {notasData.length === 0 ? (
                  <div className="empty-state">Nenhum registro encontrado para os filtros.</div>
                ) : (
                  <div style={{ overflowX: 'auto', maxHeight: '60vh' }}>
                    <table className="modern-table">
                      <thead style={{ position: 'sticky', top: 0, zIndex: 1 }}>
                        <tr>
                          <th>Fornecedor</th>
                          <th>Categoria</th>
                          <th>Emissão</th>
                          <th>Vencimento</th>
                          <th>Valor Bruto</th>
                          <th>Status</th>
                          <th>Empresa</th>
                        </tr>
                      </thead>
                      <tbody>
                        {notasData.map(n => (
                          <tr key={n.id}>
                            <td style={{ fontWeight: 500 }}>{n.fornecedor}</td>
                            <td className="text-muted">{n.categoria?.substring(0, 30) || '-'}</td>
                            <td>{n.dt_emissao}</td>
                            <td>{n.dt_vencimento}</td>
                            <td style={{ color: 'var(--accent-color)' }}>{formatMoney(n.valor_bruto)}</td>
                            <td>
                              <span className={`badge badge-${n.status === 'PAGO' ? 'success' : n.status === 'CANCELADO' ? 'danger' : 'warning'}`}>
                                {n.status}
                              </span>
                            </td>
                            <td>{n.empresa}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {/* ABA 3: TRIBUTOS E NFs */}
            {activeTab === 'tributos' && (
              <div className="table-container glass-panel" style={{ padding: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                  <h3 style={{ margin: 0, color: 'var(--text-color)' }}>Relatório Fiscal ({tributosData.length} guias/tributos)</h3>
                  <button className="btn-success" onClick={exportarExcelTributos} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Download size={18} /> Exportar Excel Fiscal
                  </button>
                </div>
                
                {tributosData.length === 0 ? (
                  <div className="empty-state">Nenhum imposto registrado para as notas no período.</div>
                ) : (
                  <div style={{ overflowX: 'auto', maxHeight: '60vh' }}>
                    <table className="modern-table">
                      <thead style={{ position: 'sticky', top: 0, zIndex: 1 }}>
                        <tr>
                          <th>Fornecedor (NF Origem)</th>
                          <th>Nº NF</th>
                          <th>Imposto Retido</th>
                          <th>Valor Guia</th>
                          <th>Vencimento Guia</th>
                          <th>Status Guia/Nota</th>
                        </tr>
                      </thead>
                      <tbody>
                        {tributosData.map((t, idx) => (
                          <tr key={idx}>
                            <td style={{ fontWeight: 500 }}>{t.fornecedor_origem}</td>
                            <td className="text-muted">{t.numero_nf || 'S/N'}</td>
                            <td>
                              <span className="badge badge-info">{t.imposto_tipo}</span>
                            </td>
                            <td style={{ color: 'var(--danger-color)', fontWeight: 'bold' }}>{formatMoney(t.imposto_valor)}</td>
                            <td>{t.imposto_vencimento || 'N/A'}</td>
                            <td>
                              <span className={`badge badge-${t.status_pagamento === 'PAGO' ? 'success' : 'warning'}`}>
                                {t.status_pagamento}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
