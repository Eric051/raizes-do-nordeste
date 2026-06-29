"""
Schemas Pydantic do recurso Cardapio (sub-recurso de Unidade).

O cardapio eh uma tabela de associacao entre produto e unidade que
guarda disponibilidade e preco local. Quando um cliente abre o
cardapio de uma unidade, ele ve os dados do produto + esses extras.
"""
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.domain.entities.enums import CategoriaProduto


class CardapioItemResponse(BaseModel):
    """
    Item visto pelo cliente ao consultar o cardapio de uma unidade.
    Combina dados do produto com a info de disponibilidade e preco
    aplicavel naquela unidade.
    """
    model_config = ConfigDict(from_attributes=True)

    produto_id: int
    nome: str
    descricao: Optional[str]
    categoria: CategoriaProduto
    preco: Decimal = Field(..., description="Preco efetivo (preco_local se houver, senao preco_base)")
    preco_base: Decimal
    preco_local: Optional[Decimal]
    disponivel: bool
    sazonal: bool


class CardapioCreate(BaseModel):
    """Adiciona um produto ao cardapio de uma unidade."""
    produto_id: int = Field(..., gt=0)
    preco_local: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    disponivel: bool = True


class CardapioUpdate(BaseModel):
    """Atualiza disponibilidade ou preco local de um item do cardapio."""
    preco_local: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    disponivel: Optional[bool] = None
