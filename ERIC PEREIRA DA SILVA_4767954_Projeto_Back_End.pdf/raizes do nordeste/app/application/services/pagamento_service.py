"""
Service de pagamento.

Esse modulo fecha o fluxo critico do MVP exigido pelo roteiro:

    pedido -> pagamento mock -> atualizacao de status

Quando o cliente solicita pagamento de um pedido em
AGUARDANDO_PAGAMENTO (ou retentativa apos PAGAMENTO_RECUSADO):

1. valida que o pedido pode receber pagamento
2. chama o gateway mock com retry simples (max 2 tentativas)
3. registra a tentativa em `pagamentos`
4. atualiza o status do pedido conforme o resultado:
   - APROVADO -> PAGO (e isso baixa o estoque + credita pontos)
   - RECUSADO -> PAGAMENTO_RECUSADO (cliente pode tentar de novo)
   - ERRO/timeout final -> PAGAMENTO_RECUSADO + 502 pro cliente

A mudanca de status do pedido eh feita via
`pedido_service.mudar_status_sistema`, que NAO checa permissao do
usuario (porque a transicao foi consequencia da resposta do gateway,
nao foi acao manual do cliente).

Toda tentativa de pagamento gera log de auditoria.
"""
import json
from typing import Optional

from sqlalchemy.orm import Session

from app.api.schemas.pagamento import PagamentoCreate, PagamentoResponse
from app.application.services import pedido_service
from app.domain.entities.enums import (
    PerfilUsuario,
    StatusPagamento,
    StatusPedido,
)
from app.domain.exceptions import (
    ConflitoDeNegocio,
    FalhaIntegracaoExterna,
    RecursoNaoEncontrado,
)
from app.infrastructure.audit.audit_logger import registrar_log
from app.infrastructure.database import models
from app.infrastructure.external_services.payment_gateway_mock import (
    FalhaTransientGateway,
    processar_pagamento,
)


# numero maximo de tentativas em caso de falha transient
MAX_TENTATIVAS = 2


# ---------------------------------------------------------
# helpers
# ---------------------------------------------------------

def _para_resposta(p: models.Pagamento) -> PagamentoResponse:
    return PagamentoResponse(
        id=p.id,
        pedido_id=p.pedido_id,
        valor=p.valor,
        metodo=p.metodo,
        status=p.status,
        referencia_externa=p.referencia_externa,
        tentativas=p.tentativas,
        criado_em=p.criado_em,
    )


def _validar_pedido_pagavel(
    db: Session, pedido_id: int, usuario: models.Usuario
) -> models.Pedido:
    pedido = db.query(models.Pedido).filter_by(id=pedido_id).first()
    if not pedido:
        raise RecursoNaoEncontrado(f"Pedido {pedido_id} nao encontrado.")

    if usuario.perfil == PerfilUsuario.CLIENTE and pedido.cliente_id != usuario.id:
        # 404 ao inves de 403 pra nao revelar que o pedido existe
        raise RecursoNaoEncontrado(f"Pedido {pedido_id} nao encontrado.")

    # ja tem pagamento aprovado pra esse pedido?
    aprovado_existente = (
        db.query(models.Pagamento)
        .filter_by(pedido_id=pedido_id, status=StatusPagamento.APROVADO)
        .first()
    )
    if aprovado_existente:
        raise ConflitoDeNegocio(
            "Esse pedido ja possui um pagamento aprovado.",
            details=[{"field": "pedido_id", "issue": "ja pago"}],
        )

    if pedido.status not in (
        StatusPedido.AGUARDANDO_PAGAMENTO,
        StatusPedido.PAGAMENTO_RECUSADO,
    ):
        raise ConflitoDeNegocio(
            f"Pedido com status {pedido.status.value} nao pode receber pagamento.",
            details=[{"field": "status", "issue": "fora da janela de pagamento"}],
        )

    return pedido


# ---------------------------------------------------------
# solicitar pagamento
# ---------------------------------------------------------

