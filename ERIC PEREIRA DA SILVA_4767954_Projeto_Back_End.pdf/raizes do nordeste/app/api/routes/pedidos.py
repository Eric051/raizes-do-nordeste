"""
Rotas do recurso /pedidos.

Endpoints:
- POST   /pedidos                    cria um pedido (qualquer autenticado)
- GET    /pedidos                    lista pedidos (cliente ve so os proprios)
- GET    /pedidos/{id}               detalhes (cliente ve so os proprios)
- PATCH  /pedidos/{id}/status        muda status (staff; cliente so cancela)
- DELETE /pedidos/{id}               cancela (atalho pra status=CANCELADO)

Filtros suportados na listagem:
- ?canalPedido=TOTEM
- ?status=PAGO
- ?cliente_id=10  (so pra staff)
- ?unidade_id=2
- ?page=1&limit=20
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, status as http_status
from sqlalchemy.orm import Session

from app.api.dependencies import get_usuario_atual
from app.api.schemas.comuns import PageMeta
from app.api.schemas.pedido import (
    PedidoCreate,
    PedidoListResponse,
    PedidoResponse,
    StatusPedidoUpdate,
)
from app.application.services import pedido_service
from app.domain.entities.enums import CanalPedido, StatusPedido
from app.infrastructure.database import models
from app.infrastructure.database.connection import get_db


router = APIRouter(prefix="/pedidos", tags=["Pedidos"])


@router.post(
    "",
    response_model=PedidoResponse,
    status_code=http_status.HTTP_201_CREATED,
    summary="Cria um novo pedido",
    description=(
        "Cria um pedido em uma unidade, registrando o canal de origem "
        "(canalPedido). Valida disponibilidade no cardapio e estoque, "
        "calcula totais e aplica promocao se houver codigo. O pedido "
        "nasce com status AGUARDANDO_PAGAMENTO."
    ),
)
def criar(
    dados: PedidoCreate,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_usuario_atual),
):
    pedido = pedido_service.criar_pedido(db, dados, usuario)
    return pedido_service.montar_resposta(pedido)


@router.get(
    "",
    response_model=PedidoListResponse,
    summary="Lista pedidos com filtros",
)
def listar(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    canalPedido: Optional[CanalPedido] = Query(
        None,
        description="Filtra pelo canal de origem do pedido (APP, TOTEM, BALCAO, PICKUP, WEB).",
    ),
    status: Optional[StatusPedido] = Query(None, description="Filtra por status do pedido."),
    cliente_id: Optional[int] = Query(None, gt=0, description="So aplicavel a perfis staff."),
    unidade_id: Optional[int] = Query(None, gt=0),
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_usuario_atual),
):
    items, total = pedido_service.listar_pedidos(
        db,
        usuario=usuario,
        page=page,
        limit=limit,
        canal_pedido=canalPedido,
        status_filtro=status,
        cliente_id=cliente_id,
        unidade_id=unidade_id,
    )
    return PedidoListResponse(
        items=[pedido_service.montar_resposta(p) for p in items],
        meta=PageMeta.calcular(page, limit, total),
    )


@router.get(
    "/{pedido_id}",
    response_model=PedidoResponse,
    summary="Detalhes de um pedido",
)
def detalhes(
    pedido_id: int,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_usuario_atual),
):
    pedido = pedido_service.buscar_pedido(db, pedido_id, usuario)
    return pedido_service.montar_resposta(pedido)


@router.patch(
    "/{pedido_id}/status",
    response_model=PedidoResponse,
    summary="Atualiza o status do pedido",
    description=(
        "Aplica uma transicao de status. As transicoes permitidas sao "
        "validadas pela regra de dominio. Quando o pedido vai pra PAGO "
        "o estoque eh baixado automaticamente; quando eh CANCELADO "
        "depois de PAGO/EM_PREPARO/PRONTO, o estoque eh estornado. "
        "Cliente so pode cancelar o proprio pedido por aqui."
    ),
)
def atualizar_status(
    pedido_id: int,
    dados: StatusPedidoUpdate,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_usuario_atual),
):
    pedido = pedido_service.mudar_status(db, pedido_id, dados.status, usuario)
    return pedido_service.montar_resposta(pedido)


@router.delete(
    "/{pedido_id}",
    response_model=PedidoResponse,
    summary="Cancela um pedido",
    description=(
        "Atalho semantico pra PATCH /pedidos/{id}/status com status=CANCELADO."
    ),
)
def cancelar(
    pedido_id: int,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_usuario_atual),
):
    pedido = pedido_service.cancelar_pedido(db, pedido_id, usuario)
    return pedido_service.montar_resposta(pedido)
