import os
from datetime import datetime
from collections import defaultdict
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

def gerar_pdf_autorizacao(pagamentos: list) -> str:
    """Gera o PDF de autorização de pagamentos no estilo BOAH."""
    empresas = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for p in pagamentos:
        emp  = p.get("empresa", "LALUA")
        data = p.get("data", "")
        tipo = p.get("tipo", "Outros")
        empresas[emp][data][tipo].append(p)

    ORDEM_TIPO = [
        "Boleto Itaú", "Boleto outros bancos", "Boletos ouros bancos",
        "Concessionária", "Tributos com código de barras",
        "DARF código de barras", "DAS código barras",
        "IPTU/ISS e outros tributos",
        "PIX Transferências", "Pix Transferencia",
        "PIX Qr Code", "TED",
        "Folha de pagamento", "Folha de pagamentos", "Outros",
    ]

    import os
    
    # Pasta de histórico
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    historico_dir = os.path.join(base_dir, "data", "historico_autorizacoes")
    os.makedirs(historico_dir, exist_ok=True)
    
    data_hoje = datetime.now().strftime("%d_%m_%Y_%H%M%S")
    nome_arq  = f"AUTORIZACAO_PAGAMENTOS_{data_hoje}.pdf"
    caminho_pdf = os.path.join(historico_dir, nome_arq)

    PAGE = landscape(A4)
    doc = SimpleDocTemplate(
        caminho_pdf,
        pagesize=PAGE,
        leftMargin=1*cm, rightMargin=1*cm,
        topMargin=1.5*cm, bottomMargin=1*cm
    )

    styles = getSampleStyleSheet()
    styleH = ParagraphStyle('Header', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=14)
    styleN = ParagraphStyle('Normal_Center', parent=styles['Normal'], alignment=TA_CENTER)
    styleR = ParagraphStyle('Normal_Right', parent=styles['Normal'], alignment=TA_RIGHT)
    
    styleTitleLeft = ParagraphStyle(
        'TitleLeft', fontName='Helvetica-Bold', fontSize=24, spaceAfter=10
    )
    styleTitleRight = ParagraphStyle(
        'TitleRight', fontName='Helvetica-Bold', fontSize=10, alignment=TA_RIGHT, textColor=colors.HexColor("#333333")
    )
    styleSubtitleRight = ParagraphStyle(
        'SubtitleRight', fontName='Helvetica', fontSize=8, alignment=TA_RIGHT, textColor=colors.HexColor("#555555")
    )

    elements = []

    # --- CABEÇALHO BOAH ---
    t_header = Table([
        [Paragraph("BOAH", styleTitleLeft), 
         [Paragraph("AUTORIZAÇÃO DE PAGAMENTOS", styleTitleRight),
          Paragraph("LALUA COMERCIO DE MODAS LTDA · SOLAR SERVIÇOS DE APOIO ADMIN", styleSubtitleRight)]]
    ], colWidths=[10*cm, PAGE[0] - 12*cm])
    
    t_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))
    
    elements.append(t_header)
    elements.append(Spacer(1, 0.5*cm))

    # --- CORPO ---
    cor_texto = colors.HexColor("#111111")
    cor_fundo_th = colors.HexColor("#111111")
    cor_txt_th   = colors.HexColor("#FFFFFF")
    
    # 3. Itera Empresas -> Datas -> Tipos
    for emp in sorted(empresas.keys()):
        for data_ in sorted(empresas[emp].keys()):
            # Adiciona quebra apenas visual para cada dia
            total_dia = 0.0
            tabela_dados = []
            
            # CABEÇALHO DO BLOCO DA EMPRESA/DATA
            tabela_dados.append([
                Paragraph(f"<b>{emp}</b>", ParagraphStyle('', textColor=cor_txt_th, fontName='Helvetica-Bold', fontSize=9)),
                "", "", "", "",
                Paragraph(f"<b>{data_}</b>", ParagraphStyle('', textColor=cor_txt_th, fontName='Helvetica-Bold', alignment=TA_RIGHT, fontSize=9))
            ])
            tabela_dados.append([
                "Favorecido / Beneficiário", "CPF/CNPJ", "Data", "Valor (R$)", "Responsável", "Categoria", "Descrição"
            ])

            for tipo_esperado in ORDEM_TIPO:
                if tipo_esperado in empresas[emp][data_]:
                    lista_tipo = empresas[emp][data_][tipo_esperado]
                    soma_tipo = sum(float(i.get("valor", 0)) for i in lista_tipo)
                    total_dia += soma_tipo
                    
                    for row_idx, item in enumerate(lista_tipo):
                        nome = item.get("favorecido") or item.get("nome") or ""
                        val  = float(item.get("valor", 0))
                        
                        tabela_dados.append([
                            Paragraph(nome[:50], ParagraphStyle('', fontSize=7)),
                            Paragraph(item.get("cnpj",""), ParagraphStyle('', fontSize=7)),
                            Paragraph(item.get("data",""), ParagraphStyle('', fontSize=7)),
                            Paragraph(f"<b>R$ {val:,.2f}</b>", ParagraphStyle('', fontSize=7)),
                            Paragraph(item.get("responsavel",""), ParagraphStyle('', fontSize=7)),
                            Paragraph(item.get("categoria",""), ParagraphStyle('', fontSize=7)),
                            Paragraph(item.get("descricao") or item.get("detalhes") or "", ParagraphStyle('', fontSize=7))
                        ])
                    
                    # LINHA SUBTOTAL TIPO
                    tabela_dados.append([
                        Paragraph(f"<b>{tipo_esperado}</b>", ParagraphStyle('', fontSize=8, textColor=colors.HexColor("#333333"))),
                        "", "", "", "", "",
                        Paragraph(f"<b>R$ {soma_tipo:,.2f}</b>", ParagraphStyle('', fontSize=8, alignment=TA_RIGHT, textColor=colors.HexColor("#666666")))
                    ])

            # LINHA TOTAL DO DIA
            tabela_dados.append([
                Paragraph(f"<b>Total {data_}</b>", ParagraphStyle('', fontSize=9)),
                "", "", "", "", "",
                Paragraph(f"<b>R$ {total_dia:,.2f}</b>", ParagraphStyle('', fontSize=9, alignment=TA_RIGHT))
            ])

            # ESTILIZAÇÃO
            ts = TableStyle([
                # Fundo preto na 1a linha (Empresa/Data)
                ('BACKGROUND', (0,0), (-1,0), cor_fundo_th),
                ('TEXTCOLOR',  (0,0), (-1,0), cor_txt_th),
                ('SPAN', (0,0), (4,0)),
                
                # Cabeçalhos da tabela (2a linha)
                ('BACKGROUND', (0,1), (-1,1), colors.HexColor("#000000")),
                ('TEXTCOLOR',  (0,1), (-1,1), cor_txt_th),
                ('FONTNAME',   (0,1), (-1,1), 'Helvetica-Bold'),
                ('FONTSIZE',   (0,1), (-1,1), 7),
                ('ALIGN',      (0,1), (-1,1), 'CENTER'),
                ('ALIGN',      (0,1), (0,1), 'LEFT'),
                
                # Formatação geral
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ('TOPPADDING', (0,0), (-1,-1), 4),
            ])
            
            # Bordas para as linhas de tipo e total
            n_linhas = len(tabela_dados)
            ts.add('BACKGROUND', (0, n_linhas-1), (-1, n_linhas-1), colors.HexColor("#dcd2c6")) # Cor bege do BOAH
            ts.add('SPAN', (0, n_linhas-1), (1, n_linhas-1))
            ts.add('SPAN', (2, n_linhas-1), (4, n_linhas-1))
            ts.add('SPAN', (5, n_linhas-1), (6, n_linhas-1))
            
            t = Table(tabela_dados, colWidths=[6.5*cm, 3.5*cm, 2*cm, 2.5*cm, 3*cm, 4*cm, 6*cm], repeatRows=2)
            t.setStyle(ts)
            
            elements.append(KeepTogether([t, Spacer(1, 0.5*cm)]))
            
    doc.build(elements)
    return caminho_pdf


