"""
Casos de uso do recurso Unidade.

CRUD basico com soft-delete (campo `ativo`). Quem chama eh o router,
que delega aqui a logica de banco e validacoes simples.
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.api.schemas.unidade import UnidadeCreate, UnidadeUpdate
from app.domain.exceptions import ConflitoDeNegocio, RecursoNaoEncontrado
from app.infrastructure.database import models


def listar(
    db: Session,
    page: int = 1,
    limit: int = 10,
    somente_ativas: bool = False,
) -> tuple[list[models.Unidade], int]:
    """
    Devolve (items, total) ja paginado. O total eh o numero de registros
    no filtro inteiro, nao so na pagina, pra a UI conseguir mostrar
    "X de Y".
    """
    query = db.query(models.Unidade)
    if somente_ativas:
        query = query.filter(models.Unidade.ativo.is_(True))

    total = query.count()
    items = (
        query.order_by(models.Unidade.id)
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return items, total


def buscar(db: Session, unidade_id: int) -> models.Unidade:
    unidade = db.query(models.Unidade).filter_by(id=unidade_id).first()
    if not unidade:
        raise RecursoNaoEncontrado(f"Unidade {unidade_id} nao encontrada.")
    return unidade


def criar(db: Session, dados: UnidadeCreate) -> models.Unidade:
    # checa duplicidade pelo nome (regra simples pra evitar copia)
    existente = db.query(models.Unidade).filter_by(nome=dados.nome.strip()).first()
    if existente:
        raise ConflitoDeNegocio(
            "Ja existe uma unidade com esse nome.",
            details=[{"field": "nome", "issue": "ja cadastrado"}],
        )

    unidade = models.Unidade(
        nome=dados.nome.strip(),
        cidade=dados.cidade.strip(),
        estado=dados.estado.strip().upper(),
        endereco=dados.endereco.strip() if dados.endereco else None,
        ativo=True,
    )
    db.add(unidade)
    db.commit()
    db.refresh(unidade)
    return unidade


def atualizar(db: Session, unidade_id: int, dados: UnidadeUpdate) -> models.Unidade:
    unidade = buscar(db, unidade_id)

    # so atualiza os campos que vieram (atualizacao parcial)
    payload = dados.model_dump(exclude_unset=True)
    for campo, valor in payload.items():
        if isinstance(valor, str):
            valor = valor.strip()
            if campo == "estado":
                valor = valor.upper()
        setattr(unidade, campo, valor)

    db.commit()
    db.refresh(unidade)
    return unidade


def desativar(db: Session, unidade_id: int) -> None:
    """Soft delete: marca como inativa em vez de remover do banco."""
    unidade = buscar(db, unidade_id)
    unidade.ativo = False
    db.commit()
