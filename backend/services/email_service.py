import smtplib
from email.message import EmailMessage
import os
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

SMTP_SERVER = "smtp.office365.com"
SMTP_PORT = 587
SMTP_USER = os.getenv("EMAIL_USER", "seu-email@empresa.com.br")
SMTP_PASS = os.getenv("EMAIL_PASS", "sua-senha")

def enviar_comprovante_email(destinatario: str, assunto: str, corpo_html: str, filepath_anexo: str = None) -> bool:
    try:
        if not destinatario:
            logger.error("Destinatário não informado para envio de e-mail.")
            return False

        msg = EmailMessage()
        msg["Subject"] = assunto
        msg["From"] = SMTP_USER
        msg["To"] = destinatario
        
        msg.set_content(corpo_html, subtype='html')

        if filepath_anexo and os.path.exists(filepath_anexo):
            filename = os.path.basename(filepath_anexo)
            # Lê o arquivo em modo binário
            with open(filepath_anexo, 'rb') as f:
                file_data = f.read()
                
            # Determina o subtipo básico
            if filename.lower().endswith(".pdf"):
                maintype, subtype = "application", "pdf"
            elif filename.lower().endswith(".png"):
                maintype, subtype = "image", "png"
            elif filename.lower().endswith((".jpg", ".jpeg")):
                maintype, subtype = "image", "jpeg"
            else:
                maintype, subtype = "application", "octet-stream"

            msg.add_attachment(file_data, maintype=maintype, subtype=subtype, filename=filename)

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            # Necessário preencher .env ou variavel de ambiente com EMAIL_USER e EMAIL_PASS
            if SMTP_USER and SMTP_PASS and SMTP_USER != "seu-email@empresa.com.br":
                server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
            
        logger.success(f"E-mail enviado com sucesso para {destinatario}!")
        return True
    except Exception as e:
        logger.error(f"Erro ao enviar e-mail para {destinatario}: {str(e)}")
        return False
