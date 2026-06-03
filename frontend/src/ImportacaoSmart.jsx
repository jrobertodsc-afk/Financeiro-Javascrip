import { useState } from 'react';
import './ImportacaoSmart.css';

export default function ImportacaoSmart() {
  const [arquivos, setArquivos] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [resultados, setResultados] = useState([]);

  const handleFileChange = (e) => {
    const files = Array.from(e.target.files);
    setArquivos(files);
  };

  const handleUpload = async () => {
    if (arquivos.length === 0) {
      alert("Selecione ao menos um arquivo XML.");
      return;
    }

    setUploading(true);
    setResultados([]);

    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const formData = new FormData();
      arquivos.forEach(f => formData.append('files', f));

      const res = await fetch(`${API_URL}/api/importar/xml`, {
        method: 'POST',
        body: formData
      });
      const json = await res.json();
      
      if (json.success) {
        setResultados(json.resultados);
        alert(`${json.importados} arquivo(s) importado(s) com sucesso!`);
      } else {
        alert(`Erro: ${json.error}`);
      }
    } catch (err) {
      alert("Erro de conexão com o servidor.");
    }
    setUploading(false);
  };

  return (
    <div className="import-container glass-panel">
      <div className="import-header">
        <h2>⚡ Importação Smart</h2>
        <p className="text-muted">Arraste ou selecione arquivos XML de notas fiscais para importação automática em lote.</p>
      </div>

      <div className="upload-area">
        <div className="upload-box">
          <div className="upload-icon">📂</div>
          <p>Arraste arquivos XML aqui ou clique para selecionar</p>
          <input 
            type="file" 
            accept=".xml" 
            multiple 
            onChange={handleFileChange} 
            className="file-input"
          />
        </div>

        {arquivos.length > 0 && (
          <div className="files-list">
            <p className="files-count">{arquivos.length} arquivo(s) selecionado(s):</p>
            <ul>
              {arquivos.map((f, idx) => (
                <li key={idx}>
                  <span className="file-icon">📄</span>
                  <span>{f.name}</span>
                  <span className="file-size">{(f.size / 1024).toFixed(1)} KB</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <button 
          className="btn-importar" 
          onClick={handleUpload} 
          disabled={uploading || arquivos.length === 0}
        >
          {uploading ? 'Importando...' : `Importar ${arquivos.length} Arquivo(s)`}
        </button>
      </div>

      {resultados.length > 0 && (
        <div className="resultados">
          <h3>Resultados da Importação</h3>
          <table>
            <thead>
              <tr>
                <th>Arquivo</th>
                <th>Status</th>
                <th>Mensagem</th>
              </tr>
            </thead>
            <tbody>
              {resultados.map((r, idx) => (
                <tr key={idx}>
                  <td>{r.arquivo}</td>
                  <td>
                    <span className={`badge ${r.ok ? 'badge-success' : 'badge-danger'}`}>
                      {r.ok ? '✅ OK' : '❌ ERRO'}
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
