"""
Service do programa de fidelidade.

Pontos sao creditados quando um pedido vai pra PAGO. Resgate eh feito
no momento da criacao de um novo pedido (via campo pontos_resgate).

Toda mexida gera uma MovimentacaoPontos com tipo:
* CREDITO: pontos ganhos num pedido pago
* RESGATE: pontos usados como desconto num pedido novo
* AJUSTE: estornos de cancelamento ou correcao manual

Os pontos nas movimentacoes sao sempre POSITIVOS. O tipo eh quem diz
se foi entrada ou saida do saldo. Facilita relatorios depois.

LGPD:
* Sem consentimento ativo, nao credita nem deixa resgatar.
* Cancelamento de conta com zera de saldo ficou pra evolucao futura
  (esta na conclusao do PDF).
"""
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.domain.entities.enums import PerfilUsuario, TipoMovimentacaoPontos
from app.domain.exceptions import (
    ConflitoDeNegocio,
    ConsentimentoLGPDNecessario,
    SemPermissao,
)
from app.domain.regras.pedido import (
    calcular_desconto_resgate,
    calcular_pontos_a_creditar,
)
from app.infrastructure.database import models


# ---------------------------------------------------------
# helper interno
# ---------------------------------------------------------

def _achar_ou_criar_carteira(
    db: Session, cliente_id: int
) -> models.PontosFidelidade:
    """
    Pega o registro de PontosFidelidade do cliente. Se nao existir,
    cria com saldo zero. Caso raro mas pode acontecer pra usuarios
    antigos.
    """
    carteira = (
        db.query(models.PontosFidelidade)
        .filter_by(cliente_id=cliente_id)
        .first()
    )
    if carteira:
        return carteira
    carteira = models.PontosFidelidade(cliente_id=cliente_id, saldo=0)
    db.add(carteira)
    db.flush()
    return carteira


# ---------------------------------------------------------
# consultas (usadas pelas rotas)
# ---------------------------------------------------------

def consultar_saldo(db: Session, cliente_id: int) -> int:
    carteira = (
        db.query(models.PontosFidelidade)
        .filter_by(cliente_id=cliente_id)
        .first()
    )
    return carteira.saldo if carteira else 0