def solicitar_pagamento(
    db: Session,
    pedido_id: int,
    dados: PagamentoCreate,
    usuario: models.Usuario,
) -> PagamentoResponse:
    """Tenta pagar o pedido via gateway mock e atualiza o status."""
    pedido = _validar_pedido_pagavel(db, pedido_id, usuario)

    # se ta tentando pagar de novo apos uma recusa, volta pra AGUARDANDO_PAGAMENTO
    if pedido.status == StatusPedido.PAGAMENTO_RECUSADO:
        pedido_service.mudar_status_sistema(
            db, pedido_id, StatusPedido.AGUARDANDO_PAGAMENTO, responsavel_id=usuario.id
        )

    # tentativa com retry
    tentativas = 0
    ultima_falha: Optional[Exception] = None
    resposta = None
    while tentativas < MAX_TENTATIVAS:
        tentativas += 1
        try:
            resposta = processar_pagamento(
                valor=pedido.total,
                metodo=pedido.metodo_pagamento.value,
                pedido_id=pedido.id,
                forcar_resultado=dados.forcar_resultado,
            )
            break
        except FalhaTransientGateway as e:
            ultima_falha = e

    # cenario 1: gateway falhou em todas as tentativas
    if resposta is None:
        pagamento = models.Pagamento(
            pedido_id=pedido.id,
            valor=pedido.total,
            metodo=pedido.metodo_pagamento,
            status=StatusPagamento.ERRO,
            referencia_externa=None,
            payload_resposta=json.dumps({"erro": str(ultima_falha)}),
            tentativas=tentativas,
        )
        db.add(pagamento)
        db.commit()
        db.refresh(pagamento)
        registrar_log(
            db,
            acao="PAGAMENTO_ERRO",
            usuario_id=usuario.id,
            recurso="PEDIDO",
            recurso_id=pedido.id,
            dados={
                "tentativas": tentativas,
                "erro": str(ultima_falha),
            },
            commit=True,
        )
        # marca como recusado pra o cliente poder tentar de novo
        pedido_service.mudar_status_sistema(
            db, pedido_id, StatusPedido.PAGAMENTO_RECUSADO, responsavel_id=usuario.id
        )
        raise FalhaIntegracaoExterna(
            "Falha na comunicacao com o gateway de pagamento apos varias tentativas.",
            details=[{"field": "gateway", "issue": str(ultima_falha)}],
        )

    # cenario 2: tivemos resposta (aprovada ou recusada)
    pagamento = models.Pagamento(
        pedido_id=pedido.id,
        valor=pedido.total,
        metodo=pedido.metodo_pagamento,
        status=resposta.status,
        referencia_externa=resposta.referencia_externa,
        payload_resposta=json.dumps(resposta.payload_bruto, default=str),
        tentativas=tentativas,
    )
    db.add(pagamento)
    db.commit()
    db.refresh(pagamento)

    registrar_log(
        db,
        acao="PAGAMENTO_APROVADO" if resposta.aprovado else "PAGAMENTO_RECUSADO",
        usuario_id=usuario.id,
        recurso="PEDIDO",
        recurso_id=pedido.id,
        dados={
            "pagamento_id": pagamento.id,
            "valor": str(pagamento.valor),
            "metodo": pagamento.metodo.value,
            "referencia_externa": pagamento.referencia_externa,
            "tentativas": tentativas,
        },
        commit=True,
    )

    # atualiza status do pedido. mudar_status_sistema commita por dentro
    # e baixa estoque + credita pontos automatic. quando vai pra PAGO.
    if resposta.aprovado:
        pedido_service.mudar_status_sistema(
            db, pedido_id, StatusPedido.PAGO, responsavel_id=usuario.id
        )
    else:
        pedido_service.mudar_status_sistema(
            db, pedido_id, StatusPedido.PAGAMENTO_RECUSADO, responsavel_id=usuario.id
        )

    return _para_resposta(pagamento)


# ---------------------------------------------------------
# consultar tentativas
# ---------------------------------------------------------

def listar_pagamentos(
    db: Session, pedido_id: int, usuario: models.Usuario
) -> list[PagamentoResponse]:
    """Devolve todas as tentativas de pagamento de um pedido."""
    pedido = db.query(models.Pedido).filter_by(id=pedido_id).first()
    if not pedido:
        raise RecursoNaoEncontrado(f"Pedido {pedido_id} nao encontrado.")
    if usuario.perfil == PerfilUsuario.CLIENTE and pedido.cliente_id != usuario.id:
        raise RecursoNaoEncontrado(f"Pedido {pedido_id} nao encontrado.")

    pagamentos = (
        db.query(models.Pagamento)
        .filter_by(pedido_id=pedido_id)
        .order_by(models.Pagamento.criado_em.desc())
        .all()
    )
    return [_para_resposta(p) for p in pagamentos]
