"""
Casos de uso do recurso Cardapio (sub-recurso de Unidade).

Cardapio eh a tabela de associacao entre produto e unidade que define
disponibilidade e preco local. Aqui ficam as operacoes de listagem
publica e gestao por GERENTE/ADMIN.
"""
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.api.schemas.cardapio import CardapioCreate, CardapioItemResponse, CardapioUpdate
from app.domain.exceptions import ConflitoDeNegocio, RecursoNaoEncontrado
from app.infrastructure.database import models


def _achar_unidade(db: Session, unidade_id: int) -> models.Unidade:
    unidade = db.query(models.Unidade).filter_by(id=unidade_id).first()
    if not unidade:
        raise RecursoNaoEncontrado(f"Unidade {unidade_id} nao encontrada.")
    return unidade


def _achar_produto(db: Session, produto_id: int) -> models.Produto:
    produto = db.query(models.Produto).filter_by(id=produto_id).first()
    if not produto:
        raise RecursoNaoEncontrado(f"Produto {produto_id} nao encontrado.")
    return produto


def listar_cardapio(
    db: Session,
    unidade_id: int,
    somente_disponiveis: bool = False,
) -> list[CardapioItemResponse]:
    """
    Devolve o cardapio "renderizado" pra exibir ao cliente, ja
    misturando os dados do produto com a info da unidade.
    """
    _achar_unidade(db, unidade_id)

    query = (
        db.query(models.CardapioUnidade, models.Produto)
        .join(models.Produto, models.Produto.id == models.CardapioUnidade.produto_id)
        .filter(models.CardapioUnidade.unidade_id == unidade_id)
        .filter(models.Produto.ativo.is_(True))
    )
    if somente_disponiveis:
        query = query.filter(models.CardapioUnidade.disponivel.is_(True))

    resultado = []
    for cardapio, produto in query.order_by(models.Produto.nome).all():
        preco = cardapio.preco_local if cardapio.preco_local is not None else produto.preco_base
        resultado.append(
            CardapioItemResponse(
                produto_id=produto.id,
                nome=produto.nome,
                descricao=produto.descricao,
                categoria=produto.categoria,
                preco=preco,
                preco_base=produto.preco_base,
                preco_local=cardapio.preco_local,
                disponivel=cardapio.disponivel,
                sazonal=produto.sazonal,
            )
        )
    return resultado


def adicionar_ao_cardapio(
    db: Session,
    unidade_id: int,
    dados: CardapioCreate,
) -> models.CardapioUnidade:
    """Vincula um produto a uma unidade. Falha se ja existir o vinculo."""
    _achar_unidade(db, unidade_id)
    _achar_produto(db, dados.produto_id)

    existente = (
        db.query(models.CardapioUnidade)
        .filter_by(unidade_id=unidade_id, produto_id=dados.produto_id)
        .first()
    )
    if existente:
        raise ConflitoDeNegocio(
            "Esse produto ja esta no cardapio dessa unidade.",
            details=[{"field": "produto_id", "issue": "ja vinculado"}],
        )

    item = models.CardapioUnidade(
        unidade_id=unidade_id,
        produto_id=dados.produto_id,
        preco_local=dados.preco_local,
        disponivel=dados.disponivel,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def atualizar_item_cardapio(
    db: Session,
    unidade_id: int,
    produto_id: int,
    dados: CardapioUpdate,
) -> models.CardapioUnidade:
    item = (
        db.query(models.CardapioUnidade)
        .filter_by(unidade_id=unidade_id, produto_id=produto_id)
        .first()
    )
    if not item:
        raise RecursoNaoEncontrado(
            f"Produto {produto_id} nao esta no cardapio da unidade {unidade_id}."
        )

    payload = dados.model_dump(exclude_unset=True)
    for campo, valor in payload.items():
        setattr(item, campo, valor)

    db.commit()
    db.refresh(item)
    return item


def remover_do_cardapio(db: Session, unidade_id: int, produto_id: int) -> None:
    """Hard delete: tira o vinculo. Nao afeta o produto em si."""
    item = (
        db.query(models.CardapioUnidade)
        .filter_by(unidade_id=unidade_id, produto_id=produto_id)
        .first()
    )
    if not item:
        raise RecursoNaoEncontrado(
            f"Produto {produto_id} nao esta no cardapio da unidade {unidade_id}."
        )
    db.delete(item)
    db.commit()
