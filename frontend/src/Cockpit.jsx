import { useState, useEffect } from 'react';
import { AlertCircle, Clock, CalendarDays } from 'lucide-react';
import './Cockpit.css';

export default function Cockpit() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    fetch(`${API_URL}/api/cockpit`)
      .then(res => res.json())
      .then(json => {
        setData(json);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="cockpit-container">
        <div className="skeleton" style={{ height: '120px', marginBottom: '24px' }}></div>
        <div className="cards-row">
          <div className="skeleton" style={{ height: '140px', flex: 1 }}></div>
          <div className="skeleton" style={{ height: '140px', flex: 1 }}></div>
          <div className="skeleton" style={{ height: '140px', flex: 1 }}></div>
        </div>
      </div>
    );
  }

  if (!data) {
    return <div className="error-state">Erro ao carregar os dados. Verifique se o Backend está rodando.</div>;
  }

  const { cards, urgentes } = data;

  const formatMoney = (val) => {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val);
  };

  return (
    <div className="cockpit-container">
      <div className="cockpit-header">
        <h2>Visão Geral do Dia</h2>
        <p className="text-muted">Acompanhe seus compromissos financeiros e fluxo de aprovações.</p>
      </div>

      <div className="cards-row">
        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Vencem Hoje</span>
            <div className="metric-icon bg-warning"><AlertCircle size={18} /></div>
          </div>
          <div className="metric-content">
            <div className="metric-value">{formatMoney(cards.hoje.valor)}</div>
            <div className="metric-subtext">{cards.hoje.qtd} faturas aguardando pagamento</div>
          </div>
        </div>
        
        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Atrasados</span>
            <div className="metric-icon bg-danger"><Clock size={18} /></div>
          </div>
          <div className="metric-content">
            <div className="metric-value text-danger">{formatMoney(cards.atrasados.valor)}</div>
            <div className="metric-subtext">{cards.atrasados.qtd} faturas em atraso crítico</div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Próximos 3 Dias</span>
            <div className="metric-icon bg-info"><CalendarDays size={18} /></div>
          </div>
          <div className="metric-content">
            <div className="metric-value">{formatMoney(cards.proximos.valor)}</div>
            <div className="metric-subtext">{cards.proximos.qtd} faturas agendadas no período</div>
          </div>
        </div>
      </div>

      <div className="urgentes-section glass-panel">
        <div className="section-header">
          <h3 className="section-title">Ação Necessária (Hoje + Atrasadas)</h3>
        </div>
        
        {urgentes.length === 0 ? (
          <div className="empty-state">Tudo em dia! Nenhuma fatura exigindo atenção imediata.</div>
        ) : (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Vencimento</th>
                  <th>Fornecedor</th>
                  <th className="col-amount">Valor</th>
                </tr>
              </thead>
              <tbody>
                {urgentes.map(u => {
                  const parts = u.dt_vencimento.split('/');
                  const dtVenc = new Date(parts[2], parts[1] - 1, parts[0]);
                  const hoje = new Date();
                  hoje.setHours(0,0,0,0);
                  
                  const isAtrasada = dtVenc < hoje;
                  
                  return (
                    <tr key={u.id}>
                      <td>
                        <span className={`badge ${isAtrasada ? 'badge-danger' : 'badge-warning'}`}>
                          {isAtrasada ? 'ATRASADA' : 'VENCE HOJE'}
                        </span>
                      </td>
                      <td>{u.dt_vencimento}</td>
                      <td className="font-bold">{u.fornecedor}</td>
                      <td className="col-amount text-accent">
                        {formatMoney(u.valor_bruto)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
