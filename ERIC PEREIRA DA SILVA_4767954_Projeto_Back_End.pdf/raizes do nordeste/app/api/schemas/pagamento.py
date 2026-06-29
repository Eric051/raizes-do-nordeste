"""
Schemas Pydantic do recurso Pagamento.

O pagamento eh sempre uma tentativa associada a um pedido. Pode haver
mais de uma tentativa por pedido (ex: primeira recusada, cliente
tenta de novo).

Por seguranca, o body NAO recebe dados de cartao. So um campo opcional
`forcar_resultado` que serve pra controlar o mock em testes.
"""
from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.domain.entities.enums import MetodoPagamento, StatusPagamento


class PagamentoCreate(BaseModel):
    """
    Body opcional ao solicitar pagamento.

    Em producao, o `forcar_resultado` nao existiria. Aqui ele eh util
    pra escrever testes deterministicos no Postman, simulando os
    cenarios de aprovacao, recusa e falha de comunicacao.
    """
    forcar_resultado: Optional[Literal["APROVADO", "RECUSADO", "ERRO"]] = Field(
        default=None,
        description=(
            "So pra testes/mock. Forca o resultado da chamada ao gateway. "
            "ERRO simula falha transient (timeout) e dispara o retry."
        ),
        examples=["APROVADO"],
    )


class PagamentoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pedido_id: int
    valor: Decimal
    metodo: MetodoPagamento
    status: StatusPagamento
    referencia_externa: Optional[str] = None
    tentativas: int
    criado_em: datetime
