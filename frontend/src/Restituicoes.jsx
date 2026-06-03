import { useState, useEffect } from 'react';
import './Restituicoes.css';

export default function Restituicoes() {
  const [notas, setNotas] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchRestituicoes = async () => {
    setLoading(true);
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      // Busca notas que possuem DIFAL ou chave_ref (candidatas a restituição)
      const res = await fetch(`${API_URL}/api/notas/busca?status=PAGO`);
      const json = await res.json();
      if (json.success) {
        // Filtra apenas notas que possuem valor_difal > 0 ou chave_ref preenchida
        const restit = json.notas.filter(n => {
          const difal = parseFloat(n.valor_difal || 0);
          return difal > 0 || (n.chave_ref && n.chave_ref.trim() !== '');
        });
        setNotas(restit);
      }
    } catch (err) {
      console.error("Erro ao buscar restituições", err);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchRestituicoes();
  }, []);

  const formatMoney = (val) => {
    if (!val) return 'R$ 0,00';
    return Number(val).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  };

  const totalDifal = notas.reduce((acc, n) => acc + parseFloat(n.valor_difal || 0), 0);

  return (
    <div className="restit-container glass-panel">
      <div className="restit-header">
        <div>
          <h2>🛡️ Restituições DIFAL / GNRE</h2>
          <p className="text-muted">Notas pagas com valor de DIFAL ou GNRE passíveis de restituição.</p>
        </div>
        <button onClick={fetchRestituicoes} className="btn-refresh">🔄 Atualizar</button>
      </div>

      <div className="restit-resumo">
        <div className="resumo-card">
          <span className="resumo-label">Total DIFAL Pago</span>
          <span className="resumo-valor" style={{color: '#fbbf24'}}>{formatMoney(totalDifal)}</span>
        </div>
        <div className="resumo-card">
          <span className="resumo-label">Notas com DIFAL</span>
          <span className="resumo-valor">{notas.length}</span>
        </div>
      </div>

      {loading ? (
        <div className="loading-state">Carregando restituições...</div>
      ) : notas.length === 0 ? (
        <div className="empty-state">Nenhuma nota com DIFAL/GNRE encontrada.</div>
      ) : (
        <table className="restit-table">
          <thead>
            <tr>
              <th>Fornecedor</th>
              <th>NF</th>
              <th>Empresa / Filial</th>
              <th>Vencimento</th>
              <th className="text-right">Valor NF</th>
              <th className="text-right">DIFAL</th>
              <th>Chave Ref</th>
            </tr>
          </thead>
          <tbody>
            {notas.map(n => (
              <tr key={n.id}>
                <td className="font-bold">{n.fornecedor}</td>
                <td>{n.numero_nf || '-'}</td>
                <td>
                  <div style={{fontSize:'11px',color:'var(--text-muted)'}}>{n.empresa}</div>
                  <div>{n.filial}</div>
                </td>
                <td>{n.dt_vencimento || '-'}</td>
                <td className="text-right">{formatMoney(n.valor_bruto)}</td>
                <td className="text-right" style={{color:'#fbbf24',fontWeight:700}}>{formatMoney(n.valor_difal)}</td>
                <td style={{fontSize:'12px',fontFamily:'monospace'}}>{n.chave_ref || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
