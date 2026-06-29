"""
Service de pedidos.

Esse modulo orquestra o fluxo principal do sistema:

    criar pedido -> aguardando pagamento -> pago -> em preparo -> pronto -> entregue

Coisa importante de saber:
* a baixa de estoque NAO acontece na criacao do pedido. Ela acontece
  quando o pedido vai pra PAGO. Isso evita ter que estornar pra todo
  pedido cancelado antes de pagar (que eh o caso comum).
* quando cancela um pedido pago, o estoque eh estornado.
* quando o pedido vai pra PAGO, pontos de fidelidade sao creditados
  automaticamente (so se o cliente tiver consentimento LGPD).
* quando cancela, pontos resgatados voltam pro saldo e creditados saem.
* toda criacao e mudanca de status registra log de auditoria.

TODO: implementar reserva de estoque na criacao do pedido (hoje eh
otimista). Em horario de pico, dois clientes podem comprar o mesmo
ultimo produto. Pra MVP academico nao tem problema.
"""
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.api.schemas.pedido import (
    ItemPedidoResponse,
    PedidoCreate,
    PedidoResponse,
)
from app.application.services import estoque_service, fidelidade_service
from app.domain.entities.enums import (
    CanalPedido,
    PerfilUsuario,
    StatusPedido,
    TipoMovimentacaoEstoque,
)
from app.domain.exceptions import (
    ConflitoDeNegocio,
    DadosInvalidos,
    RecursoNaoEncontrado,
    SemPermissao,
)
from app.domain.regras.pedido import (
    aplicar_desconto,
    calcular_subtotal,
    validar_transicao,
)
from app.infrastructure.audit.audit_logger import registrar_log
from app.infrastructure.database import models


# ---------------------------------------------------------
# helper de resposta
# ---------------------------------------------------------

def montar_resposta(pedido: models.Pedido) -> PedidoResponse:
    """Pega o model do banco e monta o PedidoResponse pra mandar pro cliente."""
    itens = []
    for item in pedido.itens:
        nome = item.produto.nome if item.produto else None
        itens.append(
            ItemPedidoResponse(
                produto_id=item.produto_id,
                nome_produto=nome,
                quantidade=item.quantidade,
                preco_unitario=item.preco_unitario,
                subtotal_item=item.subtotal_item,
            )
        )
    return PedidoResponse(
        id=pedido.id,
        cliente_id=pedido.cliente_id,
        unidade_id=pedido.unidade_id,
        canal_pedido=pedido.canal_pedido,
        status=pedido.status,
        metodo_pagamento=pedido.metodo_pagamento,
        subtotal=pedido.subtotal,
        desconto=pedido.desconto,
        total=pedido.total,
        pontos_resgatados=pedido.pontos_resgatados,
        pontos_creditados=pedido.pontos_creditados,
        promocao_id=pedido.promocao_id,
        observacoes=pedido.observacoes,
        itens=itens,
        criado_em=pedido.criado_em,
        atualizado_em=pedido.atualizado_em,
    )


# ---------------------------------------------------------
# criacao do pedido
# ---------------------------------------------------------

def _resolver_cliente(
    db: Session, dados: PedidoCreate, usuario: models.Usuario
) -> models.Usuario:
    """
    Decide quem eh o cliente do pedido. Cliente comum so faz pedido
    pra ele mesmo. Staff (atendente, gerente etc) pode passar
    cliente_id pra atender no balcao.
    """
    if usuario.perfil == PerfilUsuario.CLIENTE:
        return usuario

    cliente_id = dados.cliente_id or usuario.id
    cliente = db.query(models.Usuario).filter_by(id=cliente_id).first()
    if not cliente:
        raise RecursoNaoEncontrado(f"Cliente {cliente_id} nao encontrado.")
    if cliente.perfil != PerfilUsuario.CLIENTE:
        raise DadosInvalidos(
            "O cliente_id informado nao pertence a um usuario com perfil CLIENTE.",
            details=[{"field": "cliente_id", "issue": "perfil incompativel"}],
        )
    return cliente


def _validar_unidade(db: Session, unidade_id: int) -> models.Unidade:
    unidade = db.query(models.Unidade).filter_by(id=unidade_id).first()
    if not unidade:
        raise RecursoNaoEncontrado(f"Unidade {unidade_id} nao encontrada.")
    if not unidade.ativo:
        raise ConflitoDeNegocio(
            f"Unidade {unidade_id} esta inativa e nao recebe pedidos.",
            details=[{"field": "unidade_id", "issue": "inativa"}],
        )
    return unidade


