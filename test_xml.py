import xml.etree.ElementTree as ET

content = """<?xml version='1.0' encoding='ISO-8859-1'?>
<ConsultarNfseResposta xmlns:xsd='http://www.w3.org/2001/XMLSchema' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance' xmlns='http://www.abrasf.org.br/ABRASF/arquivos/nfse.xsd'>
<ListaNfse>
<CompNfse>
<Nfse>
<InfNfse>
<Numero>6286</Numero>
<CodigoVerificacao>JL9ZQJBR</CodigoVerificacao>
<DataEmissao>2026-06-02T15:49:28-03:00</DataEmissao>
<IdentificacaoRps>
<Numero></Numero>
<Serie></Serie>
<Tipo>3</Tipo>
</IdentificacaoRps>
<NaturezaOperacao>1</NaturezaOperacao>
<OptanteSimplesNacional>1</OptanteSimplesNacional>
<Competencia>2026-06-01T00:00:00-03:00</Competencia>
<NfseSubstituida>0</NfseSubstituida>
<OutrasInformacoes></OutrasInformacoes>
<Servico>
<Valores>
<ValorServicos>1050</ValorServicos>
<ValorDeducoes>0</ValorDeducoes>
<ValorPis>0</ValorPis>
<ValorCofins>0</ValorCofins>
<ValorInss>0</ValorInss>
<ValorIr>0</ValorIr>
<ValorCsll>0</ValorCsll>
<IssRetido>1</IssRetido>
<ValorIssRetido>32,13</ValorIssRetido>
<OutrasRetencoes>0</OutrasRetencoes>
<BaseCalculo>1050</BaseCalculo>
<Aliquota>0,0306</Aliquota>
<ValorLiquidoNfse>1017,87</ValorLiquidoNfse>
<DescontoIncondicionado>0</DescontoIncondicionado>
<DescontoCondicionado>0</DescontoCondicionado>
</Valores>
<ItemListaServico>1305</ItemListaServico>
<CodigoCnae>1813099</CodigoCnae>
<CodigoTributacaoMunicipio>1305002</CodigoTributacaoMunicipio>
<Discriminacao>ITEM 01 - 100 BL BOLETA DE VENDAS</Discriminacao>
</Servico>
<PrestadorServico>
<IdentificacaoPrestador>
<Cnpj>03.165.536/0001-55</Cnpj>
<InscricaoMunicipal>15165400183</InscricaoMunicipal>
</IdentificacaoPrestador>
<RazaoSocial>3D SERVICOS GRAFICOS LTDA</RazaoSocial>
<Endereco>
<Endereco>Rua dos Protestantes</Endereco>
<Numero>38</Numero>
<Complemento>CASA 38</Complemento>
<Bairro>GARCIA</Bairro>
<CodigoMunicipio>2927408</CodigoMunicipio>
<Uf>BA</Uf>
<Cep>04010100</Cep>
</Endereco>
<Contato>
<Telefone>7132452721</Telefone>
<Email></Email>
</Contato>
</PrestadorServico>
<TomadorServico>
<IdentificacaoTomador>
<CpfCnpj>
<Cnpj>10.436.619/0001-05</Cnpj>
</CpfCnpj>
<InscricaoMunicipal>30726100115</InscricaoMunicipal>
</IdentificacaoTomador>
<RazaoSocial>LALUA COMERCIO DE MODAS LTDA</RazaoSocial>
<Endereco>
<Endereco>Rua Marechal Andr a</Endereco>
<Numero>82</Numero>
<Complemento>CASA</Complemento>
<Bairro>PITUBA</Bairro>
<CodigoMunicipio>2927408</CodigoMunicipio>
<Uf>BA</Uf>
<Cep>41810105</Cep>
</Endereco>
<Contato>
<Telefone></Telefone>
<Email></Email>
</Contato>
</TomadorServico>
<OrgaoGerador>
<CodigoMunicipio>2927408</CodigoMunicipio>
<Uf>BA</Uf>
</OrgaoGerador>
<ContrucaoCivil>
<CodigoObra></CodigoObra>
<Art></Art>
</ContrucaoCivil>
</InfNfse>
</Nfse>
</CompNfse>
</ListaNfse>
</ConsultarNfseResposta>
"""

root = ET.fromstring(content)
for elem in root.iter():
    if '}' in elem.tag:
        elem.tag = elem.tag.split('}', 1)[1]

print("Root tag:", root.tag)

comp_nfses = root.findall('.//CompNfse')
print("Found comp_nfses:", len(comp_nfses))

for comp in comp_nfses:
    inf = comp.find('.//InfNfse')
    print("InfNfse found:", inf is not None)
    if inf is not None:
        print("Num:", inf.findtext('Numero', ''))
        print("Dt:", inf.findtext('DataEmissao', ''))
        print("Fornecedor:", inf.findtext('.//PrestadorServico/IdentificacaoPrestador/RazaoSocial', ''))
        print("Fornecedor2:", inf.findtext('.//PrestadorServico/RazaoSocial', ''))
        print("CNPJ:", inf.findtext('.//PrestadorServico/IdentificacaoPrestador/Cnpj', ''))
        print("Valor:", inf.findtext('.//Servico/Valores/ValorServicos', ''))
        print("Desc:", inf.findtext('.//Servico/Discriminacao', ''))
