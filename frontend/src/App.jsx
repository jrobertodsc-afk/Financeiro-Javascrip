import { useState } from 'react'
import { 
  LayoutDashboard, 
  FilePlus2, 
  CreditCard, 
  Search, 
  TrendingUp, 
  BookOpen, 
  Zap, 
  ShieldCheck,
  ChevronRight,
  CalendarDays,
  ShieldAlert,
  Menu
} from 'lucide-react'
import Cockpit from './Cockpit'
import LancarNota from './LancarNota'
import Pagamentos from './Pagamentos'
import BuscaUniversal from './BuscaUniversal'
import BoletimCaixa from './BoletimCaixa'
import ExtratoContabil from './ExtratoContabil'
import ImportacaoSmart from './ImportacaoSmart'
import Restituicoes from './Restituicoes'
import Relatorios from './Relatorios'
import Previsoes from './Previsoes'
import Autorizacoes from './Autorizacoes'
import NotaDetailsModal from './NotaDetailsModal'
import './App.css'

function App() {
  const [activeTab, setActiveTab] = useState('Cockpit');
  const [editNotaId, setEditNotaId] = useState(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [viewNotaId, setViewNotaId] = useState(null);

  const handleEditNota = (notaId) => {
    setViewNotaId(null);
    setEditNotaId(notaId);
    setActiveTab('Lançar Nota');
  };

  const handleViewNota = (notaId) => {
    setViewNotaId(notaId);
  };

  const tabs = [
    { id: 'Cockpit', icon: LayoutDashboard, label: 'Cockpit' },
    { id: 'Lançar Nota', icon: FilePlus2, label: 'Lançar Nota' },
    { id: 'Pagamentos Pendentes', icon: CreditCard, label: 'Pagamentos' },
    { id: 'Autorizações', icon: ShieldAlert, label: 'Autorizações' },
    { id: 'Busca Universal', icon: Search, label: 'Busca' },
    { id: 'Boletim de Caixa', icon: TrendingUp, label: 'Boletim' },
    { id: 'Relatórios', icon: BookOpen, label: 'Relatórios' },
    { id: 'Extrato Contábil', icon: BookOpen, label: 'Extrato' },
    { id: 'Previsões', icon: CalendarDays, label: 'Previsões' },
    { id: 'Importação Smart', icon: Zap, label: 'Importação' },
    { id: 'Restituições', icon: ShieldCheck, label: 'Restituições' }
  ];

  const renderTab = () => {
    switch (activeTab) {
      case 'Cockpit': return <Cockpit />;
      case 'Lançar Nota': return <LancarNota editNotaId={editNotaId} onClearEdit={() => setEditNotaId(null)} />;
      case 'Pagamentos Pendentes': return <Pagamentos onEditNota={handleEditNota} onViewNota={handleViewNota} />;
      case 'Autorizações': return <Autorizacoes />;
      case 'Busca Universal': return <BuscaUniversal onEditNota={handleEditNota} onViewNota={handleViewNota} />;
      case 'Boletim de Caixa': return <BoletimCaixa />;
      case 'Relatórios': return <Relatorios />;
      case 'Extrato Contábil': return <ExtratoContabil />;
      case 'Previsões': return <Previsoes />;
      case 'Importação Smart': return <ImportacaoSmart />;
      case 'Restituições': return <Restituicoes />;
      default: return null;
    }
  };

  return (
    <div className="app-container">
      {/* SIDEBAR */}
      <nav className={`sidebar ${!isSidebarOpen ? 'collapsed' : ''}`}>
        <div className="sidebar-header">
          <div className="logo-box">
            <div className="logo-mark">C</div>
            {isSidebarOpen && (
              <div className="logo-text">
                <h2>ComSystem</h2>
                <span className="logo-edition">Finance • ERP</span>
              </div>
            )}
          </div>
        </div>

        {isSidebarOpen && <div className="nav-section-label">Menu Principal</div>}
        <ul className="nav-list" style={{ marginTop: isSidebarOpen ? 0 : '24px' }}>
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <li 
                key={tab.id} 
                className={`nav-item ${isActive ? 'active' : ''}`}
                onClick={() => {
                  setActiveTab(tab.id);
                  if (tab.id !== 'Lançar Nota') {
                    setEditNotaId(null);
                  }
                }}
              >
                <Icon size={18} strokeWidth={isActive ? 2.2 : 1.8} style={{ minWidth: '18px' }} />
                {isSidebarOpen && <span className="nav-text">{tab.id}</span>}
                {isActive && isSidebarOpen && <ChevronRight size={14} className="nav-chevron" />}
              </li>
            );
          })}
        </ul>

        <div className="sidebar-footer">
          {isSidebarOpen ? (
            <>
              <div className="status-indicator">
                <span className="dot online"></span>
                <span>API Conectada</span>
              </div>
              <span className="version-tag">v2.0</span>
            </>
          ) : (
            <div className="status-indicator" style={{ justifyContent: 'center', width: '100%' }}>
              <span className="dot online"></span>
            </div>
          )}
        </div>
      </nav>

      {/* MAIN CONTENT AREA */}
      <main className="main-content">
        <header className="topbar">
          <div className="topbar-left" style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <button 
              className="btn-toggle-sidebar" 
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              title="Recolher / Expandir Menu"
            >
              <Menu size={20} />
            </button>
            <h1>{activeTab}</h1>
          </div>
          <div className="topbar-right">
            <div className="user-profile">
              <div className="user-info">
                <span className="user-name">Roberto</span>
                <span className="user-role">Administrador</span>
              </div>
              <div className="avatar">R</div>
            </div>
          </div>
        </header>

        <div className="tab-content" key={activeTab}>
          {renderTab()}
        </div>
      </main>

      {/* MODAL GLOBAL - Garante que ele fique acima de toda a tela e não preso na aba */}
      {viewNotaId && (
        <NotaDetailsModal 
          notaId={viewNotaId} 
          onClose={() => setViewNotaId(null)} 
          onEdit={(id) => handleEditNota(id)}
        />
      )}
    </div>
  )
}

export default App
