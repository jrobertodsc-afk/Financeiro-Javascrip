"""
utils/saas_integration.py — Camada de Ingestão Unificada do Com System SaaS.

Responsável por:
  1. HotFolderMonitorThread: Monitora em background uma pasta local, processando
     automaticamente qualquer extrato PDF/OFX do Itaú ou planilha XLSX da Getnet
     que o usuário depositar nela, sem nenhuma interação manual no ERP.
  2. ApiDataFetcher: Encapsula a busca de dados via Open Finance e APIs de
     adquirentes (Itaú, Getnet), ativado apenas quando SAAS_PREMIUM_ATIVO=True.
  3. IngestaoUnificada: Normaliza, valida e persiste os dados no banco de dados
     local (SQLite) e, quando conectado, no Supabase em nuvem.
"""
from __future__ import annotations

import os
import sys
import time
import shutil
import threading
import traceback
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional
from services.logger_service import logger

# Garante que o stdout use UTF-8 no Windows (evita UnicodeEncodeError no CP1252)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# ── Lazy imports de configurações (evita circular import) ─────────────────────
def _cfg():
    """Importa configurações de forma lazy."""
    import config as c
    return c


# ══════════════════════════════════════════════════════════════════════════════
# ── NORMALIZADOR / VALIDADOR DE DADOS ─────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def _normalizar_lancamentos(contas: dict, origem: str) -> list[dict]:
    """Converte a estrutura de contas/lançamentos para uma lista plana normalizada."""
    resultado = []
    for conta_key, dados in contas.items():
        for l in dados.get("lancamentos", []):
            resultado.append({
                "origem":       origem,
                "conta":        dados.get("nome", conta_key),
                "data":         l.get("data", ""),
                "descricao":    l.get("descricao", ""),
                "tipo":         l.get("tipo", ""),
                "valor":        float(l.get("valor", 0)),
                "debito":       bool(l.get("debito", False)),
                "processado_em": datetime.now().isoformat(),
            })
    return resultado


def _normalizar_getnet(recebiveis: list[dict], arquivo: str) -> list[dict]:
    """Normaliza lançamentos Getnet para o formato padrão interno."""
    resultado = []
    for r in recebiveis:
        dt = r.get("data_venda")
        data_str = dt.strftime("%d/%m/%Y") if hasattr(dt, "strftime") else str(dt or "")
        resultado.append({
            "origem":       f"Getnet/{r.get('filial', 'GERAL')}",
            "conta":        r.get("filial", "GETNET"),
            "data":         data_str,
            "descricao":    f"{r.get('bandeira','')} {r.get('forma','')}".strip(),
            "tipo":         r.get("modalidade", ""),
            "valor":        float(r.get("liquido", 0)),
            "debito":       False,
            "processado_em": datetime.now().isoformat(),
        })
    return resultado


