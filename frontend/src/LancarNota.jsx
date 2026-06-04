import { useState, useEffect } from 'react';
import './LancarNota.css';

const CATEGORIAS_PADRAO = [
  "111 - Custo Fixo - Desenvolvimento de Produto (Estilo)", "112 - Custo Fixo - Produção/Atelier",
  "21101 - Aluguel", "21102 - Condomínio", "21103 - Água E Esgoto", "21104 - Energia Elétrica",
  "21105 - Ar Condicionado", "21106 - Fundo de Promoção/Reserva", "21107 - Reembolso de Despesas Operacionais (Transporte, Alimentação Etc)",
  "21108 - Sindicato E Associacoes", "21109 - Seguros Loja/Imovel", "21110 - Gráficos Em Geral",
  "21111 - Serviços Advocatícios", "21112 - Serviços Contábeis", "21113 - Consultorias e Auditorias",
  "21114 - Telefonia Fixa/Internet", "21115 - Telefonia Móvel", "21117 - Seguro Geral",
  "21118 - Correios, Cartórios E Periódicos", "21119 - Consulta SPC / Serasa", "21120 - Sistemas e Softwares",
  "21121 - Domínios, Email e Site", "21201 - Copa e Cozinha", "21202 - Dedetização",
  "21203 - Recarga de Extintores", "21204 - Material de Escritório", "21205 - Material de Informática (Recargas e Tonners)",
  "21206 - Material de Limpeza", "21207 - Despesas com EPI", "21208 - Prestações de Serviços Operacionais",
  "21209 - Uso e Consumo Lojas (Copos, Comandas Etc)", "21301 - Combustível e Motoboy", "21302 - Estacionamento/Pedágio",
  "21303 - Licenciamento e Multas/IPVA Moto/Carro", "21304 - Manutenção - Moto/Carro", "21305 - Seguros - Moto/Carro",
  "21306 - Táxi/Uber (100030*2 por mês)", "12202 - Salários - Meis/PJ", "21401 - Salários", "21402 - Salários - Sócio/PJ",
  "21403 - Pró-labore", "21404 - Transportes", "21405 - Alimentação", "21406 - FGTS",
  "21407 - INSS", "21408 - IRRF - Imposto de Renda PJ (Verificar %)", "21409 - Férias",
  "21410 - Rescisão", "21411 - Multa de FGTS", "21412 - Domingos e Feriados Trabalhados",
  "21413 - Cursos e Treinamentos", "21414 - Exames Clínicos (Dem/Adm/Ret)", "21415 - Despesas com Estágio",
  "21416 - 13º salário", "21417 - Sindicatos", "21418 - Faltas", "21419 - Fardamento",
  "21420 - ISS Substituto Tributario", "21501 - Manutenção - Predial", "21502 - Manutenção - Elétrica",
  "21503 - Manutenção - Informática", "21504 - Manutenção - Máquinas e Equipamentos", "21505 - Manutenção - Refrigeração/Ar-condicionado",
  "21506 - Manutenção - Mobiliário/Decoração", "21601 - Tarifas Bancárias", "21602 - Aluguel de Maquinetas",
  "21603 - Taxa de Juros Cartões/Pix/Boletos", "21701 - Comunicação/Mídia Digital - Despesas Operacionais (Facebook/Insta...)", "21702 - Relacionamento com o Cliente - Ações (Distribuição de Mimos/Sorteios/Etc)",
  "21703 - Marketing de Influência - Blogueiras/Influencers (Tons/Permutas)", "21704 - Lookbook (1 Por Ano)", "21705 - Editorial para Campanha (4 Por Ano)",
  "21706 - Visual Merchandising - Decoração, Ambientação, Vitrines", "21707 - Material Gráfico", "21801 - Endomarketing",
  "21901 - IPTU", "21902 - Taxas Municipais", "21903 - Taxas Estaduais", "31101 - Tecidos",
  "31102 - Aviamentos", "31103 - Insumos Gerais (produção)", "31104 - Produtos Revenda",
  "31105 - Embalagens", "31106 - Sacolas", "31107 - Etiquetas - Viagem/Acessórios",
  "31108 - Lacres", "31109 - Prestação de Serviço - Corte", "31110 - Faccionista - Conserto",
  "31111 - Faccionista - Mão de Obra", "31112 - Frete/Transporte - Produção", "31113 - Faccionista - Confecção de Pilotos",
  "32101 - Bonificação / Premiação", "32102 - Comissões", "32201 - Entregas On-line",
  "32202 - Entregas Atacado", "32203 - Plataforma de Vendas On-Line", "32204 - Devolução de Vendas",
  "32205 - Aluguel Percentual", "32206 - Embalagens (Sacolas, Envelopes e Papel Seda)", "32207 - Ações Comerciais",
  "32601 - Juros Cheque Especial / IOF", "32602 - Juros por Atraso de Pagamentos", "32701 - Contrato de Mutuo - Débito",
  "33301 - ICMS", "33302 - ICMS Substituição Tributária", "33303 - ICMS Antecipacao Parcial",
  "33304 - PIS (0620)", "33305 - COFINS (2172)", "33306 - IRPJ (2089)",
  "33307 - CSLL (2372)", "33308 - Simples Nacional", "33309 - DARE",
  "33401 - Investimento - Predial", "33402 - Investimento - Informática", "33403 - Investimento - Elétrica",
  "33404 - Investimento - Máquinas e Equipamentos", "33405 - Investimento - Refrigeração/Ar-condicionado", "33406 - Investimento - Mobiliário/Decoração",
  "33407 - Investimento - Consultorias e Prestações de Serviços", "33408 - Investimento - Marcas e Patentes", "33409 - Investimento - Novas Unidades (Custos com novas lojas Boah)",
  "33410 - Investimento - Novas Unidades (Custos com novas lojas Solar)", "33501 - Retirada de Sócios",
  "TRANSFERENCIA", "A CLASSIFICAR"
];