def gerar_pdf_gnre(guia: dict) -> str:
    """Gera o PDF de uma Guia GNRE emitida no estilo oficial de duas vias."""
    
    # Pasta de guias
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    guias_dir = os.path.join(base_dir, "data", "guias_gnre")
    os.makedirs(guias_dir, exist_ok=True)
    
    nome_arq = f"GUIA_GNRE_{guia.get('numero_tx', 'TESTE')}.pdf"
    caminho_pdf = os.path.join(guias_dir, nome_arq)

    doc = SimpleDocTemplate(
        caminho_pdf,
        pagesize=A4,
        leftMargin=1*cm, rightMargin=1*cm,
        topMargin=1*cm, bottomMargin=1*cm
    )

    styles = getSampleStyleSheet()
    
    styleTitle = ParagraphStyle('TitleGNRE', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, alignment=TA_CENTER)
    styleLabel = ParagraphStyle('LabelGNRE', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7, textColor=colors.HexColor("#444444"))
    styleValue = ParagraphStyle('ValueGNRE', parent=styles['Normal'], fontName='Helvetica', fontSize=8)
    styleValueBold = ParagraphStyle('ValueBoldGNRE', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8)
    styleBarcode = ParagraphStyle('BarcodeGNRE', parent=styles['Normal'], fontName='Courier', fontSize=9, alignment=TA_CENTER)

    elements = []

    # Criaremos duas vias na mesma página (Via Contribuinte e Via Banco)
    def criar_via(nome_via):
        uf = guia.get("uf_favorecida", "PE")
        cnpj = guia.get("cnpj_emitente", "")
        receita = guia.get("codigo_receita", "100102")
        valor = float(guia.get("valor", 0))
        valor_formatado = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        vencimento = guia.get("data_vencimento", "")
        if "-" in vencimento:
            try:
                vencimento = datetime.strptime(vencimento, "%Y-%m-%d").strftime("%d/%m/%Y")
            except:
                pass
        
        doc_origem = guia.get("documento_origem", "")
        chave_nfe = guia.get("chave_acesso_nfe", "")
        linha_dig = guia.get("linha_digitavel", guia.get("codigo_barras", ""))
        
        tabela_dados = [
            [
                Paragraph("<b>GUIA NACIONAL DE RECOLHIMENTO DE TRIBUTOS ESTADUAIS - GNRE</b>", styleTitle), 
                ""
            ],
            [
                Paragraph("<b>UF FAVORECIDA:</b> " + uf, styleValueBold), 
                Paragraph("<b>CÓDIGO DA RECEITA:</b> " + receita, styleValueBold)
            ],
            [
                Paragraph("<b>CONTRIBUINTE EMITENTE:</b> CNPJ: " + cnpj + "<br/>BOAH COMERCIO VAREJISTA LTDA", styleValue), 
                Paragraph("<b>DATA DE VENCIMENTO:</b><br/>" + vencimento, styleValueBold)
            ],
            [
                Paragraph("<b>DOCUMENTO DE ORIGEM:</b> Nº NF: " + str(doc_origem) + " (Tipo 10)", styleValue), 
                Paragraph("<b>VALOR PRINCIPAL:</b><br/>" + valor_formatado, styleValueBold)
            ],
            [
                Paragraph("<b>CHAVE DE ACESSO NF-E:</b><br/>" + (chave_nfe or "N/A"), styleValue), 
                Paragraph("<b>VALOR TOTAL:</b><br/>" + valor_formatado, styleValueBold)
            ],
            [
                Paragraph("<b>CÓDIGO DE BARRAS / LINHA DIGITÁVEL:</b><br/>" + (linha_dig or "N/A"), styleBarcode), 
                ""
            ],
            [
                Paragraph("<b>INSTRUÇÕES / AUTENTICAÇÃO MECÂNICA:</b><br/>Guia emitida via WebService SEFAZ. Recolhimento por lote bancário SISPAG.", styleValue), 
                Paragraph(f"<b>VIA {nome_via.upper()}</b>", styleValueBold)
            ]
        ]

        t = Table(tabela_dados, colWidths=[12.5*cm, 6.5*cm])
        t.setStyle(TableStyle([
            ('SPAN', (0,0), (1,0)),
            ('SPAN', (0,5), (1,5)),
            ('BOX', (0,0), (-1,-1), 1.2, colors.black),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#777777")),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#e4e4e7")),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        return t

    # Adiciona a primeira via (Contribuinte)
    elements.append(criar_via("Contribuinte"))
    elements.append(Spacer(1, 0.6*cm))
    
    # Linha divisória tracejada
    styleDashed = ParagraphStyle('Dashed', parent=styles['Normal'], alignment=TA_CENTER, fontSize=8, textColor=colors.HexColor("#999999"))
    elements.append(Paragraph("- - - - - - - - - - - - - - - - - - - - - - - - - - - Destaque Aqui (Tesoura) - - - - - - - - - - - - - - - - - - - - - - - - - - -", styleDashed))
    elements.append(Spacer(1, 0.6*cm))
    
    # Adiciona a segunda via (Banco)
    elements.append(criar_via("Banco"))

    doc.build(elements)
    return caminho_pdf
