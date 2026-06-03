import { Printer, ChevronLeft } from 'lucide-react';
import './RelatorioModerno.css';

export default function RelatorioModerno({ pagamentos, saldos, onClose }) {
  const totalPagamentos = pagamentos.reduce((acc, p) => acc + (p.valor || 0), 0);
  
  // Calcula o saldo total das contas
  const saldoTotal = Object.values(saldos).reduce((acc, val) => acc + (Number(val) || 0), 0);
  
  // Saldo projetado após pagamentos
  const saldoProjetado = saldoTotal - totalPagamentos;
  
  const dataHoje = new Date().toLocaleDateString('pt-BR');

  const formatCurrency = (val) => {
    return (val || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="relatorio-moderno-wrapper">
      <div className="relatorio-controls no-print">
        <button className="btn-voltar" onClick={onClose}>
          <ChevronLeft size={18} /> Voltar
        </button>
        <button className="btn-imprimir" onClick={handlePrint}>
          <Printer size={18} /> Imprimir / Salvar PDF
        </button>
      </div>

      <div className="relatorio-moderno-container print-area">
        <header className="relatorio-header">
          <div className="relatorio-branding">
            <div className="relatorio-logo">BOAH</div>
            <div className="relatorio-titles">
              <h1>Relatório Gerencial de Autorização</h1>
              <p>Posição Consolidada de Pagamentos</p>
            </div>
          </div>
          <div className="relatorio-meta">
            <div className="meta-item">
              <span className="meta-label">Data de Emissão</span>
              <span className="meta-value">{dataHoje}</span>
            </div>
            <div className="meta-item">
              <span className="meta-label">Registros</span>
              <span className="meta-value">{pagamentos.length}</span>
            </div>
          </div>
        </header>

        <section className="dashboard-financeiro">
          <div className="dash-card">
            <span className="dash-label">Saldo Atual Consolidado</span>
            <span className="dash-value positivo">{formatCurrency(saldoTotal)}</span>
            <div className="dash-sub">
              {Object.entries(saldos).map(([banco, valor], idx) => (
                <div key={idx} className="dash-sub-item">
                  <span>{banco}</span>
                  <span>{formatCurrency(Number(valor))}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="dash-card highlight-danger">
            <span className="dash-label">Total a Pagar (Aprovado)</span>
            <span className="dash-value negativo">- {formatCurrency(totalPagamentos)}</span>
            <div className="dash-sub">
              <div className="dash-sub-item">
                <span>Qtd. Lançamentos</span>
                <span>{pagamentos.length}</span>
              </div>
            </div>
          </div>
          <div className={`dash-card ${saldoProjetado >= 0 ? 'highlight-success' : 'highlight-danger'}`}>
            <span className="dash-label">Saldo Projetado Final</span>
            <span className={`dash-value ${saldoProjetado >= 0 ? 'positivo' : 'negativo'}`}>
              {formatCurrency(saldoProjetado)}
            </span>
            <div className="dash-sub">
              <div className="dash-sub-item">
                <span>Após baixa dos pagamentos</span>
              </div>
            </div>
          </div>
        </section>

        <section className="tabela-pagamentos-section">
          <h2>Detalhamento dos Lançamentos</h2>
          <table className="tabela-limpa">
            <thead>
              <tr>
                <th>Favorecido</th>
                <th>Descrição</th>
                <th>CNPJ/CPF</th>
                <th>Responsável</th>
                <th>Categoria</th>
                <th className="text-right">Valor (R$)</th>
              </tr>
            </thead>
            <tbody>
              {pagamentos.map((p, idx) => (
                <tr key={idx}>
                  <td>
                    <div className="fav-nome">{p.favorecido || p.nome}</div>
                  </td>
                  <td>
                    <div className="fav-desc">{p.descricao || ""}</div>
                  </td>
                  <td className="col-muted">{p.cnpj}</td>
                  <td><span className="badge-resp">{p.responsavel}</span></td>
                  <td className="col-muted">{p.categoria}</td>
                  <td className="text-right font-bold">{formatCurrency(p.valor)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan="5" className="text-right font-bold">TOTAL GERAL</td>
                <td className="text-right font-bold total-geral">{formatCurrency(totalPagamentos)}</td>
              </tr>
            </tfoot>
          </table>
        </section>
        
        <footer className="relatorio-footer">
          <div className="assinaturas">
            <div className="assinatura-box">
              <div className="assinatura-linha"></div>
              <span>Aprovado por (Diretoria)</span>
            </div>
            <div className="assinatura-box">
              <div className="assinatura-linha"></div>
              <span>Processado por (Financeiro)</span>
            </div>
          </div>
          <div className="footer-text">
            Gerado automaticamente pelo Sistema BOAH ERP
          </div>
        </footer>
      </div>
    </div>
  );
}
