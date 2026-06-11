import { useState } from 'react';
import './ImportacaoSmart.css';
import { Search, UploadCloud, FileText, CheckCircle, AlertCircle } from 'lucide-react';

export default function ImportacaoSmart() {
  const [arquivos, setArquivos] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [resultados, setResultados] = useState([]);
  
  const [chaveSefaz, setChaveSefaz] = useState('');
  const [buscandoSefaz, setBuscandoSefaz] = useState(false);

  const handleFileChange = (e) => {
    const files = Array.from(e.target.files);
    setArquivos(files);
  };

  const handleUpload = async () => {
    if (arquivos.length === 0) {
      alert("Selecione ao menos um arquivo (XML ou PDF).");
      return;
    }

    setUploading(true);
    setResultados([]);

    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      
      // Separar PDFs de XMLs
      const xmls = arquivos.filter(f => f.name.toLowerCase().endsWith('.xml'));
      const pdfs = arquivos.filter(f => f.name.toLowerCase().endsWith('.pdf'));

      let todosResultados = [];

      // Processar XMLs
      if (xmls.length > 0) {
        const formDataXml = new FormData();
        xmls.forEach(f => formDataXml.append('files', f));
        const res = await fetch(`${API_URL}/api/importar/xml`, { method: 'POST', body: formDataXml });
        const json = await res.json();
        if (json.resultados) todosResultados = [...todosResultados, ...json.resultados];
      }

      // Processar PDFs (Robô Inteligente)
      if (pdfs.length > 0) {
        const formDataPdf = new FormData();
        pdfs.forEach(f => formDataPdf.append('files', f));
        const res = await fetch(`${API_URL}/api/robo/importacao_inteligente`, { method: 'POST', body: formDataPdf });
        const json = await res.json();
        if (json.resultados) todosResultados = [...todosResultados, ...json.resultados];
      }
      
      setResultados(todosResultados);
      alert("Processamento em lote concluído!");
    } catch (err) {
      alert("Erro de conexão com o servidor ao importar arquivos.");
    }
    setUploading(false);
  };

  const handleSefazSearch = async () => {
    const cleanChave = chaveSefaz.replace(/\D/g, '');
    if (cleanChave.length !== 44) {
      alert("A Chave de Acesso deve conter exatos 44 números.");
      return;
    }

    setBuscandoSefaz(true);
    setResultados([]);

    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const res = await fetch(`${API_URL}/api/sefaz/consultar_chave`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chave: cleanChave })
      });
      const json = await res.json();
      
      if (json.success) {
        setResultados([{ arquivo: `SEFAZ: ${cleanChave}`, ok: true, mensagem: json.mensagem }]);
        alert("Sucesso! O Dossiê da Nota e Guias de Impostos foram provisionados.");
        setChaveSefaz('');
      } else {
        setResultados([{ arquivo: `SEFAZ: ${cleanChave}`, ok: false, mensagem: json.error }]);
      }
    } catch (err) {
      alert("Erro de conexão com a SEFAZ.");
    }
    setBuscandoSefaz(false);
  };

  return (
    <div className="import-container glass-panel">
      <div className="import-header">
        <h2>⚡ Central de Lançamentos</h2>
        <p className="text-muted">Motor autônomo para provisionamento. Importe notas ou baixe direto da SEFAZ Nacional via Certificado A1.</p>
      </div>

      <div className="launch-grid">
        {/* MÓDULO SEFAZ */}
        <div className="launch-card sefaz-card">
          <div className="card-header">
            <div className="icon-wrapper sefaz-icon"><Search size={24} /></div>
            <h3>Importação Oficial SEFAZ</h3>
          </div>
          <p className="card-desc">Cole a chave de 44 dígitos. O Hub fará o manifesto, o download do XML e provisionará todos os impostos automaticamente.</p>
          
          <div className="sefaz-input-group">
            <input 
              type="text" 
              placeholder="Digite os 44 números da Chave de Acesso" 
              value={chaveSefaz}
              onChange={(e) => setChaveSefaz(e.target.value)}
              className="input-chave"
              maxLength={54}
            />
            <button 
              className="btn-sefaz"
              onClick={handleSefazSearch}
              disabled={buscandoSefaz || chaveSefaz.length < 44}
            >
              {buscandoSefaz ? 'Conectando...' : 'Baixar da Sefaz'}
            </button>
          </div>
        </div>

        {/* MÓDULO DRAG & DROP */}
        <div className="launch-card drop-card">
          <div className="card-header">
            <div className="icon-wrapper drop-icon"><UploadCloud size={24} /></div>
            <h3>Lote Misto (XML / PDF)</h3>
          </div>
          <p className="card-desc">Arraste notas fiscais (XML) ou comprovantes de pagamento (PDF). O motor identificará o tipo de documento.</p>
          
          <div className="upload-box drop-zone" style={{ position: 'relative' }}>
            <input 
              type="file" 
              accept=".xml,.pdf" 
              multiple 
              onChange={handleFileChange} 
              className="file-input input-file-hidden"
            />
            <p>Arraste arquivos aqui ou <b>clique para buscar</b></p>
          </div>

          {arquivos.length > 0 && (
            <div className="files-list">
              <p className="files-count">{arquivos.length} arquivo(s) na fila:</p>
              <ul>
                {arquivos.slice(0, 3).map((f, idx) => (
                  <li key={idx}>
                    <FileText size={16} /> <span>{f.name}</span>
                  </li>
                ))}
                {arquivos.length > 3 && <li><span className="text-muted">... e mais {arquivos.length - 3} arquivo(s)</span></li>}
              </ul>
              <button 
                className="btn-importar" 
                onClick={handleUpload} 
                disabled={uploading}
              >
                {uploading ? 'Processando Lote...' : `Importar ${arquivos.length} Arquivo(s)`}
              </button>
            </div>
          )}
        </div>
      </div>

      {resultados.length > 0 && (
        <div className="resultados">
          <h3>Relatório de Execução</h3>
          <table>
            <thead>
              <tr>
                <th>Alvo / Arquivo</th>
                <th>Status</th>
                <th>Detalhes do Motor</th>
              </tr>
            </thead>
            <tbody>
              {resultados.map((r, idx) => (
                <tr key={idx} className={r.ok ? 'row-success' : 'row-error'}>
                  <td className="file-name">{r.arquivo}</td>
                  <td>
                    <span className={`badge ${r.ok ? 'badge-success' : 'badge-danger'}`}>
                      {r.ok ? <CheckCircle size={14} /> : <AlertCircle size={14} />}
                      {r.ok ? ' PROVISIONADO' : ' FALHA'}
                    </span>
                  </td>
                  <td>{r.mensagem}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
