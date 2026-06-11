"""
backup_automatico.py — Backup noturno seguro dos bancos SQLite do ERP.

Funcionalidades:
- Copia todos os bancos .db do sistema com timestamp
- Mantém apenas os últimos N backups (configur\u00e1vel)
- Log de cada execução
- Pode ser agendado via Windows Task Scheduler ou cron

USO:
  python backup_automatico.py              # Executa backup imediato
  python backup_automatico.py --listar     # Lista backups existentes
  python backup_automatico.py --limpar     # Remove backups antigos
"""
import os
import sys
import shutil
import sqlite3
import json
import argparse
from datetime import datetime
from pathlib import Path

# ── Configuração ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
ERP_DIR  = BASE_DIR.parent  # C:\Users\Roberto\Desktop\ERP COMPLETO

BACKUP_DIR = BASE_DIR / "data" / "backups"
LOG_FILE   = BACKUP_DIR / "backup.log"
MAX_BACKUPS_POR_DB = 7  # Mantém 7 dias de backup por banco

# Bancos a fazer backup (caminho relativo a ERP_DIR)
BANCOS = {
    "robo_boah": BASE_DIR / "robo_boah.db",
    "fabricOS": ERP_DIR / "Controle de retirada de peças" / "backend" / "fabricos.db",
    "fabricOS_app": ERP_DIR / "Controle de retirada de peças" / "backend" / "app" / "database.db",
}


def log(msg: str, nivel: str = "INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linha = f"[{timestamp}] [{nivel}] {msg}"
    print(linha)
    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(linha + "\n")
    except Exception:
        pass


def verificar_integridade(db_path: Path) -> bool:
    """Verifica integridade do banco SQLite antes de fazer backup."""
    try:
        conn = sqlite3.connect(str(db_path))
        result = conn.execute("PRAGMA integrity_check").fetchone()
        conn.close()
        return result and result[0] == "ok"
    except Exception as e:
        log(f"Erro na verificação de integridade de {db_path.name}: {e}", "ERRO")
        return False


def fazer_backup(nome: str, db_path: Path) -> bool:
    """Faz backup de um banco com timestamp."""
    if not db_path.exists():
        log(f"Banco '{nome}' não encontrado em {db_path} — pulando.", "AVISO")
        return False

    # Verifica integridade antes do backup
    if not verificar_integridade(db_path):
        log(f"Banco '{nome}' falhou na verificação de integridade! Backup abortado.", "ERRO")
        return False

    # Cria pasta de backup para este banco
    pasta_banco = BACKUP_DIR / nome
    pasta_banco.mkdir(parents=True, exist_ok=True)

    # Nome do arquivo de backup com timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_backup = f"{nome}_{timestamp}.db"
    dest = pasta_banco / nome_backup

    try:
        # Usa connection.backup() para backup quente (sem lock)
        src_conn = sqlite3.connect(str(db_path))
        dst_conn = sqlite3.connect(str(dest))
        src_conn.backup(dst_conn)
        dst_conn.close()
        src_conn.close()

        tamanho = dest.stat().st_size / (1024 * 1024)
        log(f"✅ Backup '{nome}' → {nome_backup} ({tamanho:.2f} MB)")
        return True
    except Exception as e:
        log(f"❌ Falha no backup de '{nome}': {e}", "ERRO")
        return False


def limpar_backups_antigos(nome: str):
    """Remove backups mais antigos que MAX_BACKUPS_POR_DB."""
    pasta_banco = BACKUP_DIR / nome
    if not pasta_banco.exists():
        return

    backups = sorted(pasta_banco.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    removidos = 0
    for backup_antigo in backups[MAX_BACKUPS_POR_DB:]:
        try:
            backup_antigo.unlink()
            removidos += 1
        except Exception as e:
            log(f"Não foi possível remover {backup_antigo.name}: {e}", "AVISO")

    if removidos > 0:
        log(f"🗑️  Removidos {removidos} backup(s) antigo(s) de '{nome}'")


def listar_backups():
    """Lista todos os backups existentes com tamanho e data."""
    print("\n📦 Backups existentes:\n")
    if not BACKUP_DIR.exists():
        print("  Nenhum backup encontrado.")
        return

    for pasta in sorted(BACKUP_DIR.iterdir()):
        if not pasta.is_dir() or pasta.name == "backup.log":
            continue
        backups = sorted(pasta.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
        print(f"  [{pasta.name}] — {len(backups)} backup(s):")
        for b in backups[:5]:
            dt = datetime.fromtimestamp(b.stat().st_mtime).strftime("%d/%m/%Y %H:%M")
            sz = b.stat().st_size / (1024 * 1024)
            print(f"    • {b.name} — {sz:.2f} MB — {dt}")
        print()


def gerar_relatorio(resultados: dict):
    """Salva relatório JSON do backup."""
    relatorio = {
        "data_hora": datetime.now().isoformat(),
        "resultados": resultados,
        "total_ok": sum(1 for v in resultados.values() if v),
        "total_erro": sum(1 for v in resultados.values() if not v),
    }
    relatorio_path = BACKUP_DIR / f"relatorio_{datetime.now().strftime('%Y%m%d')}.json"
    with open(relatorio_path, "w", encoding="utf-8") as f:
        json.dump(relatorio, f, indent=2, ensure_ascii=False)
    log(f"📄 Relatório salvo em {relatorio_path.name}")


def main():
    parser = argparse.ArgumentParser(description="Backup automático dos bancos do ERP")
    parser.add_argument("--listar", action="store_true", help="Lista backups existentes")
    parser.add_argument("--limpar", action="store_true", help="Remove backups antigos")
    args = parser.parse_args()

    if args.listar:
        listar_backups()
        return

    if args.limpar:
        log("Limpando backups antigos...")
        for nome in BANCOS:
            limpar_backups_antigos(nome)
        return

    # Executa backup completo
    log("=" * 60)
    log("🚀 Iniciando backup automático do ERP")
    log("=" * 60)

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    resultados = {}

    for nome, db_path in BANCOS.items():
        resultados[nome] = fazer_backup(nome, db_path)
        limpar_backups_antigos(nome)

    ok = sum(1 for v in resultados.values() if v)
    total = len(resultados)
    log(f"\n{'✅' if ok == total else '⚠️'} Backup concluído: {ok}/{total} bancos com sucesso")
    gerar_relatorio(resultados)

    # Retorna código de erro se algum banco falhou
    sys.exit(0 if ok == total else 1)


if __name__ == "__main__":
    main()
