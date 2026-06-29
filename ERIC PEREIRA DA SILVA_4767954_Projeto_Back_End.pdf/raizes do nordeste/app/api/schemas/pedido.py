"""
Schemas Pydantic do recurso Pedido.

O Pedido eh o nucleo do sistema. Tem:
- canal_pedido (OBRIGATORIO, requisito da multicanalidade)
- itens (lista, com snapshot de preco)
- status (regra de transicao validada no dominio)
- metodo_pagamento + integracao mock (Etapa 7)
- promocao por codigo + resgate de pontos da fidelidade (Etapa 8)
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.comuns import PageMeta
from app.domain.entities.enums import (
    CanalPedido,
    MetodoPagamento,
    StatusPedido,
)


# ----------------------------------------------------------------------
# Itens do pedido
# ----------------------------------------------------------------------

class ItemPedidoCreate(BaseModel):
    produto_id: int = Field(..., gt=0, examples=[1])
    quantidade: int = Field(..., gt=0, examples=[2])


class ItemPedidoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    produto_id: int
    nome_produto: Optional[str] = None
    quantidade: int
    preco_unitario: Decimal
    subtotal_item: Decimal


# ----------------------------------------------------------------------
# Pedido
# ----------------------------------------------------------------------

class PedidoCreate(BaseModel):
    """
    Dados para criar um pedido.

    O canal_pedido eh obrigatorio (requisito de multicanalidade).
    O cliente_id eh opcional: se nao vier, usa o usuario logado. Quando
    o requisitante nao for um cliente (ex: atendente atendendo no
    balcao), pode passar cliente_id explicitamente.
    """
    unidade_id: int = Field(..., gt=0, examples=[1])
    canal_pedido: CanalPedido = Field(..., examples=["TOTEM"])
    metodo_pagamento: MetodoPagamento = Field(
        default=MetodoPagamento.MOCK,
        examples=["MOCK"],
    )
    cliente_id: Optional[int] = Field(
        None,
        gt=0,
        description=(
            "ID do cliente. Se nao informado, usa o usuario logado. "
            "Usuarios com perfil CLIENTE so podem criar pedidos pra si "
            "mesmos, qualquer cliente_id diferente eh ignorado."
        ),
    )
    itens: list[ItemPedidoCreate] = Field(..., min_length=1)
    codigo_promocao: Optional[str] = Field(None, max_length=50, examples=["CUSCUZ20"])
    pontos_resgate: int = Field(
        default=0,
        ge=0,
        description="Pontos de fidelidade a resgatar como desconto (Etapa 8).",
    )
    observacoes: Optional[str] = Field(None, max_length=500)


class StatusPedidoUpdate(BaseModel):
    """Body do PATCH /pedidos/{id}/status."""
    status: StatusPedido = Field(..., examples=["EM_PREPARO"])


class PedidoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_id: int
    unidade_id: int
    canal_pedido: CanalPedido
    status: StatusPedido
    metodo_pagamento: MetodoPagamento
    subtotal: Decimal
    desconto: Decimal
    total: Decimal
    pontos_resgatados: int
    pontos_creditados: int
    promocao_id: Optional[int]
    observacoes: Optional[str]
    itens: list[ItemPedidoResponse]
    criado_em: datetime
    atualizado_em: Optional[datetime] = None


class PedidoListResponse(BaseModel):
    items: list[PedidoResponse]
    meta: PageMeta
