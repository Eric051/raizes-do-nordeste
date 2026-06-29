"""
Rotas de autenticacao.

Endpoints:
- POST /auth/register  -> cadastra um novo cliente
- POST /auth/login     -> autentica e retorna JWT
- GET  /auth/me        -> retorna o usuario atualmente autenticado
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_usuario_atual
from app.api.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UsuarioResponse,
)
from app.application.services import auth_service
from app.infrastructure.database import models
from app.infrastructure.database.connection import get_db


router = APIRouter(prefix="/auth", tags=["Autenticacao"])


@router.post(
    "/register",
    response_model=UsuarioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra um novo cliente",
    description=(
        "Cria uma conta com perfil CLIENTE. Exige aceite explicito do "
        "termo da LGPD via campo `consentimento_lgpd=true`."
    ),
)
def register(dados: RegisterRequest, db: Session = Depends(get_db)) -> UsuarioResponse:
    return auth_service.cadastrar_cliente(db, dados)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Autentica um usuario e retorna o JWT",
    description=(
        "Recebe e-mail e senha. Se forem validos, devolve um access token JWT "
        "que deve ser usado nos demais endpoints como header "
        "`Authorization: Bearer <token>`."
    ),
)
def login(dados: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    return auth_service.fazer_login(db, dados)


@router.get(
    "/me",
    response_model=UsuarioResponse,
    summary="Retorna o usuario atualmente autenticado",
)
def me(usuario: models.Usuario = Depends(get_usuario_atual)) -> UsuarioResponse:
    return auth_service.montar_resposta_usuario(usuario)
