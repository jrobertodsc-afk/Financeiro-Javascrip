"""
auth_service.py — Autenticação JWT segura para o ERP Hub.

Substitui o bypass inseguro anterior por tokens reais com:
- Expiração configurável (padrão 8h)
- Roles/Alçadas de aprovação
- Verificação de senha bcrypt
- Geração e validação de JWT via python-jose
"""
import os
import sqlite3
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from fastapi import HTTPException, status
from dotenv import load_dotenv

load_dotenv()

# ── Configurações JWT ─────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "TROQUE_ESSA_CHAVE_NO_ENV_AGORA_2024!")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))  # 8 horas

# ── Roles disponíveis no sistema ──────────────────────────────────────────────
ROLES = {
    "viewer":    {"nivel": 1, "label": "Visualizador",   "limite_aprovacao": 0},
    "operator":  {"nivel": 2, "label": "Operador",        "limite_aprovacao": 5_000},
    "manager":   {"nivel": 3, "label": "Gerente",         "limite_aprovacao": 50_000},
    "director":  {"nivel": 4, "label": "Diretor",         "limite_aprovacao": 999_999_999},
    "admin":     {"nivel": 5, "label": "Administrador",   "limite_aprovacao": 999_999_999},
}

# ── Usuários fallback (quando o DB de produção não está disponível) ───────────
# IMPORTANTE: Substitua estas senhas com hash bcrypt real antes de ir para produção
# Para gerar um hash: python -c "from passlib.context import CryptContext; print(CryptContext(['bcrypt']).hash('sua_senha'))"
FALLBACK_USERS = {
    "admin@erp.com.br": {
        "name": "Administrador",
        "role": "admin",
        # Senha: erp@2024 (troque no .env)
        "hashed_password": os.getenv("ADMIN_HASHED_PASSWORD", "$2b$12$placeholder_troque_no_env"),
    }
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica senha em texto plano contra hash bcrypt (bcrypt nativo, compatível com v5)."""
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8') if isinstance(hashed_password, str) else hashed_password
        )
    except Exception:
        return False


def hash_password(plain_password: str) -> str:
    """Gera hash bcrypt de uma senha."""
    return bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Cria um JWT assinado com expiração."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decodifica e valida um JWT. Lança HTTPException se inválido ou expirado."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou expirado. Faça login novamente.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception


def authenticate_user(username: str, password: str, fabricos_db_path: Optional[str] = None) -> Optional[dict]:
    """
    Autentica um usuário verificando:
    1. Banco de dados do FabricOS (SSO real)
    2. Usuários fallback definidos em FALLBACK_USERS

    Retorna dict com dados do usuário ou None se inválido.
    """
    # ── Tentativa 1: Banco de dados do FabricOS (SSO) ────────────────────────
    if fabricos_db_path and os.path.exists(fabricos_db_path):
        try:
            conn = sqlite3.connect(fabricos_db_path)
            conn.row_factory = sqlite3.Row
            user_row = conn.execute(
                "SELECT * FROM user WHERE email = ? AND is_active = 1", (username,)
            ).fetchone()
            conn.close()

            if user_row and verify_password(password, user_row["hashed_password"]):
                role = user_row.get("role", "operator")
                return {
                    "email": user_row["email"],
                    "name": user_row.get("full_name", username.split("@")[0].capitalize()),
                    "role": role if role in ROLES else "operator",
                    "nivel": ROLES.get(role, ROLES["operator"])["nivel"],
                }
        except Exception as e:
            print(f"[auth_service] Aviso — Erro no SSO FabricOS: {e}")

    # ── Tentativa 2: Usuários fallback ────────────────────────────────────────
    if username in FALLBACK_USERS:
        user = FALLBACK_USERS[username]
        if verify_password(password, user["hashed_password"]):
            role = user.get("role", "operator")
            return {
                "email": username,
                "name": user["name"],
                "role": role,
                "nivel": ROLES.get(role, ROLES["operator"])["nivel"],
            }

    return None  # Autenticação falhou


def get_role_info(role: str) -> dict:
    """Retorna informações da role/alçada do usuário."""
    return ROLES.get(role, ROLES["operator"])