def _carregar_itens(
    db: Session, unidade_id: int, itens_payload: list
) -> list[tuple[int, int, Decimal]]:
    """
    Pra cada item: confere se o produto existe, se ta ativo, se ta no
    cardapio dessa unidade e se ta disponivel. Devolve uma lista de
    tuplas (produto_id, quantidade, preco_unitario) ja calculado.
    """
    resultado = []
    for it in itens_payload:
        produto = db.query(models.Produto).filter_by(id=it.produto_id).first()
        if not produto:
            raise RecursoNaoEncontrado(f"Produto {it.produto_id} nao encontrado.")
        if not produto.ativo:
            raise ConflitoDeNegocio(
                f"Produto '{produto.nome}' esta inativo.",
                details=[{"field": "itens.produto_id", "issue": "produto inativo"}],
            )

        cardapio = (
            db.query(models.CardapioUnidade)
            .filter_by(unidade_id=unidade_id, produto_id=it.produto_id)
            .first()
        )
        if not cardapio:
            raise ConflitoDeNegocio(
                f"Produto '{produto.nome}' nao esta no cardapio dessa unidade.",
                details=[{"field": "itens.produto_id", "issue": "fora do cardapio"}],
            )
        if not cardapio.disponivel:
            raise ConflitoDeNegocio(
                f"Produto '{produto.nome}' indisponivel nesta unidade.",
                details=[{"field": "itens.produto_id", "issue": "indisponivel"}],
            )

        # se a unidade tem preco local, usa esse, senao o preco base do produto
        preco = (
            cardapio.preco_local
            if cardapio.preco_local is not None
            else produto.preco_base
        )
        resultado.append((it.produto_id, it.quantidade, Decimal(preco)))
    return resultado


def _aplicar_promocao(
    db: Session, codigo: str, subtotal: Decimal
) -> tuple[Optional[int], Decimal]:
    """Verifica o codigo de promocao e devolve (id, valor_desconto)."""
    codigo_upper = codigo.strip().upper()
    promocao = db.query(models.Promocao).filter_by(codigo=codigo_upper).first()
    if not promocao or not promocao.ativo:
        raise ConflitoDeNegocio(
            f"Promocao '{codigo}' nao encontrada ou inativa.",
            details=[{"field": "codigo_promocao", "issue": "invalida"}],
        )
    desconto = aplicar_desconto(
        subtotal,
        percentual=promocao.percentual_desconto,
        valor_fixo=promocao.valor_desconto,
    )
    return promocao.id, desconto


def criar_pedido(
    db: Session, dados: PedidoCreate, usuario: models.Usuario
) -> models.Pedido:
    """Cria o pedido inteiro: valida, calcula totais e salva."""
    cliente = _resolver_cliente(db, dados, usuario)
    _validar_unidade(db, dados.unidade_id)

    itens_calc = _carregar_itens(db, dados.unidade_id, dados.itens)

    # checa estoque (otimista, nao baixa nada aqui)
    estoque_service.validar_disponibilidade(
        db,
        dados.unidade_id,
        [(produto_id, qtd) for (produto_id, qtd, _) in itens_calc],
    )

    subtotal = calcular_subtotal([(preco, qtd) for (_, qtd, preco) in itens_calc])

    promocao_id: Optional[int] = None
    desconto = Decimal("0.00")
    if dados.codigo_promocao:
        promocao_id, desconto = _aplicar_promocao(db, dados.codigo_promocao, subtotal)

    desconto_resgate = Decimal("0.00")
    pontos_a_resgatar = dados.pontos_resgate or 0
    if pontos_a_resgatar > 0:
        desconto_resgate = fidelidade_service.calcular_desconto_se_houver(
            cliente, pontos_a_resgatar
        )

    desconto_total = (desconto + desconto_resgate).quantize(Decimal("0.01"))
    if desconto_total > subtotal:
        # desconto nao pode passar do subtotal, senao da total negativo
        desconto_total = subtotal

    total = (subtotal - desconto_total).quantize(Decimal("0.01"))

    pedido = models.Pedido(
        cliente_id=cliente.id,
        unidade_id=dados.unidade_id,
        canal_pedido=dados.canal_pedido,
        status=StatusPedido.AGUARDANDO_PAGAMENTO,
        metodo_pagamento=dados.metodo_pagamento,
        subtotal=subtotal,
        desconto=desconto_total,
        total=total,
        pontos_resgatados=pontos_a_resgatar,
        pontos_creditados=0,
        promocao_id=promocao_id,
        observacoes=dados.observacoes.strip() if dados.observacoes else None,
    )
    db.add(pedido)
    db.flush()  # pra ja ter o id pros itens e pra movimentacao de pontos

    # se o cara resgatou pontos, debita agora (com pedido.id em maos)
    if pontos_a_resgatar > 0:
        fidelidade_service.aplicar_resgate(db, cliente, pontos_a_resgatar, pedido.id)

    for produto_id, qtd, preco in itens_calc:
        subtotal_item = (preco * qtd).quantize(Decimal("0.01"))
        item = models.ItemPedido(
            pedido_id=pedido.id,
            produto_id=produto_id,
            quantidade=qtd,
            preco_unitario=preco,
            subtotal_item=subtotal_item,
        )
        db.add(item)

    registrar_log(
        db,
        acao="PEDIDO_CRIADO",
        usuario_id=usuario.id,
        recurso="PEDIDO",
        recurso_id=pedido.id,
        dados={
            "cliente_id": cliente.id,
            "unidade_id": pedido.unidade_id,
            "canal_pedido": pedido.canal_pedido.value,
            "total": str(pedido.total),
            "qtd_itens": len(itens_calc),
            "promocao_id": promocao_id,
            "pontos_resgatados": pontos_a_resgatar,
        },
    )

    db.commit()
    db.refresh(pedido)
    return pedido


