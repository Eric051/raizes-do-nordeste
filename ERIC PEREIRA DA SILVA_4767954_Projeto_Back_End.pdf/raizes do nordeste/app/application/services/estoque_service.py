"""
Casos de uso do recurso Estoque.

A funcao `aplicar_movimentacao` eh o coracao do modulo: toda alteracao
de saldo (manual ou automatica via pedido) passa por ela. Isso garante
que o saldo do estoque e o historico de movimentacoes ficam sempre
consistentes.

A funcao `validar_disponibilidade` eh usada pelo service de pedido
pra checar se da pra criar o pedido antes de mexer no banco.

Movimentacoes manuais (via API) tambem geram log de auditoria.
Movimentacoes automaticas (saida por venda, estorno por cancelamento)
nao geram log de auditoria porque ja ficam registradas em
movimentacoes_estoque com referencia ao pedido.
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.api.schemas.estoque import (
    MovimentacaoEstoqueCreate,
    SaldoEstoqueResponse,
)
from app.domain.entities.enums import TipoMovimentacaoEstoque
from app.domain.exceptions import (
    DadosInvalidos,
    EstoqueInsuficiente,
    RecursoNaoEncontrado,
)
from app.infrastructure.audit.audit_logger import registrar_log
from app.infrastructure.database import models


# ----------------------------------------------------------------------
# Consultas
# ----------------------------------------------------------------------

def listar_saldos_da_unidade(
    db: Session,
    unidade_id: int,
    page: int = 1,
    limit: int = 50,
) -> tuple[list[SaldoEstoqueResponse], int]:
    """
    Lista os saldos de estoque de uma unidade, paginado.
    Cada linha vem ja com o nome do produto pra facilitar a UI.
    """
    if not db.query(models.Unidade).filter_by(id=unidade_id).first():
        raise RecursoNaoEncontrado(f"Unidade {unidade_id} nao encontrada.")

    base = (
        db.query(models.Estoque, models.Produto)
        .join(models.Produto, models.Produto.id == models.Estoque.produto_id)
        .filter(models.Estoque.unidade_id == unidade_id)
        .order_by(models.Produto.nome)
    )
    total = base.count()
    rows = base.offset((page - 1) * limit).limit(limit).all()

    items = [
        SaldoEstoqueResponse(
            unidade_id=estoque.unidade_id,
            produto_id=estoque.produto_id,
            nome_produto=produto.nome,
            quantidade=estoque.quantidade,
            atualizado_em=estoque.atualizado_em,
        )
        for estoque, produto in rows
    ]
    return items, total


def listar_movimentacoes(
    db: Session,
    unidade_id: int,
    produto_id: Optional[int] = None,
    page: int = 1,
    limit: int = 50,
) -> tuple[list[models.MovimentacaoEstoque], int]:
    """Devolve o historico de movimentacoes de uma unidade, opcionalmente filtrado por produto."""
    if not db.query(models.Unidade).filter_by(id=unidade_id).first():
        raise RecursoNaoEncontrado(f"Unidade {unidade_id} nao encontrada.")

    query = (
        db.query(models.MovimentacaoEstoque)
        .join(models.Estoque, models.Estoque.id == models.MovimentacaoEstoque.estoque_id)
        .filter(models.Estoque.unidade_id == unidade_id)
    )
    if produto_id is not None:
        query = query.filter(models.Estoque.produto_id == produto_id)

    total = query.count()
    items = (
        query.order_by(models.MovimentacaoEstoque.criado_em.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return items, total


# ----------------------------------------------------------------------
# Movimentacao (entrada / saida / ajuste)
# ----------------------------------------------------------------------

def _achar_ou_criar_estoque(
    db: Session, unidade_id: int, produto_id: int
) -> models.Estoque:
    """
    Retorna o registro de estoque pra (unidade, produto), criando com
    saldo 0 se ainda nao existir. Valida que unidade e produto existem.
    """
    estoque = (
        db.query(models.Estoque)
        .filter_by(unidade_id=unidade_id, produto_id=produto_id)
        .first()
    )
    if estoque:
        return estoque

    if not db.query(models.Unidade).filter_by(id=unidade_id).first():
        raise RecursoNaoEncontrado(f"Unidade {unidade_id} nao encontrada.")
    if not db.query(models.Produto).filter_by(id=produto_id).first():
        raise RecursoNaoEncontrado(f"Produto {produto_id} nao encontrado.")

    estoque = models.Estoque(unidade_id=unidade_id, produto_id=produto_id, quantidade=0)
    db.add(estoque)
    db.flush()
    return estoque


def aplicar_movimentacao(
    db: Session,
    unidade_id: int,
    produto_id: int,
    tipo: TipoMovimentacaoEstoque,
    quantidade: int,
    motivo: Optional[str] = None,
    responsavel_id: Optional[int] = None,
    pedido_id: Optional[int] = None,
    commit: bool = True,
) -> models.Estoque:
    """
    Aplica uma movimentacao no estoque. Atualiza o saldo e cria o
    registro historico em MovimentacaoEstoque.

    Comportamento por tipo:
    - ENTRADA: soma `quantidade` ao saldo atual
    - SAIDA:   subtrai `quantidade`; se nao houver saldo, levanta
               EstoqueInsuficiente (status 409)
    - AJUSTE:  define o saldo final como `quantidade` (sobrescreve)

    O parametro `commit` permite que essa funcao seja chamada de dentro
    de uma transacao maior (criar pedido baixa varios itens no mesmo
    commit), evitando partial updates.
    """
    if quantidade <= 0:
        raise DadosInvalidos(
            "A quantidade deve ser maior que zero.",
            details=[{"field": "quantidade", "issue": "deve ser positivo"}],
        )

    estoque = _achar_ou_criar_estoque(db, unidade_id, produto_id)
    saldo_anterior = estoque.quantidade

    if tipo == TipoMovimentacaoEstoque.ENTRADA:
        novo_saldo = saldo_anterior + quantidade
    elif tipo == TipoMovimentacaoEstoque.SAIDA:
        if saldo_anterior < quantidade:
            raise EstoqueInsuficiente(
                f"Estoque insuficiente para o produto {produto_id} na unidade {unidade_id}.",
                details=[{
                    "field": "quantidade",
                    "issue": f"solicitado {quantidade}, disponivel {saldo_anterior}",
                }],
            )
        novo_saldo = saldo_anterior - quantidade
    elif tipo == TipoMovimentacaoEstoque.AJUSTE:
        novo_saldo = quantidade
    else:  # pragma: no cover
        raise DadosInvalidos(f"Tipo de movimentacao invalido: {tipo}")

    estoque.quantidade = novo_saldo

    movimentacao = models.MovimentacaoEstoque(
        estoque_id=estoque.id,
        tipo=tipo,
        quantidade=quantidade,
        motivo=motivo,
        responsavel_id=responsavel_id,
        pedido_id=pedido_id,
    )
    db.add(movimentacao)

    if commit:
        db.commit()
        db.refresh(estoque)
    else:
        db.flush()

    return estoque


def criar_movimentacao(
    db: Session,
    unidade_id: int,
    dados: MovimentacaoEstoqueCreate,
    responsavel_id: int,
) -> models.Estoque:
    """Wrapper pra movimentacoes feitas via API por um usuario logado.
    Alem de aplicar a movimentacao, registra log de auditoria."""
    estoque = aplicar_movimentacao(
        db,
        unidade_id=unidade_id,
        produto_id=dados.produto_id,
        tipo=dados.tipo,
        quantidade=dados.quantidade,
        motivo=dados.motivo,
        responsavel_id=responsavel_id,
        commit=False,  # vamos commitar junto com o log
    )
    # auditoria: movimentacao manual eh acao sensivel
    registrar_log(
        db,
        acao="ESTOQUE_MOVIMENTADO",
        usuario_id=responsavel_id,
        recurso="ESTOQUE",
        recurso_id=estoque.id,
        dados={
            "unidade_id": unidade_id,
            "produto_id": dados.produto_id,
            "tipo": dados.tipo.value,
            "quantidade": dados.quantidade,
            "motivo": dados.motivo,
            "saldo_apos": estoque.quantidade,
        },
        commit=True,
    )
    db.refresh(estoque)
    return estoque


# ----------------------------------------------------------------------
# Validacao usada pelo service de pedido
# ----------------------------------------------------------------------

def validar_disponibilidade(
    db: Session,
    unidade_id: int,
    itens: list[tuple[int, int]],
) -> None:
    """
    Recebe uma lista de tuplas (produto_id, quantidade) e levanta
    EstoqueInsuficiente se algum item nao puder ser atendido.
    """
    insuficientes = []
    for idx, (produto_id, qtd) in enumerate(itens):
        estoque = (
            db.query(models.Estoque)
            .filter_by(unidade_id=unidade_id, produto_id=produto_id)
            .first()
        )
        saldo = estoque.quantidade if estoque else 0
        if saldo < qtd:
            insuficientes.append({
                "field": f"itens[{idx}].quantidade",
                "issue": (
                    f"produto {produto_id}: solicitado {qtd}, "
                    f"disponivel {saldo}"
                ),
            })

    if insuficientes:
        raise EstoqueInsuficiente(
            "Estoque insuficiente para um ou mais itens.",
            details=insuficientes,
        )
