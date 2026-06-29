"""
Casos de uso do recurso Produto.

CRUD com soft-delete (`ativo`). Aceita filtro por categoria e busca
por nome (parcial, case-insensitive) na listagem.
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.api.schemas.produto import ProdutoCreate, ProdutoUpdate
from app.domain.entities.enums import CategoriaProduto
from app.domain.exceptions import ConflitoDeNegocio, RecursoNaoEncontrado
from app.infrastructure.database import models


def listar(
    db: Session,
    page: int = 1,
    limit: int = 10,
    categoria: Optional[CategoriaProduto] = None,
    busca: Optional[str] = None,
    somente_ativos: bool = False,
) -> tuple[list[models.Produto], int]:
    query = db.query(models.Produto)

    if categoria:
        query = query.filter(models.Produto.categoria == categoria)
    if busca:
        # ilike eh portavel entre SQLite e Postgres pra busca case-insensitive
        query = query.filter(models.Produto.nome.ilike(f"%{busca.strip()}%"))
    if somente_ativos:
        query = query.filter(models.Produto.ativo.is_(True))

    total = query.count()
    items = (
        query.order_by(models.Produto.nome)
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return items, total


def buscar(db: Session, produto_id: int) -> models.Produto:
    produto = db.query(models.Produto).filter_by(id=produto_id).first()
    if not produto:
        raise RecursoNaoEncontrado(f"Produto {produto_id} nao encontrado.")
    return produto


def criar(db: Session, dados: ProdutoCreate) -> models.Produto:
    nome = dados.nome.strip()
    if db.query(models.Produto).filter_by(nome=nome).first():
        raise ConflitoDeNegocio(
            "Ja existe um produto com esse nome.",
            details=[{"field": "nome", "issue": "ja cadastrado"}],
        )

    produto = models.Produto(
        nome=nome,
        descricao=dados.descricao.strip() if dados.descricao else None,
        preco_base=dados.preco_base,
        categoria=dados.categoria,
        sazonal=dados.sazonal,
        ativo=True,
    )
    db.add(produto)
    db.commit()
    db.refresh(produto)
    return produto


def atualizar(db: Session, produto_id: int, dados: ProdutoUpdate) -> models.Produto:
    produto = buscar(db, produto_id)
    payload = dados.model_dump(exclude_unset=True)
    for campo, valor in payload.items():
        if isinstance(valor, str):
            valor = valor.strip()
        setattr(produto, campo, valor)

    db.commit()
    db.refresh(produto)
    return produto


def desativar(db: Session, produto_id: int) -> None:
    """Soft delete pra preservar historico em pedidos antigos."""
    produto = buscar(db, produto_id)
    produto.ativo = False
    db.commit()
