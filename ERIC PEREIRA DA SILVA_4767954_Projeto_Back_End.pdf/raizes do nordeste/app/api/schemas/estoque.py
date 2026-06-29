"""
Schemas Pydantic do recurso Estoque.

Estoque eh um sub-recurso de Unidade. Cada par (unidade, produto)
tem um saldo, e toda alteracao gera uma MovimentacaoEstoque com
o tipo (ENTRADA, SAIDA, AJUSTE).
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.comuns import PageMeta
from app.domain.entities.enums import TipoMovimentacaoEstoque


class SaldoEstoqueResponse(BaseModel):
    """Saldo atual de um produto numa unidade."""
    model_config = ConfigDict(from_attributes=True)

    unidade_id: int
    produto_id: int
    nome_produto: str
    quantidade: int
    atualizado_em: Optional[datetime] = None


class SaldoListResponse(BaseModel):
    items: list[SaldoEstoqueResponse]
    meta: PageMeta


class MovimentacaoEstoqueCreate(BaseModel):
    """
    Cria uma movimentacao de estoque.

    - ENTRADA: soma `quantidade` ao saldo atual
    - SAIDA: subtrai `quantidade` (falha com 409 se nao houver saldo)
    - AJUSTE: define o saldo final como `quantidade` (usado pra
      corrigir divergencias apos contagem fisica)
    """
    produto_id: int = Field(..., gt=0)
    tipo: TipoMovimentacaoEstoque = Field(..., examples=["ENTRADA"])
    quantidade: int = Field(..., gt=0, examples=[10])
    motivo: Optional[str] = Field(
        None, max_length=255, examples=["Reposicao semanal"]
    )


class MovimentacaoEstoqueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    estoque_id: int
    tipo: TipoMovimentacaoEstoque
    quantidade: int
    motivo: Optional[str]
    responsavel_id: Optional[int]
    pedido_id: Optional[int]
    criado_em: datetime


class MovimentacaoListResponse(BaseModel):
    items: list[MovimentacaoEstoqueResponse]
    meta: PageMeta