# ---------------------------------------------------------
# listagem e consulta
# ---------------------------------------------------------

def listar_pedidos(
    db: Session,
    usuario: models.Usuario,
    page: int = 1,
    limit: int = 20,
    canal_pedido: Optional[CanalPedido] = None,
    status_filtro: Optional[StatusPedido] = None,
    cliente_id: Optional[int] = None,
    unidade_id: Optional[int] = None,
) -> tuple[list[models.Pedido], int]:
    """Lista pedidos. Cliente so ve os proprios."""
    query = db.query(models.Pedido)

    if usuario.perfil == PerfilUsuario.CLIENTE:
        # forca o filtro pra evitar que o cliente passe outro id
        query = query.filter(models.Pedido.cliente_id == usuario.id)
    elif cliente_id is not None:
        query = query.filter(models.Pedido.cliente_id == cliente_id)

    if canal_pedido:
        query = query.filter(models.Pedido.canal_pedido == canal_pedido)
    if status_filtro:
        query = query.filter(models.Pedido.status == status_filtro)
    if unidade_id is not None:
        query = query.filter(models.Pedido.unidade_id == unidade_id)

    total = query.count()
    items = (
        query.order_by(models.Pedido.criado_em.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return items, total


def buscar_pedido(
    db: Session, pedido_id: int, usuario: models.Usuario
) -> models.Pedido:
    """Busca um pedido. Cliente so ve os proprios."""
    pedido = db.query(models.Pedido).filter_by(id=pedido_id).first()
    if not pedido:
        raise RecursoNaoEncontrado(f"Pedido {pedido_id} nao encontrado.")

    if usuario.perfil == PerfilUsuario.CLIENTE and pedido.cliente_id != usuario.id:
        # devolvo 404 ao inves de 403 pra nao revelar que o pedido existe
        raise RecursoNaoEncontrado(f"Pedido {pedido_id} nao encontrado.")
    return pedido


# ---------------------------------------------------------
# mudanca de status
# ---------------------------------------------------------

def _baixar_estoque_do_pedido(
    db: Session, pedido: models.Pedido, responsavel_id: int
) -> None:
    """Baixa SAIDA pra cada item do pedido. Sem commit (quem chama commita)."""
    for item in pedido.itens:
        estoque_service.aplicar_movimentacao(
            db,
            unidade_id=pedido.unidade_id,
            produto_id=item.produto_id,
            tipo=TipoMovimentacaoEstoque.SAIDA,
            quantidade=item.quantidade,
            motivo=f"Venda do pedido {pedido.id}",
            responsavel_id=responsavel_id,
            pedido_id=pedido.id,
            commit=False,
        )


def _estornar_estoque_do_pedido(
    db: Session, pedido: models.Pedido, responsavel_id: int
) -> None:
    """ENTRADA pra cada item, no caso de cancelamento depois de pago."""
    for item in pedido.itens:
        estoque_service.aplicar_movimentacao(
            db,
            unidade_id=pedido.unidade_id,
            produto_id=item.produto_id,
            tipo=TipoMovimentacaoEstoque.ENTRADA,
            quantidade=item.quantidade,
            motivo=f"Estorno do pedido {pedido.id} (cancelado)",
            responsavel_id=responsavel_id,
            pedido_id=pedido.id,
            commit=False,
        )


# status em que o estoque ja foi baixado e precisa ser estornado se cancelar
_STATUS_COM_BAIXA_DE_ESTOQUE = {
    StatusPedido.PAGO,
    StatusPedido.EM_PREPARO,
    StatusPedido.PRONTO,
}


def _executar_mudanca_status(
    db: Session,
    pedido: models.Pedido,
    novo_status: StatusPedido,
    responsavel_id: int,
) -> models.Pedido:
    """
    Executa a transicao de status (sem checar permissao do usuario,
    isso eh papel de quem chamou). Aplica regra de transicao do dominio
    e dispara as acoes laterais (estoque, fidelidade, log).
    """
    status_anterior = pedido.status
    validar_transicao(status_anterior, novo_status)

    if novo_status == StatusPedido.PAGO and status_anterior != StatusPedido.PAGO:
        _baixar_estoque_do_pedido(db, pedido, responsavel_id=responsavel_id)
        # credita pontos (so credita se o cliente tiver consentimento)
        pontos_creditados = fidelidade_service.creditar_por_pagamento(
            db,
            cliente_id=pedido.cliente_id,
            pedido_id=pedido.id,
            total_pedido=pedido.total,
            commit=False,
        )
        pedido.pontos_creditados = pontos_creditados
    elif novo_status == StatusPedido.CANCELADO:
        if status_anterior in _STATUS_COM_BAIXA_DE_ESTOQUE:
            _estornar_estoque_do_pedido(db, pedido, responsavel_id=responsavel_id)
        # pontos sempre estornam no cancelamento (resgatados voltam, creditados saem)
        fidelidade_service.estornar_pedido(db, pedido, commit=False)

    pedido.status = novo_status

    registrar_log(
        db,
        acao="PEDIDO_STATUS_ALTERADO",
        usuario_id=responsavel_id,
        recurso="PEDIDO",
        recurso_id=pedido.id,
        dados={
            "status_anterior": status_anterior.value,
            "novo_status": novo_status.value,
        },
    )

    db.commit()
    db.refresh(pedido)
    return pedido


def mudar_status(
    db: Session,
    pedido_id: int,
    novo_status: StatusPedido,
    usuario: models.Usuario,
) -> models.Pedido:
    """Muda status acionado direto pela API (PATCH). Checa permissao."""
    pedido = db.query(models.Pedido).filter_by(id=pedido_id).first()
    if not pedido:
        raise RecursoNaoEncontrado(f"Pedido {pedido_id} nao encontrado.")

    # cliente so cancela proprio pedido
    if usuario.perfil == PerfilUsuario.CLIENTE:
        if pedido.cliente_id != usuario.id:
            raise RecursoNaoEncontrado(f"Pedido {pedido_id} nao encontrado.")
        if novo_status != StatusPedido.CANCELADO:
            raise SemPermissao("Cliente so pode cancelar o proprio pedido.")

    return _executar_mudanca_status(db, pedido, novo_status, responsavel_id=usuario.id)


def mudar_status_sistema(
    db: Session,
    pedido_id: int,
    novo_status: StatusPedido,
    responsavel_id: int,
) -> models.Pedido:
    """
    Versao "interna" do mudar_status, usada por outros services
    (ex: pagamento). Nao checa permissao porque a transicao foi
    consequencia de outra operacao do sistema.
    """
    pedido = db.query(models.Pedido).filter_by(id=pedido_id).first()
    if not pedido:
        raise RecursoNaoEncontrado(f"Pedido {pedido_id} nao encontrado.")
    return _executar_mudanca_status(db, pedido, novo_status, responsavel_id=responsavel_id)


def cancelar_pedido(
    db: Session, pedido_id: int, usuario: models.Usuario
) -> models.Pedido:
    """Atalho pra mudar_status(..., CANCELADO)."""
    return mudar_status(db, pedido_id, StatusPedido.CANCELADO, usuario)
