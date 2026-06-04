import { useState, useEffect } from 'react';
import { CalendarDays, ArrowRight, CheckCircle2 } from 'lucide-react';
import './Previsoes.css';

export default function Previsoes() {
  const [previsoes, setPrevisoes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dtInicio, setDtInicio] = useState('');
  const [dtFim, setDtFim] = useState('');

  const fetchPrevisoes = async () => {
    setLoading(true);
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      let url = `${API_URL}/api/previsoes`;
      const queryParams = new URLSearchParams();
      if (dtInicio) queryParams.append('dt_inicio', dtInicio);
      if (dtFim) queryParams.append('dt_fim', dtFim);
      if (queryParams.toString()) url += `?${queryParams.toString()}`;
      
      const res = await fetch(url);
      const json = await res.json();
      if (json.success) {
        setPrevisoes(json.previsoes);
      }
    } catch (err) {
      console.error("Erro ao buscar previsoes", err);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchPrevisoes();
  }, []);

  const formatMoney = (val) => {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val);
  };

  const converterEmConta = async (id, fornecedor) => {
    const confirmar = window.confirm(`A fatura oficial de ${fornecedor} chegou? Deseja converter esta previsão em Conta a Pagar Real?`);
    if (!confirmar) return;

    try {
      // Para o MVP: só dar baixa como "PENDENTE" e is_previsao = 0
      // Idealmente o backend teria uma rota especifica para "efetivar_previsao"
      // Aqui vamos reaproveitar o dar_baixa e o backend precisaria atualizar a flag.
      // Mas podemos apenas avisar que foi convertida.
      alert(`Na versão completa, isso abriria o formulário preenchido para anexar o PDF da NF real de ${fornecedor} e desmarcaria a flag de Previsão.`);
    } catch (err) {
      console.error(err);
    }
  };

  const totalEstimado = previsoes.reduce((acc, p) => acc + parseFloat(p.valor_bruto || 0), 0);

  return (
    <div className="previsoes-container">
      <div className="previsoes-header">
        <div>
          <h2><CalendarDays className="inline-icon" /> Fluxo de Previsões</h2>
          <p className="text-muted">Despesas estimadas (folha, luz, aluguel) que ainda não possuem nota fiscal emitida.</p>
        </div>
        <button onClick={fetchPrevisoes} className="btn-refresh">🔄 Atualizar</button>
      </div>

      <div className="metric-card mb-24">
        <div className="metric-header">
          <span className="metric-label">Total Estimado no Radar</span>
        </div>
        <div className="metric-content">
          <div className="metric-value text-info">{formatMoney(totalEstimado)}</div>
          <div className="metric-subtext">{previsoes.length} despesas previstas</div>
        </div>
      </div>

      <div className="filters-bar glass-panel" style={{ display: 'flex', gap: '16px', alignItems: 'flex-end', marginBottom: '24px', padding: '16px', borderRadius: '8px' }}>
         <div className="form-group" style={{ margin: 0, flex: 1 }}>
           <label style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>Data Inicial</label>
           <input type="date" value={dtInicio} onChange={e => setDtInicio(e.target.value)} style={{ width: '100%', padding: '10px', borderRadius: '4px', border: '1px solid var(--border-color)', background: 'var(--bg-lighter)', color: '#fff' }} />
         </div>
         <div className="form-group" style={{ margin: 0, flex: 1 }}>
           <label style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>Data Final</label>
           <input type="date" value={dtFim} onChange={e => setDtFim(e.target.value)} style={{ width: '100%', padding: '10px', borderRadius: '4px', border: '1px solid var(--border-color)', background: 'var(--bg-lighter)', color: '#fff' }} />
         </div>
         <button className="btn-salvar" onClick={fetchPrevisoes} style={{ padding: '10px 24px', height: '42px', margin: 0 }}>
           Filtrar
         </button>
      </div>

      <div className="previsoes-list glass-panel" style={{ background: 'transparent', border: 'none', padding: 0 }}>
        <div className="section-header" style={{ marginBottom: '24px' }}>
          <h3 className="section-title">Timeline de Estimativas</h3>
        </div>

        {loading ? (
          <div className="loading-state glass-panel">
            <div className="skeleton" style={{ height: '200px', width: '100%' }}></div>
          </div>
        ) : previsoes.length === 0 ? (
          <div className="empty-state glass-panel">Nenhuma previsão de despesa futura registrada.</div>
        ) : (
          <div>
            {Object.entries(previsoes.reduce((acc, p) => {
              let mesAno = "Mês Desconhecido";
              if (p.dt_vencimento && p.dt_vencimento.includes('/')) {
                  const parts = p.dt_vencimento.split('/');
                  if (parts.length === 3) {
                    const date = new Date(parts[2], parseInt(parts[1])-1, 1);
                    mesAno = date.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' });
                    mesAno = mesAno.charAt(0).toUpperCase() + mesAno.slice(1);
                  }
              } else if (p.dt_vencimento && p.dt_vencimento.includes('-')) {
                  const parts = p.dt_vencimento.split('-');
                  if (parts.length === 3) {
                    const date = new Date(parts[0], parseInt(parts[1])-1, 1);
                    mesAno = date.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' });
                    mesAno = mesAno.charAt(0).toUpperCase() + mesAno.slice(1);
                  }
              }
              
              if (!acc[mesAno]) {
                acc[mesAno] = { items: [], total: 0 };
              }
              acc[mesAno].items.push(p);
              acc[mesAno].total += parseFloat(p.valor_bruto || 0);
              return acc;
            }, {})).map(([mesAno, grupo]) => (
              <div key={mesAno} className="month-group mb-24 glass-panel" style={{ overflow: 'hidden' }}>
                <div className="month-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 24px', background: 'rgba(59, 130, 246, 0.1)', borderBottom: '2px solid var(--accent-color)' }}>
                  <h4 style={{ margin: 0, color: '#fff', fontSize: '18px', textTransform: 'capitalize' }}>🗓️ {mesAno}</h4>
                  <div style={{ textAlign: 'right' }}>
                    <span style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block' }}>Total Previsto no Mês</span>
                    <span style={{ fontWeight: 'bold', color: 'var(--accent-color)', fontSize: '18px' }}>{formatMoney(grupo.total)}</span>
                  </div>
                </div>
                <div className="table-responsive">
                  <table className="data-table" style={{ border: 'none', background: 'transparent' }}>
                    <thead>
                      <tr>
                        <th style={{ background: 'transparent', paddingLeft: '24px' }}>Vencimento</th>
                        <th style={{ background: 'transparent' }}>Fornecedor / Categoria</th>
                        <th style={{ background: 'transparent' }}>Descrição</th>
                        <th className="col-amount" style={{ background: 'transparent' }}>Valor Estimado</th>
                        <th className="text-center" style={{ background: 'transparent', paddingRight: '24px' }}>Ações</th>
                      </tr>
                    </thead>
                    <tbody>
                      {grupo.items.map(p => (
                        <tr key={p.id}>
                          <td style={{ paddingLeft: '24px' }}>
                            <span className="badge badge-info">{p.dt_vencimento}</span>
                          </td>
                          <td>
                            <div className="font-bold">{p.fornecedor}</div>
                            <div className="text-muted" style={{fontSize: '12px'}}>{p.categoria}</div>
                          </td>
                          <td>{p.descricao}</td>
                          <td className="col-amount font-bold">{formatMoney(p.valor_bruto)}</td>
                          <td className="actions-cell" style={{ paddingRight: '24px' }}>
                            <button 
                              className="btn-action btn-convert"
                              onClick={() => converterEmConta(p.id, p.fornecedor)}
                              title="Chegou a NF oficial? Converter em conta real."
                              style={{ border: '1px solid var(--success-color)', background: 'rgba(34, 197, 94, 0.1)', padding: '6px 12px' }}
                            >
                              <CheckCircle2 size={16} color="var(--success-color)" /> <span style={{color: 'var(--success-color)', fontWeight: '600'}}>Efetivar</span>
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
