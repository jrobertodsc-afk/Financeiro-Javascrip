import { useState, useEffect } from 'react';
import './ExtratoContabil.css';

export default function ExtratoContabil() {
  const [notas, setNotas] = useState([]);
  const [loading, setLoading] = useState(false);
  const [empresaFiltro, setEmpresaFiltro] = useState('');
  const [agrupamento, setAgrupamento] = useState('categoria');

  const fetchNotas = async () => {
    setLoading(true);
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const params = new URLSearchParams();
      params.append('status', 'PAGO');
      if (empresaFiltro) params.append('empresa', empresaFiltro);
      
      const res = await fetch(`${API_URL}/api/notas/busca?${params.toString()}`);
      const json = await res.json();
      if (json.success) {
        setNotas(json.notas);
      }
    } catch (err) {
      console.error("Erro ao buscar extrato", err);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchNotas();
  }, [empresaFiltro]);

  const formatMoney = (val) => {
    if (!val) return 'R$ 0,00';
    return Number(val).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  };

  // Agrupa notas pelo campo selecionado
  const agrupar = () => {
    const grupos = {};
    notas.forEach(n => {
      const chave = n[agrupamento] || 'SEM CLASSIFICAÇÃO';
      if (!grupos[chave]) grupos[chave] = { notas: [], total: 0 };
      grupos[chave].notas.push(n);
      grupos[chave].total += parseFloat(n.valor_bruto || 0);
    });
    // Ordena por total decrescente
    return Object.entries(grupos)
      .map(([nome, dados]) => ({ nome, ...dados }))
      .sort((a, b) => b.total - a.total);
  };

  const grupos = agrupar();
  const totalGeral = notas.reduce((acc, n) => acc + parseFloat(n.valor_bruto || 0), 0);

  return (
    <div className="extrato-container glass-panel">
      <div className="extrato-header">
        <div>
          <h2>📑 Extrato Contábil</h2>
          <p className="text-muted">Visão consolidada dos pagamentos agrupados por categoria, filial ou natureza.</p>
        </div>
        <div className="filtros">
          <label>Agrupar por:</label>
          <select value={agrupamento} onChange={e => setAgrupamento(e.target.value)}>
            <option value="categoria">Categoria</option>
            <option value="filial">Filial</option>
            <option value="natureza">Natureza</option>
            <option value="fornecedor">Fornecedor</option>
          </select>
          <select value={empresaFiltro} onChange={e => setEmpresaFiltro(e.target.value)}>
            <option value="">TODAS</option>
            <option value="LALUA">LALUA</option>
            <option value="SOLAR">SOLAR</option>
          </select>
        </div>
      </div>

      <div className="extrato-total-bar">
        <span>Total Geral:</span>
        <span className="extrato-total-valor">{formatMoney(totalGeral)}</span>
      </div>

      {loading ? (
        <div className="loading-state">Carregando extrato...</div>
      ) : grupos.length === 0 ? (
        <div className="empty-state">Nenhum pagamento para exibir.</div>
      ) : (
        <div className="extrato-grupos">
          {grupos.map(grupo => {
            const pct = totalGeral > 0 ? ((grupo.total / totalGeral) * 100).toFixed(1) : 0;
            return (
              <div key={grupo.nome} className="grupo-card">
                <div className="grupo-header">
                  <div className="grupo-info">
                    <span className="grupo-nome">{grupo.nome}</span>
                    <span className="grupo-qtd">{grupo.notas.length} nota(s)</span>
                  </div>
                  <div className="grupo-valores">
                    <span className="grupo-pct">{pct}%</span>
                    <span className="grupo-total">{formatMoney(grupo.total)}</span>
                  </div>
                </div>
                <div className="grupo-bar">
                  <div className="grupo-bar-fill" style={{ width: `${pct}%` }}></div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
