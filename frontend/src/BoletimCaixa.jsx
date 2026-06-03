import { useState, useEffect } from 'react';
import './BoletimCaixa.css';

export default function BoletimCaixa() {
  const [boletim, setBoletim] = useState([]);
  const [loading, setLoading] = useState(true);
  const [empresaFiltro, setEmpresaFiltro] = useState('');
  const [expandedDate, setExpandedDate] = useState(null);

  const fetchBoletim = async () => {
    setLoading(true);
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const url = empresaFiltro
        ? `${API_URL}/api/boletim?empresa=${empresaFiltro}`
        : `${API_URL}/api/boletim`;
      const res = await fetch(url);
      const json = await res.json();
      if (json.success) {
        setBoletim(json.boletim);
      }
    } catch (err) {
      console.error("Erro ao carregar boletim", err);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchBoletim();
  }, [empresaFiltro]);

  const formatMoney = (val) => {
    if (!val) return 'R$ 0,00';
    return Number(val).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  };

  const totalGeral = boletim.reduce((acc, dia) => acc + dia.total, 0);

  return (
    <div className="boletim-container glass-panel">
      <div className="boletim-header">
        <div>
          <h2>📈 Boletim de Caixa</h2>
          <p className="text-muted">Pagamentos realizados agrupados por data de vencimento.</p>
        </div>
        <div className="filtros">
          <select value={empresaFiltro} onChange={e => setEmpresaFiltro(e.target.value)}>
            <option value="">TODAS</option>
            <option value="LALUA">LALUA</option>
            <option value="SOLAR">SOLAR</option>
          </select>
          <button onClick={fetchBoletim} className="btn-refresh">🔄</button>
        </div>
      </div>

      {/* Resumo Geral */}
      <div className="boletim-resumo">
        <div className="resumo-card">
          <span className="resumo-label">Total Pago</span>
          <span className="resumo-valor">{formatMoney(totalGeral)}</span>
        </div>
        <div className="resumo-card">
          <span className="resumo-label">Dias com Pagamento</span>
          <span className="resumo-valor">{boletim.length}</span>
        </div>
        <div className="resumo-card">
          <span className="resumo-label">Total de Notas Pagas</span>
          <span className="resumo-valor">{boletim.reduce((acc, d) => acc + d.qtd, 0)}</span>
        </div>
      </div>

      {loading ? (
        <div className="loading-state">Carregando boletim...</div>
      ) : boletim.length === 0 ? (
        <div className="empty-state">Nenhum pagamento registrado ainda.</div>
      ) : (
        <div className="boletim-lista">
          {boletim.map(dia => (
            <div key={dia.data} className="dia-card">
              <div 
                className="dia-header" 
                onClick={() => setExpandedDate(expandedDate === dia.data ? null : dia.data)}
              >
                <div className="dia-info">
                  <span className="dia-data">{dia.data}</span>
                  <span className="dia-qtd">{dia.qtd} nota(s)</span>
                </div>
                <div className="dia-total">{formatMoney(dia.total)}</div>
                <span className="dia-chevron">{expandedDate === dia.data ? '▲' : '▼'}</span>
              </div>
              
              {expandedDate === dia.data && (
                <div className="dia-detalhes">
                  <table>
                    <thead>
                      <tr>
                        <th>Fornecedor</th>
                        <th>Descrição</th>
                        <th>Empresa</th>
                        <th className="text-right">Valor</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dia.notas.map((n, idx) => (
                        <tr key={idx}>
                          <td className="font-bold">{n.fornecedor}</td>
                          <td>{n.descricao}</td>
                          <td>{n.empresa} / {n.filial}</td>
                          <td className="text-right text-accent">{formatMoney(n.valor_bruto)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
