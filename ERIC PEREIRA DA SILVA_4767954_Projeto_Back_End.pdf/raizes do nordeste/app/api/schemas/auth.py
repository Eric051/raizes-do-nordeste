"""
Schemas Pydantic dos endpoints de autenticacao e do recurso usuario.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.entities.enums import PerfilUsuario


class RegisterRequest(BaseModel):
    """Dados de auto-cadastro de cliente."""
    nome: str = Field(..., min_length=2, max_length=150, examples=["Maria da Silva"])
    email: EmailStr = Field(..., examples=["maria@exemplo.com"])
    senha: str = Field(
        ...,
        min_length=8,
        max_length=72,  # limite do bcrypt
        description="Minimo 8 caracteres. Maximo 72 (limite do bcrypt).",
        examples=["MinhaSenha@123"],
    )
    cpf: Optional[str] = Field(None, max_length=14, examples=["12345678900"])
    consentimento_lgpd: bool = Field(
        ...,
        description=(
            "Marca como true pra autorizar o tratamento dos dados conforme a LGPD. "
            "Sem consentimento, a conta nao eh criada."
        ),
        examples=[True],
    )


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., examples=["cliente@exemplo.com"])
    senha: str = Field(..., examples=["Cliente@123"])


class UsuarioResponse(BaseModel):
    """Representacao publica de um usuario. Nunca devolve a senha."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: EmailStr
    perfil: PerfilUsuario
    consentimento_lgpd: bool
    cpf_mascarado: Optional[str] = None
    ativo: bool
    criado_em: datetime


class TokenResponse(BaseModel):
    """Resposta do login com o JWT e os dados do usuario autenticado."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = Field(..., description="Tempo de vida do token em segundos")
    usuario: UsuarioResponse