const RESPONSAVEIS_PADRAO = [
  "ADM/FINANCEIRO", "COMPRAS", "GERENTE ONLINE", "LOGISTICA",
  "MARKETING", "PRODUCAO", "RH", "SUPRIMENTOS", "GERÊNCIA LOJA"
];
export default function LancarNota({ editNotaId, onClearEdit }) {
  const [chave, setChave] = useState('');
  const [loadingSefaz, setLoadingSefaz] = useState(false);
  const [sefazMessage, setSefazMessage] = useState('');
  const [isSuccessSefaz, setIsSuccessSefaz] = useState(false);

  // Form Fields - SESSÃO 1
  const [fornecedor, setFornecedor] = useState('');
  const [cnpj, setCnpj] = useState('');
  const [empresa, setEmpresa] = useState('LALUA');
  const [filial, setFilial] = useState('LALUA MATRIZ');
  const [categoria, setCategoria] = useState('');
  const [natureza, setNatureza] = useState('COMPRA DE MERCADORIA');
  const [responsavel, setResponsavel] = useState('');
  const [descricao, setDescricao] = useState('');
  const [numeroNf, setNumeroNf] = useState('');
  
  // SESSÃO 2
  const [dtEmissao, setDtEmissao] = useState(new Date().toISOString().split('T')[0]);
  const [dtVencimento, setDtVencimento] = useState(new Date().toISOString().split('T')[0]);
  const [valorBruto, setValorBruto] = useState('0,00');
  const [difal, setDifal] = useState('0,00');
  const [fcp, setFcp] = useState('0,00');
  const [chaveRef, setChaveRef] = useState('');

  // SESSÃO 3
  const [observacao, setObservacao] = useState('');
  const [codBarras, setCodBarras] = useState('');
  const [isPrevisao, setIsPrevisao] = useState(false);
  const [isRecorrente, setIsRecorrente] = useState(false);
  const [mesesRecorrencia, setMesesRecorrencia] = useState(12);
  const [formaPgto, setFormaPgto] = useState('BOLETO');
  
  // PIX
  const [pixTipo, setPixTipo] = useState('CNPJ');
  const [pixChave, setPixChave] = useState('');
  
  // TED
  const [bancoDest, setBancoDest] = useState('');
  const [agDest, setAgDest] = useState('');
  const [contaDest, setContaDest] = useState('');
  const [cpfCnpjDest, setCpfCnpjDest] = useState('');

  // RATEIOS (Itens)
  const [itens, setItens] = useState([{ id: 1, descricao: '', centroCusto: '', valor: '0,00' }]);

  // IMPOSTOS RETIDOS
  const [impostos, setImpostos] = useState([
    { tipo: 'IRRF', retido: false, aliquota: '1,50', valor: '0,00', vencimento: '' },
    { tipo: 'PIS', retido: false, aliquota: '0,65', valor: '0,00', vencimento: '' },
    { tipo: 'COFINS', retido: false, aliquota: '3,00', valor: '0,00', vencimento: '' },
    { tipo: 'CSLL', retido: false, aliquota: '1,00', valor: '0,00', vencimento: '' },
    { tipo: 'INSS', retido: false, aliquota: '11,00', valor: '0,00', vencimento: '' },
    { tipo: 'ISS', retido: false, aliquota: '5,00', valor: '0,00', vencimento: '' }
  ]);

  const [saving, setSaving] = useState(false);
  const [numeroTx, setNumeroTx] = useState('');

  // Carregar dados se editNotaId estiver presente
  useEffect(() => {
    if (!editNotaId) {
      // Limpa os estados se não estiver editando (apenas se mudou)
      if (numeroTx) {
         setFornecedor(''); setCnpj(''); setResponsavel(''); setDescricao(''); setNumeroNf('');
         setCodBarras(''); setValorBruto('0,00'); setNumeroTx('');
      }
      return;
    }
    
    const fetchEditData = async () => {
      try {
        const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        const res = await fetch(`${API_URL}/api/nota/${editNotaId}`);
        const json = await res.json();
        if (json.success) {
          const n = json.nota;
          
          setNumeroTx(n.numero_tx || '');
          setFornecedor(n.fornecedor || '');
          setCnpj(n.cnpj || '');
          setEmpresa(n.empresa || 'LALUA');
          setFilial(n.filial || '');
          setCategoria(n.categoria || '');
          setNatureza(n.natureza || 'COMPRA DE MERCADORIA');
          setResponsavel(n.responsavel || '');
          setDescricao(n.descricao || '');
          setNumeroNf(n.numero_nf || '');
          
          if (n.dt_emissao) {
            const parts = n.dt_emissao.split('/');
            if(parts.length === 3) setDtEmissao(`${parts[2]}-${parts[1]}-${parts[0]}`);
          }
          if (n.dt_vencimento) {
            const parts = n.dt_vencimento.split('/');
            if(parts.length === 3) setDtVencimento(`${parts[2]}-${parts[1]}-${parts[0]}`);
          }
          
          // Reverte a lógica de valor bruto (no backend o valor bruto salvo é descontado, 
          // mas vamos assumir que queremos mostrar o valor bruto + impostos retidos como original)
          // Na verdade, o banco de dados tem valor_bruto.
          const totalRet = (n.impostos || []).reduce((acc, curr) => acc + (parseFloat(curr.valor) || 0), 0);
          setValorBruto(applyMoneyMask(((n.valor_bruto || 0) + totalRet).toFixed(2)));
          
          setDifal(applyMoneyMask((n.valor_difal || 0).toFixed(2)));
          setChaveRef(n.chave_ref || '');
          setObservacao(n.observacao || '');
          setCodBarras(n.cod_barras || '');
          setIsPrevisao(n.is_previsao === 1);
          setIsRecorrente(n.recorrente === 1);
          setFormaPgto(n.forma_pgto || 'BOLETO');
          setPixChave(n.pix_chave || '');
          setBancoDest(n.banco_dest || '');
          setAgDest(n.agencia_dest || '');
          setContaDest(n.conta_dest || '');
          setCpfCnpjDest(n.cpf_cnpj_dest || '');

          if (n.rateio && n.rateio.length > 0) {
            setItens(n.rateio.map((r, i) => ({
              id: Date.now() + i,
              descricao: n.itens && n.itens[i] ? n.itens[i].descricao : '',
              centroCusto: r.centro_custo || r.filial || '',
              valor: applyMoneyMask((r.valor || 0).toFixed(2))
            })));
          }

          if (n.impostos && n.impostos.length > 0) {
            const loadedImpostos = impostos.map(imp => {
              const found = n.impostos.find(x => x.tipo === imp.tipo);
              if (found) {
                return {
                  ...imp,
                  retido: true,
                  aliquota: applyMoneyMask((found.aliquota || 0).toFixed(2)),
                  valor: applyMoneyMask((found.valor || 0).toFixed(2)),
                  vencimento: found.dt_venc_imp ? found.dt_venc_imp.split('/').reverse().join('-') : ''
                };
              }
              return imp;
            });
            setImpostos(loadedImpostos);
          }
        }
      } catch (err) {
        console.error("Erro ao carregar nota para edição:", err);
      }
    };
    fetchEditData();
  }, [editNotaId]);

  const consultarSefaz = async () => {
    if (!chave || chave.length !== 44) {
      setSefazMessage("⚠️ A chave de acesso deve ter 44 dígitos.");
      setIsSuccessSefaz(false);
      return;
    }
    setLoadingSefaz(true);
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const res = await fetch(`${API_URL}/api/sefaz/consultar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chave })
      });
      const json = await res.json();
      
      if (json.success) {
        setIsSuccessSefaz(true);
        setSefazMessage(`Chave válida — NF ${json.info.num_nf} | CNPJ ${json.info.cnpj}`);
        setCnpj(json.info.cnpj);
        setDescricao(`NF ${json.info.num_nf}`);
        setNumeroNf(json.info.num_nf);
        
        if (json.info.razao_social) setFornecedor(json.info.razao_social);
        if (json.info.categoria) setCategoria(json.info.categoria);
      } else {
        setIsSuccessSefaz(false);
        setSefazMessage(`⚠️ ${json.error}`);
      }
    } catch (err) {
      setIsSuccessSefaz(false);
      setSefazMessage(`⚠️ Erro de conexão com o servidor.`);
    }
    setLoadingSefaz(false);
  };

  const parseMoney = (val) => {
    const f = parseFloat(String(val).replace(/\./g, '').replace(',', '.'));
    return isNaN(f) ? 0 : f;
  };

  const applyMoneyMask = (value) => {
    let v = String(value).replace(/\D/g, '');
    if (!v) return '0,00';
    v = (parseInt(v, 10) / 100).toFixed(2);
    v = v.replace('.', ',');
    v = v.replace(/(\d)(?=(\d{3})+(?!\d))/g, '$1.');
    return v;
  };

  const formatMoneyDisplay = (val) => {
    return val.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  };

  const addItem = () => setItens([...itens, { id: Date.now(), descricao: '', centroCusto: '', valor: '0,00' }]);
  const removeItem = (id) => setItens(itens.filter(i => i.id !== id));
  const updateItem = (id, field, value) => {
    setItens(itens.map(i => {
      if (i.id === id) {
        return { ...i, [field]: field === 'valor' ? applyMoneyMask(value) : value };
      }
      return i;
    }));
  };

  const updateImposto = (index, field, value) => {
    const newImpostos = [...impostos];
    newImpostos[index][field] = field === 'valor' || field === 'aliquota' ? applyMoneyMask(value) : value;
    
    // Auto-calcula o valor ao marcar como retido
    if (field === 'retido' && value === true) {
      const vBruto = parseMoney(valorBruto);
      const aliq = parseMoney(newImpostos[index].aliquota);
      const calcVal = vBruto * (aliq / 100);
      newImpostos[index].valor = applyMoneyMask(Math.round(calcVal * 100).toString());
      
      if (!newImpostos[index].vencimento) {
        newImpostos[index].vencimento = dtVencimento;
      }
    }
    setImpostos(newImpostos);
  };

  const calcularTotalRetido = () => {
    return impostos.filter(i => i.retido).reduce((acc, curr) => acc + parseMoney(curr.valor), 0);
  };

  const totalRetido = calcularTotalRetido();
  const vBrutoNum = parseMoney(valorBruto);
  const valorLiquido = vBrutoNum - totalRetido;
  
  const somaItens = itens.reduce((acc, curr) => acc + parseMoney(curr.valor), 0);
  const diffRateio = Math.abs(somaItens - vBrutoNum);

  // Formata a data de YYYY-MM-DD para DD/MM/YYYY antes de enviar para o backend
  const formatDateBR = (isoDate) => {
    if (!isoDate) return '';
    const parts = isoDate.split('-');
    if (parts.length === 3) return `${parts[2]}/${parts[1]}/${parts[0]}`;
    return isoDate;
  };

  const salvarNota = async (e) => {
    e.preventDefault();
    setSaving(true);

    const payload = {
      dados_base: {
        id: editNotaId || undefined,
        numero_tx: numeroTx || undefined,
        chave_acesso: chave,
        fornecedor: fornecedor,
        cnpj: cnpj,
        empresa: empresa,
        filial: filial,
        categoria: categoria,
        natureza: natureza,
        responsavel: responsavel,
        descricao: descricao,
        numero_nf: numeroNf,
        dt_emissao: formatDateBR(dtEmissao),
        dt_vencimento: formatDateBR(dtVencimento),
        valor_bruto: vBrutoNum,
        valor_difal: parseMoney(difal),
        chave_ref: chaveRef,
        observacao: observacao,
        cod_barras: codBarras,
        forma_pgto: formaPgto,
        pix_chave: pixChave,
        banco_dest: bancoDest,
        agencia_dest: agDest,
        conta_dest: contaDest,
        cpf_cnpj_dest: cpfCnpjDest,
        status: "PENDENTE",
        is_previsao: isPrevisao ? 1 : 0,
        recorrente: isRecorrente ? 1 : 0,
        meses_recorrencia: isRecorrente ? parseInt(mesesRecorrencia) : 1
      },
      impostos: impostos.filter(i => i.retido).map(i => ({
        tipo: i.tipo,
        aliquota: parseMoney(i.aliquota),
        valor: parseMoney(i.valor),
        dt_venc_imp: formatDateBR(i.vencimento)
      })),
      parcelas: [],
      rateio: itens.map(i => ({
        centro_custo: i.centroCusto || 'Geral',
        valor: parseMoney(i.valor)
      })),
      itens: itens.map(i => ({
        descricao: i.descricao,
        valor_total: parseMoney(i.valor)
      }))
    };

    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const res = await fetch(`${API_URL}/api/salvar_nota`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const json = await res.json();
      
      if (json.success) {
        alert(editNotaId ? "Nota/Despesa atualizada com sucesso!" : "Nota/Despesa salva com sucesso!");
        if (onClearEdit) onClearEdit();
        
        // Reset parcial pós salvamento, para facilitar digitação continuada
        setDescricao('');
        setNumeroNf('');
        setCodBarras('');
        setValorBruto('0,00');
        setItens([{ id: 1, descricao: '', centroCusto: '', valor: '0,00' }]);
      } else {
        alert(`Erro ao salvar: ${json.error}`);
      }
    } catch (err) {
      alert(`Erro de conexão com o servidor.`);
    }
    setSaving(false);
  };

  return (
    <div className="lancar-container glass-panel">
      <div className="lancar-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2>{editNotaId ? '✏️ Editar Nota / Despesa' : '✨ Nova Nota / Despesa Completa'}</h2>
          <p className="text-muted">{editNotaId ? `Editando registro #${editNotaId}` : 'Preencha as informações para registro contábil e financeiro.'}</p>
        </div>
        {editNotaId && (
          <button type="button" onClick={onClearEdit} className="btn-cancel" style={{ padding: '8px 16px', background: 'var(--surface-raised)', border: '1px solid var(--border-color)', borderRadius: '4px', color: '#fff', cursor: 'pointer' }}>
            Cancelar Edição
          </button>
        )}
      </div>

      <div className="sefaz-box">
        <label>Chave de Acesso Sefaz (Opcional):</label>
        <div className="sefaz-input-row">
          <input type="text" placeholder="Cole a Chave de 44 dígitos..." value={chave} onChange={(e) => setChave(e.target.value.replace(/\D/g, ''))} maxLength={44} />
          <button type="button" className="btn-sefaz" onClick={consultarSefaz} disabled={loadingSefaz}>
            {loadingSefaz ? 'Consultando...' : 'Consultar SEFAZ'}
          </button>
        </div>
        {sefazMessage && <p className={`sefaz-message ${isSuccessSefaz ? 'success' : 'error'}`}>{sefazMessage}</p>}
      </div>

      <form className="nota-form" onSubmit={salvarNota}>
        
        {/* Adicionado Datalist para reaproveitamento e facilidade de digitação */}
        <datalist id="list-categorias">
          {CATEGORIAS_PADRAO.map(c => <option key={c} value={c} />)}
        </datalist>
        <datalist id="list-responsaveis">
          {RESPONSAVEIS_PADRAO.map(r => <option key={r} value={r} />)}
        </datalist>

        <h3 className="section-title">🏢 Dados Básicos</h3>
        <div className="form-grid">
          <div className="form-group span-2">
            <label>Fornecedor</label>
            <input type="text" required value={fornecedor} onChange={e => setFornecedor(e.target.value)} />
          </div>
          <div className="form-group">
            <label>CNPJ / CPF</label>
            <input type="text" required value={cnpj} onChange={e => setCnpj(e.target.value)} />
          </div>

          <div className="form-group">
            <label>Empresa</label>
            <select value={empresa} onChange={e => {
              setEmpresa(e.target.value);
              setFilial(e.target.value === 'LALUA' ? 'LALUA MATRIZ' : 'SOLAR MATRIZ');
            }}>
              <option value="LALUA">LALUA</option>
              <option value="SOLAR">SOLAR</option>
            </select>
          </div>
          <div className="form-group">
            <label>Filial</label>
            <select value={filial} onChange={e => setFilial(e.target.value)}>
              {empresa === 'LALUA' ? (
                <>
                  <option>LALUA MATRIZ</option>
                  <option>BOAH BARRA</option>
                  <option>PASEO</option>
                  <option>VILAS</option>
                  <option>SDB</option>
                  <option>HORTO</option>
                  <option>ONLINE</option>
                </>
              ) : (
                <option>SOLAR MATRIZ</option>
              )}
            </select>
          </div>
          <div className="form-group">
            <label>Categoria</label>
            <input type="text" list="list-categorias" value={categoria} onChange={e => setCategoria(e.target.value)} />
          </div>

          <div className="form-group">
            <label>Natureza / Tipo</label>
            <select value={natureza} onChange={e => setNatureza(e.target.value)}>
              <option value="COMPRA DE MERCADORIA">COMPRA DE MERCADORIA</option>
              <option value="SERVIÇO">SERVIÇO</option>
              <option value="DESPESA FIXA">DESPESA FIXA</option>
              <option value="IMPOSTO">IMPOSTO</option>
              <option value="FOLHA DE PAGAMENTO">FOLHA DE PAGAMENTO</option>
              <option value="INVESTIMENTO">INVESTIMENTO</option>
            </select>
          </div>
          <div className="form-group span-2">
            <label>Responsável / Setor</label>
            <input type="text" list="list-responsaveis" value={responsavel} onChange={e => setResponsavel(e.target.value)} />
          </div>

          <div className="form-group span-2">
            <label>Descrição / Referência</label>
            <input type="text" required value={descricao} onChange={e => setDescricao(e.target.value)} />
          </div>
          <div className="form-group">
            <label>Nº NF / Documento</label>
            <input type="text" value={numeroNf} onChange={e => setNumeroNf(e.target.value)} />
          </div>
        </div>

        <div className="valores-dashboard">
          <div className="valor-card bruto">
            <span>Valor Bruto (Original)</span>
            <h3>{formatMoneyDisplay(vBrutoNum)}</h3>
          </div>
          <div className="valor-card retido">
            <span>Impostos Retidos</span>
            <h3>- {formatMoneyDisplay(totalRetido)}</h3>
          </div>
          <div className="valor-card liquido">
            <span>Valor Líquido (A Pagar)</span>
            <h3>{formatMoneyDisplay(valorLiquido)}</h3>
          </div>
        </div>

        <h3 className="section-title" style={{ marginTop: '32px' }}>💰 Valores e Datas</h3>
        <div className="form-grid">
          <div className="form-group">
            <label>Emissão</label>
            <input type="date" required value={dtEmissao} onChange={e => setDtEmissao(e.target.value)} />
          </div>
          <div className="form-group">
            <label>Vencimento</label>
            <input type="date" required value={dtVencimento} onChange={e => setDtVencimento(e.target.value)} />
          </div>
          <div className="form-group">
            <label>Valor Bruto (R$)</label>
            <input type="text" required value={valorBruto} onChange={e => setValorBruto(applyMoneyMask(e.target.value))} className="font-bold text-accent text-right" />
          </div>
        </div>

        {/* COMPONENTE DE ITENS (RATEIO) */}
        <div className="rateio-section">
          <div className="rateio-header">
            <label>🛒 Itens da Nota / Serviço (Rateio por Centro de Custo)</label>
            {diffRateio > 0.01 && (
              <span className="rateio-warning">⚠️ Diferença de {formatMoneyDisplay(diffRateio)} entre rateio e valor bruto.</span>
            )}
            {diffRateio <= 0.01 && vBrutoNum > 0 && (
              <span className="rateio-success">✅ Rateio bate com valor bruto.</span>
            )}
          </div>
          {itens.map((item, idx) => (
            <div className="rateio-row" key={item.id}>
              <input type="text" placeholder="Centro de Custo (Ex: TI, Marketing)" value={item.centroCusto} onChange={e => updateItem(item.id, 'centroCusto', e.target.value)} />
              <input type="text" placeholder="Descrição do Item / Despesa" value={item.descricao} onChange={e => updateItem(item.id, 'descricao', e.target.value)} />
              <input type="text" className="money-input" placeholder="0,00" value={item.valor} onChange={e => updateItem(item.id, 'valor', e.target.value)} />
              <button type="button" className="btn-remove" onClick={() => removeItem(item.id)}>X</button>
            </div>
          ))}
          <button type="button" onClick={addItem} className="btn-add-item">+ Adicionar Centro de Custo</button>
        </div>

        {/* COMPONENTE DE IMPOSTOS RETIDOS */}
        <div className="impostos-section">
          <label className="impostos-title">🏛️ Impostos Retidos (Cálculo Automático)</label>
          <div className="impostos-grid">
            {impostos.map((imp, idx) => (
              <div key={imp.tipo} className="imposto-row">
                <input type="checkbox" checked={imp.retido} onChange={e => updateImposto(idx, 'retido', e.target.checked)} />
                <span className="imposto-label">{imp.tipo}</span>
                <input type="text" placeholder="Aliq %" value={imp.aliquota} onChange={e => updateImposto(idx, 'aliquota', e.target.value)} disabled={!imp.retido} className="imposto-input-sm" />
                <input type="text" placeholder="R$ Valor" value={imp.valor} onChange={e => updateImposto(idx, 'valor', e.target.value)} disabled={!imp.retido} className="imposto-input-md" />
                <input type="date" placeholder="Vencimento" value={imp.vencimento} onChange={e => updateImposto(idx, 'vencimento', e.target.value)} disabled={!imp.retido} className="imposto-input-lg" />
              </div>
            ))}
          </div>
        </div>

        <h3 className="section-title" style={{ marginTop: '32px' }}>💳 Pagamento e Opções Adicionais</h3>
        <div className="form-grid">
          <div className="form-group">
            <label>Forma de Pagamento</label>
            <select value={formaPgto} onChange={e => setFormaPgto(e.target.value)}>
              <option value="BOLETO">BOLETO</option>
              <option value="PIX">PIX</option>
              <option value="TED">TED</option>
              <option value="DARF">DARF</option>
              <option value="GPS">GPS</option>
            </select>
          </div>
          <div className="form-group span-2">
            <label>Cód. Barras (Bipe com pistola)</label>
            <input type="text" value={codBarras} onChange={e => setCodBarras(e.target.value)} style={{ fontFamily: 'monospace', color: 'var(--accent-color)' }} />
          </div>

          {formaPgto === 'PIX' && (
            <>
              <div className="form-group">
                <label>Tipo Chave PIX</label>
                <select value={pixTipo} onChange={e => setPixTipo(e.target.value)}>
                  <option value="CNPJ">CNPJ / CPF</option>
                  <option value="TELEFONE">TELEFONE</option>
                  <option value="EMAIL">EMAIL</option>
                  <option value="ALEATÓRIA">ALEATÓRIA</option>
                </select>
              </div>
              <div className="form-group span-2">
                <label>Chave PIX</label>
                <input type="text" value={pixChave} onChange={e => setPixChave(e.target.value)} />
              </div>
            </>
          )}

          {formaPgto === 'TED' && (
            <>
              <div className="form-group span-3" style={{ display: 'flex', gap: '16px' }}>
                <div style={{ flex: 1 }}><label style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Banco</label><input style={{ width: '100%', padding: '8px', background: 'var(--bg-color)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: '4px' }} type="text" value={bancoDest} onChange={e => setBancoDest(e.target.value)} /></div>
                <div style={{ flex: 1 }}><label style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Agência</label><input style={{ width: '100%', padding: '8px', background: 'var(--bg-color)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: '4px' }} type="text" value={agDest} onChange={e => setAgDest(e.target.value)} /></div>
                <div style={{ flex: 1 }}><label style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Conta</label><input style={{ width: '100%', padding: '8px', background: 'var(--bg-color)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: '4px' }} type="text" value={contaDest} onChange={e => setContaDest(e.target.value)} /></div>
                <div style={{ flex: 1 }}><label style={{ fontSize: '13px', color: 'var(--text-muted)' }}>CPF/CNPJ Dest</label><input style={{ width: '100%', padding: '8px', background: 'var(--bg-color)', border: '1px solid var(--border-color)', color: '#fff', borderRadius: '4px' }} type="text" value={cpfCnpjDest} onChange={e => setCpfCnpjDest(e.target.value)} /></div>
              </div>
            </>
          )}
          
          <div className="form-group">
             <label>DIFAL (Opcional)</label>
             <input type="text" value={difal} onChange={e => setDifal(applyMoneyMask(e.target.value))} className="text-right" />
          </div>
          <div className="form-group">
             <label>FCP (Opcional)</label>
             <input type="text" value={fcp} onChange={e => setFcp(applyMoneyMask(e.target.value))} className="text-right" />
          </div>
          <div className="form-group">
             <label>Chave Ref / Transação</label>
             <input type="text" value={chaveRef} onChange={e => setChaveRef(e.target.value)} />
          </div>

          <div className="form-group span-3">
            <label>Observação</label>
            <input type="text" value={observacao} onChange={e => setObservacao(e.target.value)} />
          </div>
          
          <div className="form-group span-3" style={{ display: 'flex', alignItems: 'center', marginTop: '16px', padding: '16px', border: '1px dashed var(--warning)', borderRadius: '8px' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer', margin: 0 }}>
              <input type="checkbox" checked={isPrevisao} onChange={e => setIsPrevisao(e.target.checked)} style={{ width: '20px', height: '20px', cursor: 'pointer' }} />
              <span style={{ fontSize: '16px', fontWeight: 'bold', color: 'var(--warning)' }}>🔮 Lançar como Previsão Financeira (Sem Nota / Provisão)</span>
            </label>
          </div>

          <div className="form-group span-3" style={{ display: 'flex', alignItems: 'center', marginTop: '8px', padding: '16px', border: '1px dashed var(--accent-color)', borderRadius: '8px' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer', margin: 0 }}>
              <input type="checkbox" checked={isRecorrente} onChange={e => setIsRecorrente(e.target.checked)} style={{ width: '20px', height: '20px', cursor: 'pointer' }} />
              <span style={{ fontSize: '16px', fontWeight: 'bold', color: 'var(--accent-color)' }}>🔄 Lançar Recorrente (Criar cópias futuras automaticamente)</span>
            </label>
            {isRecorrente && (
               <div style={{marginLeft: '24px', display: 'flex', alignItems: 'center', gap: '12px'}}>
                 <label style={{margin:0, color:'var(--text-primary)', fontSize: '14px', fontWeight: '500'}}>Por quantos meses?</label>
                 <input type="number" min="2" max="120" value={mesesRecorrencia} onChange={e => setMesesRecorrencia(e.target.value)} style={{width: '90px', padding: '8px'}}/>
               </div>
            )}
          </div>
        </div>

        <div className="form-footer">
          <button type="submit" className="btn-salvar" disabled={saving}>
            {saving ? 'Salvando...' : 'Salvar Nota / Despesa'}
          </button>
        </div>
      </form>
    </div>
  );
}
