"""
Schemas Pydantic do recurso Produto.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.comuns import PageMeta
from app.domain.entities.enums import CategoriaProduto


class ProdutoBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=150, examples=["Tapioca de Queijo Coalho"])
    descricao: Optional[str] = Field(None, examples=["Tapioca recheada com queijo coalho artesanal"])
    preco_base: Decimal = Field(..., ge=0, decimal_places=2, examples=["12.50"])
    categoria: CategoriaProduto = Field(default=CategoriaProduto.OUTRO)
    sazonal: bool = Field(default=False, description="Se eh sazonal (ex.: comidas juninas)")


class ProdutoCreate(ProdutoBase):
    pass


class ProdutoUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=2, max_length=150)
    descricao: Optional[str] = None
    preco_base: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    categoria: Optional[CategoriaProduto] = None
    sazonal: Optional[bool] = None
    ativo: Optional[bool] = None


class ProdutoResponse(ProdutoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ativo: bool
    criado_em: datetime


class ProdutoListResponse(BaseModel):
    items: list[ProdutoResponse]
    meta: PageMeta