# ══════════════════════════════════════════════════════════════════════════════
# ── PERSISTER — Grava no banco de dados local ─────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def _persistir_lancamentos(lancamentos: list[dict]) -> int:
    """
    Persiste a lista de lançamentos na tabela `saas_lancamentos` do SQLite.
    Cria a tabela se ainda não existir. Retorna o número de linhas inseridas.
    """
    if not lancamentos:
        return 0
    try:
        import sqlite3
        cfg = _cfg()
        con = sqlite3.connect(cfg.DB_PATH)
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS saas_lancamentos (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                origem        TEXT,
                conta         TEXT,
                data          TEXT,
                descricao     TEXT,
                tipo          TEXT,
                valor         REAL,
                debito        INTEGER,
                processado_em TEXT
            )
        """)
        rows = [
            (l["origem"], l["conta"], l["data"], l["descricao"],
             l["tipo"], l["valor"], 1 if l["debito"] else 0, l["processado_em"])
            for l in lancamentos
        ]
        cur.executemany(
            "INSERT INTO saas_lancamentos (origem,conta,data,descricao,tipo,valor,debito,processado_em) "
            "VALUES (?,?,?,?,?,?,?,?)",
            rows
        )
        con.commit()
        con.close()
        return len(rows)
    except Exception as e:
        logger.error(f"[saas_integration] Erro ao persistir lançamentos: {e}")
        return 0


# ══════════════════════════════════════════════════════════════════════════════
# ── PROCESSADOR DE ARQUIVO ────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def processar_arquivo(caminho: str) -> tuple[bool, str, list[dict]]:
    """
    Identifica o tipo do arquivo e invoca o parser correto.

    Retorna:
        (sucesso, mensagem, lancamentos_normalizados)
    """
    ext = Path(caminho).suffix.lower()
    nome = os.path.basename(caminho)

    try:
        if ext in (".pdf", ".ofx"):
            from utils.extratos_processor import ler_extrato_pdf
            contas, periodo = ler_extrato_pdf(caminho)
            if not contas:
                return False, f"Nenhuma transação encontrada em '{nome}'.", []
            lancamentos = _normalizar_lancamentos(contas, nome)
            total_inseridos = _persistir_lancamentos(lancamentos)
            msg = (f"✅ Extrato bancário '{nome}' processado — "
                   f"{total_inseridos} lançamentos · período: {periodo}")
            return True, msg, lancamentos

        elif ext in (".xlsx", ".xls"):
            from utils.extratos_processor import ler_getnet_excel
            recebiveis = ler_getnet_excel(caminho)
            if not recebiveis:
                return False, f"Nenhuma transação Getnet encontrada em '{nome}'.", []
            lancamentos = _normalizar_getnet(recebiveis, nome)
            total_inseridos = _persistir_lancamentos(lancamentos)
            msg = (f"✅ Relatório Getnet '{nome}' processado — "
                   f"{total_inseridos} transações registradas")
            return True, msg, lancamentos

        else:
            return False, f"Extensão '{ext}' não reconhecida. Ignorando '{nome}'.", []

    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"[saas_integration] Erro ao processar '{nome}':\n{tb}")
        return False, f"❌ Erro ao processar '{nome}': {e}", []


def _marcar_processado(caminho: str):
    """Move o arquivo para a pasta de backup com sufixo .processado."""
    try:
        cfg = _cfg()
        os.makedirs(cfg.PASTA_BACKUP_EXTRATOS, exist_ok=True)
        nome_base = os.path.basename(caminho)
        destino = os.path.join(
            cfg.PASTA_BACKUP_EXTRATOS,
            f"{Path(nome_base).stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{Path(nome_base).suffix}.processado"
        )
        shutil.move(caminho, destino)
    except Exception as e:
        logger.info(f"[saas_integration] Aviso: Não foi possível mover '{caminho}': {e}")


# ══════════════════════════════════════════════════════════════════════════════
# ── HOT FOLDER MONITOR THREAD ─────────────────────────────════════════════════
# ══════════════════════════════════════════════════════════════════════════════

EXTENSOES_SUPORTADAS = {".pdf", ".ofx", ".xlsx", ".xls"}


class HotFolderMonitorThread(threading.Thread):
    """
    Thread daemon que varre silenciosamente a pasta configurada a cada N segundos.
    Quando detecta um arquivo suportado, o processa automaticamente e notifica
    a interface gráfica via callback.

    Args:
        pasta:          Caminho do diretório a monitorar.
        callback_ok:    Chamada quando um arquivo é processado com sucesso.
                        Assinatura: callback_ok(mensagem: str, lancamentos: list)
        callback_erro:  Chamada em caso de erro de processamento.
                        Assinatura: callback_erro(mensagem: str)
        intervalo_seg:  Intervalo entre varreduras em segundos (padrão: 5).
    """

    def __init__(
        self,
        pasta: str,
        callback_ok: Optional[Callable] = None,
        callback_erro: Optional[Callable] = None,
        intervalo_seg: int = 5,
    ):
        super().__init__(daemon=True, name="HotFolderMonitor")
        self.pasta = pasta
        self.callback_ok = callback_ok
        self.callback_erro = callback_erro
        self.intervalo_seg = intervalo_seg
        self._stop_event = threading.Event()
        self._arquivos_vistos: set[str] = set()

    def parar(self):
        """Solicita o encerramento seguro da thread."""
        self._stop_event.set()

    def run(self):
        logger.info(f"[HotFolderMonitor] INICIADO - Monitorando: {self.pasta} (intervalo: {self.intervalo_seg}s)")
        while not self._stop_event.is_set():
            try:
                self._varrer()
            except Exception as e:
                logger.error(f"[HotFolderMonitor] Erro durante varredura: {e}")
            self._stop_event.wait(self.intervalo_seg)
        logger.info("[HotFolderMonitor] ENCERRADO.")

    def _varrer(self):
        """Percorre a pasta procurando arquivos novos para processar."""
        if not os.path.isdir(self.pasta):
            return

        for nome in os.listdir(self.pasta):
            if self._stop_event.is_set():
                break
            caminho = os.path.join(self.pasta, nome)
            if not os.path.isfile(caminho):
                continue

            # Ignora arquivos já vistos ou com extensão não suportada
            ext = Path(nome).suffix.lower()
            if ext not in EXTENSOES_SUPORTADAS:
                continue
            if caminho in self._arquivos_vistos:
                continue

            # Aguarda o arquivo estar completamente escrito (até 3 tentativas)
            if not self._aguardar_arquivo_pronto(caminho):
                continue

            self._arquivos_vistos.add(caminho)
            logger.info(f"[HotFolderMonitor] Novo arquivo detectado: {nome}")

            sucesso, mensagem, lancamentos = processar_arquivo(caminho)

            if sucesso:
                _marcar_processado(caminho)
                if self.callback_ok:
                    self.callback_ok(mensagem, lancamentos)
            else:
                if self.callback_erro:
                    self.callback_erro(mensagem)

    @staticmethod
    def _aguardar_arquivo_pronto(caminho: str, tentativas: int = 3, espera: float = 1.0) -> bool:
        """Verifica se o arquivo está estável (tamanho não muda entre leituras)."""
        tamanho_anterior = -1
        for _ in range(tentativas):
            try:
                tamanho_atual = os.path.getsize(caminho)
                if tamanho_atual == tamanho_anterior and tamanho_atual > 0:
                    return True
                tamanho_anterior = tamanho_atual
                time.sleep(espera)
            except OSError:
                return False
        return tamanho_anterior > 0


# ══════════════════════════════════════════════════════════════════════════════
# ── API DATA FETCHER (Premium) ────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

class ApiDataFetcher:
    """
    Encapsula a busca de dados via Open Finance / APIs de adquirentes.
    Ativado somente quando SAAS_PREMIUM_ATIVO = True e SAAS_MODO_INTEGRACAO = "API".

    Estratégia: usa as implementações reais quando credenciais estiverem
    configuradas, ou a simulação Mock para desenvolvimento e demonstração.
    """

    def __init__(self, credenciais: dict):
        self.credenciais = credenciais or {}

    def buscar_extrato_itau(self, data_ini: str, data_fim: str) -> tuple[dict, str]:
        """Busca extrato do Itaú via Open Finance e retorna no formato padrão interno."""
        try:
            from utils.open_finance import ItauOpenFinance
            api = ItauOpenFinance(
                client_id=self.credenciais.get("itau_client_id"),
                client_secret=self.credenciais.get("itau_client_secret"),
            )
            api.autenticar()
            resposta = api.buscar_extrato(data_ini, data_fim)

            # Converte resposta JSON da API para o formato padrão de `contas`
            lancamentos = []
            for tx in resposta.get("transacoes", []):
                valor = float(tx.get("valor", 0))
                debito = tx.get("tipoTransacao", "DEBITO") == "DEBITO"
                lancamentos.append({
                    "data":      tx.get("dataTransacao", ""),
                    "descricao": tx.get("descricao", ""),
                    "tipo":      tx.get("tipoTransacao", ""),
                    "valor":     valor,
                    "debito":    debito,
                })

            conta_key = f"{resposta.get('agencia','0000')}/{resposta.get('conta','00000-0')}"
            periodo = f"{data_ini} a {data_fim}"
            contas = {
                conta_key: {
                    "nome": resposta.get("banco", "ITAÚ"),
                    "lancamentos": lancamentos,
                    "saldo_final": 0.0,
                    "saldo_inicial": 0.0,
                }
            }
            return contas, periodo

        except Exception as e:
            logger.error(f"[ApiDataFetcher] Erro ao buscar extrato Itaú: {e}")
            return {}, datetime.now().strftime("%d/%m/%Y")

    def buscar_getnet(self, data_ini: str, data_fim: str) -> list[dict]:
        """Busca recebíveis Getnet via API e retorna lista no formato padrão interno."""
        # Stub preparado — implementação real ativada quando credenciais Getnet forem fornecidas
        logger.info(f"[ApiDataFetcher] Getnet API: Em desenvolvimento. Período: {data_ini} a {data_fim}")
        return []


# ══════════════════════════════════════════════════════════════════════════════
# ── INGESTÃO UNIFICADA — Fachada Principal ────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

class IngestaoUnificada:
    """
    Ponto de entrada único para qualquer tipo de ingestão de dados financeiros.
    Roteamento automático com base nas flags SaaS do config.py.
    """

    def __init__(self):
        cfg = _cfg()
        self.modo          = getattr(cfg, "SAAS_MODO_INTEGRACAO", "PASTA")
        self.premium_ativo = getattr(cfg, "SAAS_PREMIUM_ATIVO", False)
        self.credenciais   = getattr(cfg, "SAAS_API_CREDENTIALS", {})

    def processar_arquivo_manual(self, caminho: str) -> tuple[bool, str, list[dict]]:
        """Processa um arquivo fornecido manualmente pelo usuário via seletor de arquivos."""
        return processar_arquivo(caminho)

    def buscar_via_api(self, data_ini: str, data_fim: str) -> tuple[dict, list, str]:
        """
        Busca dados bancários + adquirentes via API.
        Disponível somente se SAAS_PREMIUM_ATIVO = True.
        Retorna (contas_itau, recebiveis_getnet, periodo).
        """
        if not self.premium_ativo or self.modo != "API":
            return {}, [], datetime.now().strftime("%d/%m/%Y")

        fetcher = ApiDataFetcher(self.credenciais)
        contas, periodo = fetcher.buscar_extrato_itau(data_ini, data_fim)
        recebiveis = fetcher.buscar_getnet(data_ini, data_fim)
        return contas, recebiveis, periodo
