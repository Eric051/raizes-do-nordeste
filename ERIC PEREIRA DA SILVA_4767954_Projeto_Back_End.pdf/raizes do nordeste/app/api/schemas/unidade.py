"""
Schemas Pydantic do recurso Unidade.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.comuns import PageMeta


class UnidadeBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=150, examples=["Raizes Recife - Boa Viagem"])
    cidade: str = Field(..., min_length=2, max_length=100, examples=["Recife"])
    estado: str = Field(..., min_length=2, max_length=2, examples=["PE"])
    endereco: Optional[str] = Field(None, max_length=255, examples=["Av. Boa Viagem, 1234"])


class UnidadeCreate(UnidadeBase):
    """Dados pra cadastrar uma nova unidade."""
    pass


class UnidadeUpdate(BaseModel):
    """Atualizacao parcial de unidade. Todos os campos sao opcionais."""
    nome: Optional[str] = Field(None, min_length=2, max_length=150)
    cidade: Optional[str] = Field(None, min_length=2, max_length=100)
    estado: Optional[str] = Field(None, min_length=2, max_length=2)
    endereco: Optional[str] = Field(None, max_length=255)
    ativo: Optional[bool] = None


class UnidadeResponse(UnidadeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ativo: bool
    criado_em: datetime


class UnidadeListResponse(BaseModel):
    items: list[UnidadeResponse]
    meta: PageMeta
