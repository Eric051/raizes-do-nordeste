"""
Dependencies do FastAPI usadas pelas rotas.

- `get_db` ja vem do connection.py e abre/fecha a sessao do banco.
- `get_usuario_atual` extrai o usuario do JWT no header Authorization.
- `exigir_perfis(...)` eh uma factory que devolve uma dependency que
  so deixa passar quem tem um dos perfis informados.
"""
from typing import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.domain.entities.enums import PerfilUsuario
from app.domain.exceptions import CredenciaisInvalidas, SemPermissao
from app.infrastructure.database import models
from app.infrastructure.database.connection import get_db
from app.infrastructure.security.jwt_handler import decodificar_token


# auto_error=False pra que a gente mesma controle a mensagem de erro
# (com o padrao de erro JSON), em vez de o FastAPI levantar 403 bruto.
bearer_scheme = HTTPBearer(auto_error=False, description="Token JWT obtido em /auth/login")


def get_usuario_atual(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.Usuario:
    """
    Extrai o usuario do JWT no header `Authorization: Bearer <token>`.
    Falha com 401 se nao houver token, se for invalido ou se o usuario
    nao estiver mais ativo no banco.
    """
    if credentials is None:
        raise CredenciaisInvalidas("Token de autenticacao nao informado.")

    try:
        payload = decodificar_token(credentials.credentials)
    except JWTError:
        raise CredenciaisInvalidas("Token invalido ou expirado.")

    user_id = payload.get("sub")
    if user_id is None:
        raise CredenciaisInvalidas("Token invalido.")

    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise CredenciaisInvalidas("Token invalido.")

    usuario = db.query(models.Usuario).filter_by(id=user_id_int).first()
    if usuario is None or not usuario.ativo:
        raise CredenciaisInvalidas("Usuario nao encontrado ou inativo.")

    return usuario


def exigir_perfis(*perfis_permitidos: PerfilUsuario) -> Callable:
    """
    Factory que devolve uma dependency restrita aos perfis informados.

    Uso tipico:
        @router.post(
            "/produtos",
            dependencies=[Depends(exigir_perfis(PerfilUsuario.ADMIN, PerfilUsuario.GERENTE))],
        )

    Ou pra recuperar o usuario na rota:
        def rota(usuario = Depends(exigir_perfis(PerfilUsuario.ADMIN))):
            ...
    """
    def checar(usuario: models.Usuario = Depends(get_usuario_atual)) -> models.Usuario:
        if usuario.perfil not in perfis_permitidos:
            permitidos = ", ".join(p.value for p in perfis_permitidos)
            raise SemPermissao(
                f"Seu perfil ({usuario.perfil.value}) nao tem permissao pra essa acao. "
                f"Perfis permitidos: {permitidos}."
            )
        return usuario
    return checar
