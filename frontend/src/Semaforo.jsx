import { useState, useEffect, useMemo } from 'react'
import { AlertTriangle, Clock, Calendar, TrendingDown } from 'lucide-react'
import './Semaforo.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const formatMoney = (val) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val || 0)

const FAIXA_META = {
  vencido:  { label: 'VENCIDO',   cls: 'badge-vencido',  dot: 'dot-vencido' },
  hoje:     { label: 'HOJE',      cls: 'badge-hoje',     dot: 'dot-hoje'    },
  urgente:  { label: 'URGENTE',   cls: 'badge-urgente',  dot: 'dot-urgente' },
  proximo:  { label: 'A VENCER',  cls: 'badge-proximo',  dot: 'dot-proximo' },
}

export default function Semaforo() {
  const [dados, setDados]         = useState(null)
  const [loading, setLoading]     = useState(true)
  const [filtro, setFiltro]       = useState('todos')
  const [gerando, setGerando]     = useState(false)
  const [cnabStatus, setCnabStatus] = useState('')
  const [cnabOk, setCnabOk]       = useState(false)
  const [banco, setBanco]         = useState('ITAÚ')

  useEffect(() => {
    fetch(`${API_URL}/api/vencimentos/semaforo`)
      .then(r => r.json())
      .then(json => { setDados(json); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  const notasFiltradas = useMemo(() => {
    if (!dados) return []
    if (filtro === 'todos')
      return [
        ...dados.notas.vencido,
        ...dados.notas.hoje,
        ...dados.notas.urgente,
        ...dados.notas.proximo,
      ]
    return dados.notas[filtro] || []
  }, [dados, filtro])

  const gerarCnab = async () => {
    setGerando(true)
    setCnabStatus('')
    try {
      const res = await fetch(`${API_URL}/api/cnab/gerar?banco=${encodeURIComponent(banco)}`, {
        method: 'POST',
      })
      const json = await res.json()
      if (json.success) {
        const total = formatMoney(json.valor_total)
        setCnabStatus(`✓ ${json.arquivo_gerado || 'arquivo.REM'} | ${json.notas_incluidas} notas | ${total}`)
        setCnabOk(true)
      } else {
        setCnabStatus(`Erro: ${json.error || 'falha desconhecida'}`)
        setCnabOk(false)
      }
    } catch (err) {
      setCnabStatus(`Erro: ${err.message}`)
      setCnabOk(false)
    } finally {
      setGerando(false)
    }
  }

  if (loading) {
    return (
      <div className="semaforo-container">
        <div className="skeleton" style={{ height: '120px', marginBottom: '24px' }}></div>
        <div className="sem-cards-row">
          {[0,1,2,3].map(i => (
            <div key={i} className="skeleton" style={{ height: '140px', flex: 1 }}></div>
          ))}
        </div>
      </div>
    )
  }

  if (!dados) {
    return <div className="error-state">Erro ao carregar. Verifique se o Backend está rodando.</div>
  }

  const { totais, contagens } = dados

  const CARDS = [
    { faixa: 'vencido', label: 'Vencidos',      icon: AlertTriangle, cor: 'card-vencido',  total: totais.vencido,  qtd: contagens.vencido  },
    { faixa: 'hoje',    label: 'Vencem Hoje',   icon: Clock,         cor: 'card-hoje',     total: totais.hoje,     qtd: contagens.hoje     },
    { faixa: 'urgente', label: 'Próx. 3 Dias',  icon: TrendingDown,  cor: 'card-urgente',  total: totais.urgente,  qtd: contagens.urgente  },
    { faixa: 'proximo', label: 'Próx. 30 Dias', icon: Calendar,      cor: 'card-proximo',  total: totais.proximo,  qtd: contagens.proximo  },
  ]

  const FILTROS = [
    { id: 'todos',   label: 'Todos' },
    { id: 'vencido', label: 'Vencidos' },
    { id: 'hoje',    label: 'Hoje' },
    { id: 'urgente', label: 'Urgentes' },
    { id: 'proximo', label: 'Próximos' },
  ]

  return (
    <div className="semaforo-container">
      {/* Header */}
      <div className="cockpit-header">
        <h2>Semáforo de Vencimentos</h2>
        <p className="text-muted">Visão de prioridade por prazo de vencimento das contas a pagar.</p>
      </div>

      {/* Cards de métricas */}
      <div className="sem-cards-row">
        {CARDS.map(({ faixa, label, icon: Icon, cor, total, qtd }) => (
          <div
            key={faixa}
            className={`metric-card sem-card ${cor} ${filtro === faixa ? 'active' : ''}`}
            onClick={() => setFiltro(filtro === faixa ? 'todos' : faixa)}
            style={{ cursor: 'pointer' }}
          >
            <div className="metric-header">
              <span className="metric-label">{label}</span>
              <div className={`metric-icon sem-icon-${faixa}`}><Icon size={18} /></div>
            </div>
            <div className="metric-content">
              <div className={`metric-value sem-val-${faixa}`}>{formatMoney(total)}</div>
              <div className="metric-subtext">{qtd} {qtd === 1 ? 'fatura' : 'faturas'}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Filtros de lista */}
      <div className="sem-filtros">
        {FILTROS.map(f => (
          <button
            key={f.id}
            className={`sem-btn-filtro ${filtro === f.id ? 'active' : ''}`}
            onClick={() => setFiltro(f.id)}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Tabela de notas */}
      <div className="urgentes-section glass-panel">
        <div className="section-header">
          <h3 className="section-title">
            {notasFiltradas.length} {notasFiltradas.length === 1 ? 'nota' : 'notas'}
            {filtro !== 'todos' ? ` — ${FAIXA_META[filtro]?.label}` : ''}
          </h3>
        </div>

        {notasFiltradas.length === 0 ? (
          <div className="empty-state">🎉 Nenhuma nota nesta faixa.</div>
        ) : (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th></th>
                  <th>Vencimento</th>
                  <th>Fornecedor</th>
                  <th>Categoria</th>
                  <th>Empresa</th>
                  <th>Faixa</th>
                  <th className="col-amount">Valor</th>
                </tr>
              </thead>
              <tbody>
                {notasFiltradas.map(n => {
                  const meta = FAIXA_META[n.faixa] || FAIXA_META.proximo
                  return (
                    <tr key={n.id}>
                      <td><div className={`sem-dot ${meta.dot}`}></div></td>
                      <td>{n.dt_vencimento}</td>
                      <td className="font-bold" title={n.fornecedor}>
                        {(n.fornecedor || '').slice(0, 35)}{n.fornecedor?.length > 35 ? '…' : ''}
                      </td>
                      <td>{n.categoria || '—'}</td>
                      <td>{n.empresa || '—'}</td>
                      <td>
                        <span className={`badge ${meta.cls}`}>{meta.label}</span>
                      </td>
                      <td className="col-amount text-accent">{formatMoney(n.valor_bruto)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Seção CNAB */}
      <div className="cnab-section">
        <span>Gerar remessa bancária:</span>
        <select
          id="banco-select"
          value={banco}
          onChange={e => setBanco(e.target.value)}
          className="cnab-select"
        >
          <option value="ITAÚ">ITAÚ</option>
          <option value="SANTANDER">SANTANDER</option>
        </select>
        <button
          className="cnab-btn"
          onClick={gerarCnab}
          disabled={gerando}
        >
          {gerando ? 'Gerando…' : 'Gerar CNAB 240'}
        </button>
        {cnabStatus && (
          <span className={cnabOk ? 'cnab-ok' : 'cnab-erro'}>{cnabStatus}</span>
        )}
      </div>
    </div>
  )
}
