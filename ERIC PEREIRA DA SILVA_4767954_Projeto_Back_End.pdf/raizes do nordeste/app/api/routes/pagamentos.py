"""
Rotas do recurso Pagamento (sub-recurso de /pedidos).

URLs:
- POST /pedidos/{pedido_id}/pagamentos    solicita pagamento via gateway mock
- GET  /pedidos/{pedido_id}/pagamentos    lista tentativas de pagamento

Permissoes: cliente paga proprio pedido; staff pode pagar pedido de
qualquer cliente (uso tipico em atendimento de balcao).
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_usuario_atual
from app.api.schemas.pagamento import PagamentoCreate, PagamentoResponse
from app.application.services import pagamento_service
from app.infrastructure.database import models
from app.infrastructure.database.connection import get_db


router = APIRouter(prefix="/pedidos/{pedido_id}/pagamentos", tags=["Pagamentos"])


@router.post(
    "",
    response_model=PagamentoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Solicita o pagamento de um pedido",
    description=(
        "Chama o gateway mock e atualiza o status do pedido conforme "
        "o resultado. Se aprovado, o pedido vai pra PAGO e o estoque "
        "eh baixado automaticamente. Se recusado, fica como "
        "PAGAMENTO_RECUSADO e o cliente pode tentar de novo. Em caso "
        "de falha de comunicacao, ha retry interno (max 2 tentativas)."
    ),
)
def solicitar(
    pedido_id: int,
    dados: PagamentoCreate = PagamentoCreate(),
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_usuario_atual),
):
    return pagamento_service.solicitar_pagamento(db, pedido_id, dados, usuario)


@router.get(
    "",
    response_model=list[PagamentoResponse],
    summary="Lista as tentativas de pagamento de um pedido",
)
def listar(
    pedido_id: int,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_usuario_atual),
):
    return pagamento_service.listar_pagamentos(db, pedido_id, usuario)
