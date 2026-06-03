import { useState } from 'react';
import './BuscaUniversal.css';

export default function BuscaUniversal({ onEditNota, onViewNota }) {
  const [notas, setNotas] = useState([]);
  const [loading, setLoading] = useState(false);
  const [busca, setBusca] = useState('');
  const [statusFiltro, setStatusFiltro] = useState('');
  const [empresaFiltro, setEmpresaFiltro] = useState('');

  const fetchNotas = async () => {
    setLoading(true);
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const params = new URLSearchParams();
      if (statusFiltro) params.append('status', statusFiltro);
      if (empresaFiltro) params.append('empresa', empresaFiltro);
      if (busca) params.append('busca', busca);
      
      const res = await fetch(`${API_URL}/api/notas/busca?${params.toString()}`);
      const json = await res.json();
      if (json.success) {
        setNotas(json.notas);
      }
    } catch (err) {
      console.error("Erro ao buscar", err);
    }
    setLoading(false);
  };

  // Busca ao pressionar Enter ou clicar
  const handleSearch = (e) => {
    e && e.preventDefault();
    fetchNotas();
  };

  const formatMoney = (val) => {
    if (!val) return 'R$ 0,00';
    return Number(val).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  };

  const statusColor = (s) => {
    if (s === 'PAGO') return 'badge-success';
    if (s === 'CANCELADO') return 'badge-cancel';
    if (s === 'PENDENTE') return 'badge-warning';
    return 'badge-neutral';
  };

  return (
    <div className="busca-container glass-panel">
      <div className="busca-header">
        <h2>🔍 Busca Universal</h2>
        <p className="text-muted">Pesquise qualquer nota, despesa ou pagamento do sistema.</p>
      </div>

      <form className="busca-filtros" onSubmit={handleSearch}>
        <input 
          type="text" 
          className="busca-input"
          placeholder="Fornecedor, descrição, nº NF, CNPJ..." 
          value={busca} 
          onChange={e => setBusca(e.target.value)} 
        />
        <select value={statusFiltro} onChange={e => setStatusFiltro(e.target.value)}>
          <option value="">Todos Status</option>
          <option value="PENDENTE">PENDENTE</option>
          <option value="PAGO">PAGO</option>
          <option value="CANCELADO">CANCELADO</option>
        </select>
        <select value={empresaFiltro} onChange={e => setEmpresaFiltro(e.target.value)}>
          <option value="">Todas Empresas</option>
          <option value="LALUA">LALUA</option>
          <option value="SOLAR">SOLAR</option>
        </select>
        <button type="submit" className="btn-buscar">Buscar</button>
      </form>

      <div className="busca-results-count">
        {!loading && <span>{notas.length} resultado(s)</span>}
      </div>

      <div className="table-responsive">
        {loading ? (
          <div className="loading-state">Buscando...</div>
        ) : notas.length === 0 ? (
          <div className="empty-state">Nenhum resultado. Use os filtros acima para refinar a busca.</div>
        ) : (
          <table className="busca-table">
            <thead>
              <tr>
                <th>Status</th>
                <th>Vencimento</th>
                <th>Fornecedor</th>
                <th>Empresa / Filial</th>
                <th>Descrição</th>
                <th>Nº NF</th>
                <th className="text-right">Valor</th>
                <th className="text-center">Ações</th>
              </tr>
            </thead>
            <tbody>
              {notas.map(nota => (
                <tr key={nota.id}>
                  <td>
                    <span className={`badge ${statusColor(nota.status)}`}>{nota.status}</span>
                  </td>
                  <td>{nota.dt_vencimento || '-'}</td>
                  <td className="font-bold">{nota.fornecedor}</td>
                  <td>
                    <div style={{fontSize: '11px', color: 'var(--text-muted)'}}>{nota.empresa}</div>
                    <div style={{fontSize: '13px'}}>{nota.filial}</div>
                  </td>
                  <td>{nota.descricao}</td>
                  <td>{nota.numero_nf || '-'}</td>
                  <td className="text-right text-accent font-bold">{formatMoney(nota.valor_bruto)}</td>
                  <td className="text-center">
                    <div className="card-actions">
                      <button 
                        className="btn-details" 
                        onClick={() => onViewNota(nota.id)}
                        style={{ padding: '6px 12px', background: 'var(--surface-raised)', border: '1px solid var(--border-color)', borderRadius: '4px', cursor: 'pointer', color: '#fff', fontSize: '12px' }}
                      >
                        👁️ Detalhes
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
