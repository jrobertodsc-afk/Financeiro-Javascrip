import { useState, useEffect } from 'react';
import './Pagamentos.css';

export default function Pagamentos({ onEditNota, onViewNota }) {
  const [notas, setNotas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [empresaFiltro, setEmpresaFiltro] = useState('');

  const fetchNotas = async () => {
    setLoading(true);
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const url = empresaFiltro 
        ? `${API_URL}/api/notas/pendentes?empresa=${empresaFiltro}` 
        : `${API_URL}/api/notas/pendentes`;
        
      const res = await fetch(url);
      const json = await res.json();
      if (json.success) {
        setNotas(json.notas);
      }
    } catch (err) {
      console.error("Erro ao buscar notas", err);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchNotas();
  }, [empresaFiltro]);

  const darBaixa = async (id, fornecedor) => {
    const confirmar = window.confirm(`Confirmar BAIXA / PAGAMENTO para ${fornecedor}?`);
    if (!confirmar) return;

    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const res = await fetch(`${API_URL}/api/notas/dar_baixa`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, novo_status: 'PAGO' })
      });
      const json = await res.json();
      
      if (json.success) {
        // Remover a nota da lista ou recarregar
        fetchNotas();
      } else {
        alert("Erro ao dar baixa: " + json.error);
      }
    } catch (err) {
      alert("Erro de conexão.");
    }
  };

  const cancelarNota = async (id, fornecedor) => {
    const confirmar = window.confirm(`Deseja CANCELAR a nota de ${fornecedor}?`);
    if (!confirmar) return;

    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const res = await fetch(`${API_URL}/api/notas/dar_baixa`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, novo_status: 'CANCELADO' })
      });
      const json = await res.json();
      
      if (json.success) {
        fetchNotas();
      } else {
        alert("Erro ao cancelar: " + json.error);
      }
    } catch (err) {
      alert("Erro de conexão.");
    }
  };

  const formatMoney = (val) => {
    if (!val) return 'R$ 0,00';
    return Number(val).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  };

  return (
    <div className="pagamentos-container glass-panel">
      <div className="pagamentos-header">
        <div>
          <h2>💸 Pagamentos Pendentes</h2>
          <p className="text-muted">Lista de despesas e notas lançadas aguardando pagamento.</p>
        </div>
        
        <div className="filtros">
          <label>Filtrar por Empresa:</label>
          <select value={empresaFiltro} onChange={e => setEmpresaFiltro(e.target.value)}>
            <option value="">TODAS</option>
            <option value="LALUA">LALUA</option>
            <option value="SOLAR">SOLAR</option>
          </select>
          <button onClick={fetchNotas} className="btn-refresh">🔄 Atualizar</button>
        </div>
      </div>

      <div className="table-responsive">
        {loading ? (
          <div className="loading-state">Carregando notas...</div>
        ) : notas.length === 0 ? (
          <div className="empty-state">Nenhum pagamento pendente encontrado. 🎉</div>
        ) : (
          <table className="pagamentos-table">
            <thead>
              <tr>
                <th>Vencimento</th>
                <th>Fornecedor</th>
                <th>Empresa / Filial</th>
                <th>Descrição</th>
                <th className="text-right">Valor</th>
                <th className="text-center">Ações</th>
              </tr>
            </thead>
            <tbody>
              {notas.map(nota => {
                // Tentar verificar se está atrasada comparando com a data de hoje
                const vencSplit = nota.dt_vencimento ? nota.dt_vencimento.split('/') : [];
                let isAtrasada = false;
                if (vencSplit.length === 3) {
                  const dataVenc = new Date(`${vencSplit[2]}-${vencSplit[1]}-${vencSplit[0]}T00:00:00`);
                  const hoje = new Date();
                  hoje.setHours(0,0,0,0);
                  if (dataVenc < hoje) isAtrasada = true;
                }

                return (
                  <tr key={nota.id}>
                    <td>
                      <span className={`badge ${isAtrasada ? 'badge-danger' : 'badge-neutral'}`}>
                        {nota.dt_vencimento || '-'}
                      </span>
                    </td>
                    <td className="font-bold">{nota.fornecedor}</td>
                    <td>
                      <div style={{fontSize: '12px', color: 'var(--text-muted)'}}>{nota.empresa}</div>
                      <div>{nota.filial}</div>
                    </td>
                    <td>{nota.descricao}</td>
                    <td className="text-right text-accent font-bold">
                      {formatMoney(nota.valor_bruto)}
                    </td>
                    <td className="actions-cell">
                      <button 
                        className="btn-details" 
                        onClick={() => onViewNota(nota.id)}
                        title="Ver Detalhes"
                        style={{ marginRight: '8px', padding: '6px 12px', background: 'var(--surface-raised)', border: '1px solid var(--border-color)', borderRadius: '4px', cursor: 'pointer', color: '#fff' }}
                      >
                        👁️ Detalhes
                      </button>
                      <button 
                        className="btn-baixa" 
                        onClick={() => darBaixa(nota.id, nota.fornecedor)}
                        title="Registrar Pagamento"
                      >
                        ✅ Dar Baixa
                      </button>
                      <button 
                        className="btn-cancel" 
                        onClick={() => cancelarNota(nota.id, nota.fornecedor)}
                        title="Cancelar Nota"
                      >
                        ❌
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