def listar_historico(
    db: Session, cliente_id: int, page: int = 1, limit: int = 20
) -> tuple[list[models.MovimentacaoPontos], int]:
    query = db.query(models.MovimentacaoPontos).filter_by(cliente_id=cliente_id)
    total = query.count()
    items = (
        query.order_by(models.MovimentacaoPontos.criado_em.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return items, total


# ---------------------------------------------------------
# resgate (chamado pela criacao de pedido)
# ---------------------------------------------------------

def calcular_desconto_se_houver(
    cliente: models.Usuario, pontos: int
) -> Decimal:
    """
    So calcula o desconto que `pontos` resgatariam, sem mexer no banco.
    Se o cliente nao tem consentimento LGPD, levanta excecao.
    Usado durante o calculo do total do pedido.
    """
    if pontos <= 0:
        return Decimal("0.00")

    if cliente.perfil != PerfilUsuario.CLIENTE:
        raise SemPermissao(
            "So usuarios com perfil CLIENTE podem usar fidelidade.",
        )

    if not cliente.consentimento_lgpd:
        raise ConsentimentoLGPDNecessario(
            "Eh necessario consentimento LGPD ativo pra usar pontos de fidelidade.",
            details=[{"field": "consentimento_lgpd", "issue": "obrigatorio"}],
        )

    return calcular_desconto_resgate(pontos)


def aplicar_resgate(
    db: Session,
    cliente: models.Usuario,
    pontos: int,
    pedido_id: int,
    commit: bool = False,
) -> None:
    """
    Debita pontos do saldo e registra MovimentacaoPontos de RESGATE
    apontando pro pedido. Tem que ser chamado depois que o pedido
    foi criado (precisa ter o id pra linkar a movimentacao).
    """
    if pontos <= 0:
        return

    if not cliente.consentimento_lgpd:
        raise ConsentimentoLGPDNecessario(
            "Eh necessario consentimento LGPD ativo pra usar pontos de fidelidade.",
            details=[{"field": "consentimento_lgpd", "issue": "obrigatorio"}],
        )

    carteira = _achar_ou_criar_carteira(db, cliente.id)
    if carteira.saldo < pontos:
        raise ConflitoDeNegocio(
            f"Saldo de pontos insuficiente. Disponivel: {carteira.saldo}, "
            f"solicitado: {pontos}.",
            details=[{"field": "pontos_resgate", "issue": "saldo insuficiente"}],
        )

    carteira.saldo -= pontos

    db.add(
        models.MovimentacaoPontos(
            cliente_id=cliente.id,
            tipo=TipoMovimentacaoPontos.RESGATE,
            pontos=pontos,
            descricao=f"Resgate em pedido {pedido_id}",
            pedido_id=pedido_id,
        )
    )

    if commit:
        db.commit()
    else:
        db.flush()


# ---------------------------------------------------------
# credito (chamado quando pedido vai pra PAGO)
# ---------------------------------------------------------

def creditar_por_pagamento(
    db: Session,
    cliente_id: int,
    pedido_id: int,
    total_pedido: Decimal,
    commit: bool = False,
) -> int:
    """
    Credita pontos quando um pedido eh pago. Devolve a quantidade de
    pontos que foi creditada.

    Se o cliente nao tem consentimento LGPD, NAO credita (mas tambem
    nao falha o pagamento). Eh proposital: o cliente pode optar por
    nao participar do programa sem perder a capacidade de comprar.
    """
    cliente = db.query(models.Usuario).filter_by(id=cliente_id).first()
    if not cliente or not cliente.consentimento_lgpd:
        return 0

    pontos = calcular_pontos_a_creditar(total_pedido)
    if pontos <= 0:
        return 0

    carteira = _achar_ou_criar_carteira(db, cliente_id)
    carteira.saldo += pontos

    db.add(
        models.MovimentacaoPontos(
            cliente_id=cliente_id,
            tipo=TipoMovimentacaoPontos.CREDITO,
            pontos=pontos,
            descricao=f"Pontos do pedido {pedido_id}",
            pedido_id=pedido_id,
        )
    )

    if commit:
        db.commit()

    return pontos


# ---------------------------------------------------------
# estorno (cancelamento de pedido)
# ---------------------------------------------------------

def estornar_pedido(
    db: Session,
    pedido: models.Pedido,
    commit: bool = False,
) -> None:
    """
    Reverte movimentacoes de pontos quando um pedido eh cancelado:
    * se o pedido creditou pontos: tira do saldo (limitado ao saldo
      atual pra nao deixar negativo. Se o cliente ja gastou os pontos
      creditados, registra a movimentacao mesmo assim pra ficar com
      a rastreabilidade certinha).
    * se o pedido resgatou pontos: devolve pro saldo.
    """
    if pedido.pontos_creditados <= 0 and pedido.pontos_resgatados <= 0:
        return

    carteira = _achar_ou_criar_carteira(db, pedido.cliente_id)

    if pedido.pontos_creditados > 0:
        # nao deixa o saldo ir abaixo de zero (a CheckConstraint do banco
        # impede de qualquer jeito, mas defendo aqui pra evitar erro feio)
        debito_efetivo = min(pedido.pontos_creditados, carteira.saldo)
        carteira.saldo -= debito_efetivo
        db.add(
            models.MovimentacaoPontos(
                cliente_id=pedido.cliente_id,
                tipo=TipoMovimentacaoPontos.AJUSTE,
                pontos=pedido.pontos_creditados,
                descricao=f"Estorno de credito do pedido {pedido.id} (cancelado)",
                pedido_id=pedido.id,
            )
        )

    if pedido.pontos_resgatados > 0:
        carteira.saldo += pedido.pontos_resgatados
        db.add(
            models.MovimentacaoPontos(
                cliente_id=pedido.cliente_id,
                tipo=TipoMovimentacaoPontos.AJUSTE,
                pontos=pedido.pontos_resgatados,
                descricao=f"Devolucao de resgate do pedido {pedido.id} (cancelado)",
                pedido_id=pedido.id,
            )
        )

    if commit:
        db.commit()
