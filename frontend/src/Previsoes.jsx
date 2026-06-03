import { useState, useEffect } from 'react';
import { CalendarDays, ArrowRight, CheckCircle2 } from 'lucide-react';
import './Previsoes.css';

export default function Previsoes() {
  const [previsoes, setPrevisoes] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchPrevisoes = async () => {
    setLoading(true);
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const res = await fetch(`${API_URL}/api/previsoes`);
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

      <div className="previsoes-list glass-panel">
        <div className="section-header">
          <h3 className="section-title">Timeline de Estimativas</h3>
        </div>

        {loading ? (
          <div className="loading-state">
            <div className="skeleton" style={{ height: '200px', width: '100%' }}></div>
          </div>
        ) : previsoes.length === 0 ? (
          <div className="empty-state">Nenhuma previsão de despesa futura registrada.</div>
        ) : (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Vencimento Estimado</th>
                  <th>Fornecedor / Categoria</th>
                  <th>Descrição</th>
                  <th className="col-amount">Valor Estimado</th>
                  <th className="text-center">Ações</th>
                </tr>
              </thead>
              <tbody>
                {previsoes.map(p => (
                  <tr key={p.id}>
                    <td>
                      <span className="badge badge-info">{p.dt_vencimento}</span>
                    </td>
                    <td>
                      <div className="font-bold">{p.fornecedor}</div>
                      <div className="text-muted" style={{fontSize: '12px'}}>{p.categoria}</div>
                    </td>
                    <td>{p.descricao}</td>
                    <td className="col-amount">{formatMoney(p.valor_bruto)}</td>
                    <td className="actions-cell">
                      <button 
                        className="btn-action btn-convert"
                        onClick={() => converterEmConta(p.id, p.fornecedor)}
                        title="Chegou a NF oficial? Converter em conta real."
                      >
                        <CheckCircle2 size={16} /> Converter em Real
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
