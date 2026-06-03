import { useState, useEffect } from 'react';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import './Relatorios.css';

export default function Relatorios() {
  const [rateioData, setRateioData] = useState([]);
  const [categoriaData, setCategoriaData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [empresaFiltro, setEmpresaFiltro] = useState('');

  const fetchRelatorios = async () => {
    setLoading(true);
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const params = empresaFiltro ? `?empresa=${empresaFiltro}` : '';
      
      // Busca dados de rateio do novo endpoint
      const resRateio = await fetch(`${API_URL}/api/relatorios/rateio${params}`);
      const jsonRateio = await resRateio.json();
      if (jsonRateio.success) {
        setRateioData(jsonRateio.rateio);
      }

      // Busca dados de categoria a partir das notas já existentes
      const resCat = await fetch(`${API_URL}/api/notas/busca${params}`);
      const jsonCat = await resCat.json();
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
    } catch (err) {
      console.error("Erro ao buscar relatórios", err);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchRelatorios();
  }, [empresaFiltro]);

  const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];

  const formatMoney = (val) => {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val);
  };

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div className="custom-tooltip">
          <p className="label">{`${payload[0].name || payload[0].payload.centro_custo}`}</p>
          <p className="value">{formatMoney(payload[0].value)}</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="relatorios-container">
      <div className="relatorios-header">
        <div>
          <h2>📊 Relatórios Gerenciais</h2>
          <p className="text-muted">Análise aprofundada das despesas por Categoria e Centro de Custo.</p>
        </div>
        <div className="filtros">
          <select value={empresaFiltro} onChange={e => setEmpresaFiltro(e.target.value)}>
            <option value="">Todas as Empresas</option>
            <option value="LALUA">LALUA</option>
            <option value="SOLAR">SOLAR</option>
          </select>
          <button onClick={fetchRelatorios} className="btn-refresh">🔄 Atualizar</button>
        </div>
      </div>

      {loading ? (
        <div className="loading-state">
          <div className="skeleton" style={{ height: '400px', width: '100%' }}></div>
        </div>
      ) : (
        <div className="charts-grid">
          {/* Card: Despesas por Categoria */}
          <div className="chart-card metric-card">
            <h3 className="chart-title">Despesas por Categoria</h3>
            <div className="chart-wrapper">
              {categoriaData.length === 0 ? (
                <div className="empty-state">Sem dados de categoria.</div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={categoriaData}
                      cx="50%"
                      cy="50%"
                      innerRadius={80}
                      outerRadius={120}
                      paddingAngle={2}
                      dataKey="value"
                    >
                      {categoriaData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip content={<CustomTooltip />} />
                    <Legend verticalAlign="bottom" height={36} />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          {/* Card: Despesas por Centro de Custo (Rateio) */}
          <div className="chart-card metric-card">
            <h3 className="chart-title">Gastos por Centro de Custo (Rateio)</h3>
            <div className="chart-wrapper">
              {rateioData.length === 0 ? (
                <div className="empty-state">Nenhum rateio registrado.</div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={rateioData}
                    layout="vertical"
                    margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                  >
                    <XAxis type="number" hide />
                    <YAxis 
                      dataKey="centro_custo" 
                      type="category" 
                      width={120}
                      tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
                    />
                    <Tooltip content={<CustomTooltip />} cursor={{fill: 'rgba(255,255,255,0.05)'}} />
                    <Bar dataKey="total" radius={[0, 4, 4, 0]}>
                      {rateioData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
