"""
utils/inbox_scanner.py — Varredor de e-mails em background (IMAP Scanner) do Com System.

Monitora periodicamente uma caixa postal via IMAP seguro, extraindo anexos de extratos
e relatórios de adquirentes e salvando-os automaticamente na pasta monitorada do Hot Folder.
"""
from __future__ import annotations

import os
import sys
import time
import imaplib
import email
import threading
import traceback
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional
from services.logger_service import logger

# Garante codificação UTF-8 no console do Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _cfg():
    import config as c
    return c


EXTENSOES_ANEXOS = {".pdf", ".ofx", ".xlsx", ".xls"}


class InboxScannerThread(threading.Thread):
    """
    Thread daemon que conecta periodicamente via IMAP SSL para varrer e-mails não lidos,
    baixando anexos de extratos/relatórios direto na pasta do Hot Folder.
    """

    def __init__(
        self,
        callback_novo_arquivo: Optional[Callable[[str], None]] = None,
        callback_log: Optional[Callable[[str], None]] = None
    ):
        super().__init__(daemon=True, name="InboxScanner")
        self.callback_novo_arquivo = callback_novo_arquivo
        self.callback_log = callback_log
        self._stop_event = threading.Event()
        
        cfg = _cfg()
        self.host = getattr(cfg, "IMAP_HOST", "imap.suaempresa.com.br")
        self.port = getattr(cfg, "IMAP_PORT", 993)
        self.user = getattr(cfg, "IMAP_USER", "")
        self.password = getattr(cfg, "IMAP_PASSWORD", "")
        self.intervalo_min = getattr(cfg, "IMAP_SCAN_INTERVAL_MIN", 15)
        self.pasta_destino = getattr(cfg, "SAAS_PASTA_MONITORADA", "")

    def _log(self, msg: str):
        full_msg = f"[InboxScanner] {msg}"
        logger.info(full_msg)
        if self.callback_log:
            try:
                self.callback_log(full_msg)
            except Exception:
                pass

    def parar(self):
        """Para a thread de forma segura."""
        self._stop_event.set()

    def run(self):
        self._log("INICIADO - Varredura em segundo plano ativada.")
        
        # Primeira execução imediata
        if not self.password:
            self._log("⚠️ Nenhuma senha configurada para IMAP. Varredura suspensa até configuração.")
        else:
            try:
                self.varrer()
            except Exception as e:
                self._log(f"Erro na varredura inicial: {e}")

        # Loop periódico
        while not self._stop_event.is_set():
            # Converte minutos em segundos para a espera
            segundos_espera = self.intervalo_min * 60
            # Espera fracionada para permitir parada rápida do app
            etapa = 5.0
            esperados = 0.0
            while esperados < segundos_espera:
                if self._stop_event.is_set():
                    break
                self._stop_event.wait(etapa)
                esperados += etapa
            
            if self._stop_event.is_set():
                break

            if not self.password:
                continue

            try:
                self.varrer()
            except Exception as e:
                self._log(f"Erro durante a varredura: {e}")
                
        self._log("ENCERRADO.")

    def varrer(self):
        """Executa a conexão e varredura de e-mails na pasta INBOX."""
        self._log(f"Iniciando varredura em {self.host}:{self.port}...")
        
        if not self.pasta_destino:
            self._log("Erro: SAAS_PASTA_MONITORADA não configurada.")
            return

        os.makedirs(self.pasta_destino, exist_ok=True)
        
        mail = None
        try:
            # Conecta via IMAP SSL de forma segura
            mail = imaplib.IMAP4_SSL(self.host, self.port, timeout=30)
            mail.login(self.user, self.password)
            
            # Seleciona pasta principal de e-mails de entrada
            status, data = mail.select("INBOX")
            if status != "OK":
                self._log("Erro ao selecionar a pasta INBOX.")
                return

            # Busca por e-mails NÃO lidos (UNSEEN)
            status, ids_data = mail.search(None, "UNSEEN")
            if status != "OK":
                self._log("Erro ao buscar e-mails não lidos.")
                return

            email_ids = ids_data[0].split()
            if not email_ids:
                self._log("Nenhum e-mail não lido encontrado para ingestão.")
                return

            self._log(f"Detectado(s) {len(email_ids)} e-mail(s) não lido(s). Processando...")

            for e_id in email_ids:
                if self._stop_event.is_set():
                    break
                try:
                    self._processar_email_id(mail, e_id)
                except Exception as ex:
                    self._log(f"Erro ao processar e-mail ID {e_id.decode()}: {ex}")

        except Exception as e:
            self._log(f"Erro de conexão IMAP: {e}")
        finally:
            if mail:
                try:
                    mail.logout()
                except Exception:
                    pass

    def _processar_email_id(self, mail, e_id):
        """Busca o e-mail completo, extrai anexos válidos e marca como lido."""
        # Busca o conteúdo do e-mail (RFC822)
        status, data = mail.fetch(e_id, "(RFC822)")
        if status != "OK" or not data:
            return

        raw_email = data[0][1]
        msg = email.message_from_bytes(raw_email)
        
        assunto = msg.get("Subject", "(Sem Assunto)")
        remetente = msg.get("From", "(Desconhecido)")
        
        # Decodifica cabeçalho do assunto se necessário
        try:
            from email.header import decode_header
            decoded = decode_header(assunto)
            partes = []
            for text, codec in decoded:
                if isinstance(text, bytes):
                    partes.append(text.decode(codec or "utf-8", errors="replace"))
                else:
                    partes.append(text)
            assunto = "".join(partes)
        except Exception:
            pass

        self._log(f"Lendo e-mail: '{assunto}' de <{remetente}>")

        anexos_salvos = []

        # Varre as partes do e-mail procurando por anexos
        if msg.is_multipart():
            for part in msg.walk():
                # Ignora contêineres multipart
                if part.get_content_maintype() == "multipart":
                    continue
                # Ignora se não houver cabeçalho de disposição (anexo)
                if part.get("Content-Disposition") is None:
                    continue

                filename = part.get_filename()
                if not filename:
                    continue

                # Decodifica nome do arquivo
                try:
                    from email.header import decode_header
                    decoded = decode_header(filename)
                    partes = []
                    for text, codec in decoded:
                        if isinstance(text, bytes):
                            partes.append(text.decode(codec or "utf-8", errors="replace"))
                        else:
                            partes.append(text)
                    filename = "".join(partes)
                except Exception:
                    pass

                ext = Path(filename).suffix.lower()
                if ext in EXTENSOES_ANEXOS:
                    # Carrega conteúdo do anexo
                    payload = part.get_payload(decode=True)
                    if not payload:
                        continue

                    # Garante nome único para evitar colisões
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    safe_filename = f"{Path(filename).stem}_{timestamp}{ext}"
                    caminho_completo = os.path.join(self.pasta_destino, safe_filename)

                    with open(caminho_completo, "wb") as f:
                        f.write(payload)

                    self._log(f"Anexo salvo com sucesso: '{filename}' ➔ '{safe_filename}'")
                    anexos_salvos.append(safe_filename)
                    
                    # Dispara callback para a GUI
                    if self.callback_novo_arquivo:
                        try:
                            self.callback_novo_arquivo(caminho_completo)
                        except Exception as cb_err:
                            self._log(f"Erro no callback de novo arquivo: {cb_err}")

        # Marca o e-mail como lido (adiciona a flag Seen)
        mail.store(e_id, "+FLAGS", "\\Seen")
        
        if anexos_salvos:
            self._log(f"Concluído: e-mail processado e {len(anexos_salvos)} anexo(s) extraído(s).")
        else:
            self._log("Concluído: e-mail processado (nenhum anexo compatível encontrado).")
