"""
Cria e valida JSON Web Tokens (JWT) usados na autenticacao da API.

Usa python-jose. O segredo, algoritmo e tempo de expiracao vem do
config (.env). O payload do token guarda o id do usuario e o perfil,
o que ja basta pra autorizar a maioria das requisicoes sem precisar
ir ao banco.

Pra checar a senha em si, ver password_hasher.py.
"""
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt

from app.config import settings


def criar_token(usuario_id: int, perfil: str, expira_em_minutos: int | None = None) -> tuple[str, int]:
    """
    Gera um JWT assinado pro usuario.

    Retorna uma tupla (token, expires_in_segundos), igual ao formato que
    o RFC 6749 (OAuth 2) recomenda na resposta de login.
    """
    minutos = expira_em_minutos or settings.jwt_expiration_minutes
    agora = datetime.now(timezone.utc)
    expira_em = agora + timedelta(minutes=minutos)
    payload: dict[str, Any] = {
        "sub": str(usuario_id),
        "perfil": perfil,
        "iat": agora,
        "exp": expira_em,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, minutos * 60


def decodificar_token(token: str) -> dict:
    """
    Decodifica e valida o JWT. Levanta jose.JWTError se for invalido,
    expirado ou se a assinatura nao bater.
    """
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
