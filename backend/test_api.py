import asyncio
from fastapi import UploadFile
from main import api_importar_xml
from io import BytesIO

async def test_import():
    content = b"""<?xml version='1.0' encoding='ISO-8859-1'?>
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
</InfNfse>
</Nfse>
</CompNfse>
</ListaNfse>
</ConsultarNfseResposta>"""
    f = UploadFile(filename="test.xml", file=BytesIO(content))
    res = await api_importar_xml([f])
    print(res)

if __name__ == "__main__":
    asyncio.run(test_import())
