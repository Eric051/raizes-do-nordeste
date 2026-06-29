"""
Schemas compartilhados pela API.

O RespostaErro define o formato unico de erro JSON usado em toda a
aplicacao, atendendo o requisito de "padrao de erro consistente"
do roteiro.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DetalheErro(BaseModel):
    """Detalhe especifico de um erro, geralmente associado a um campo."""
    field: Optional[str] = None
    issue: str


class RespostaErro(BaseModel):
    """Formato padrao de erro retornado pela API."""
    error: str = Field(..., description="Codigo do erro (ex: ESTOQUE_INSUFICIENTE)")
    message: str = Field(..., description="Mensagem legivel pro usuario")
    details: list[DetalheErro] = Field(default_factory=list)
    timestamp: datetime = Field(..., description="Quando o erro aconteceu (UTC)")
    path: str = Field(..., description="Endpoint que gerou o erro")


class PageMeta(BaseModel):
    """Metadados de paginacao usados nas listagens."""
    page: int = Field(..., ge=1)
    limit: int = Field(..., ge=1)
    total: int = Field(..., ge=0)
    total_pages: int = Field(..., ge=0)

    @classmethod
    def calcular(cls, page: int, limit: int, total: int) -> "PageMeta":
        total_pages = (total + limit - 1) // limit if limit > 0 else 0
        return cls(page=page, limit=limit, total=total, total_pages=total_pages)
