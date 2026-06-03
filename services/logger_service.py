import logging
import queue
import sys
import os
from datetime import datetime

# Fila thread-safe para enviar logs para a interface gráfica
gui_log_queue = queue.Queue()

class GuiLogHandler(logging.Handler):
    """Handler customizado que envia logs formatados para a fila da GUI."""
    def emit(self, record):
        try:
            msg = self.format(record)
            # Envia uma tupla com o nível (INFO, ERROR, etc) e a mensagem
            gui_log_queue.put((record.levelname, msg))
        except Exception:
            self.handleError(record)

def setup_logger():
    """Configura o logger global da aplicação."""
    logger = logging.getLogger("ComSystem")
    logger.setLevel(logging.DEBUG)

    # Evita duplicação de handlers se for chamado múltiplas vezes
    if not logger.handlers:
        # Formatter padrão
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%H:%M:%S')

        # 1. Console Handler (Substitui os prints soltos no terminal)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # 2. File Handler (Persistência para auditoria)
        # Cria a pasta de logs se não existir
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"comsystem_{datetime.now().strftime('%Y%m%d')}.log")
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # 3. GUI Handler (Para exibir na tela de logs do app)
        gui_handler = GuiLogHandler()
        gui_handler.setLevel(logging.INFO)
        # Na GUI, a própria função _log do app pode formatar a data
        gui_formatter = logging.Formatter('%(message)s')
        gui_handler.setFormatter(gui_formatter)
        logger.addHandler(gui_handler)

    # Intercepta exceções globais silenciosas
    def global_exception_handler(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.error("Exceção Não Tratada:", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = global_exception_handler

    return logger

# Instância global configurada
logger = setup_logger()
