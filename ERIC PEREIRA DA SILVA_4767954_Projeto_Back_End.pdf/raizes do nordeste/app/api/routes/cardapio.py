"""
Rotas do recurso Cardapio (sub-recurso de /unidades).

URLs:
- GET    /unidades/{unidade_id}/cardapio
- POST   /unidades/{unidade_id}/cardapio
- PUT    /unidades/{unidade_id}/cardapio/{produto_id}
- DELETE /unidades/{unidade_id}/cardapio/{produto_id}

Permissoes: leitura aberta a qualquer autenticado; alteracoes restritas
a ADMIN e GERENTE.
"""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import exigir_perfis, get_usuario_atual
from app.api.schemas.cardapio import CardapioCreate, CardapioItemResponse, CardapioUpdate
from app.application.services import cardapio_service
from app.domain.entities.enums import PerfilUsuario
from app.infrastructure.database.connection import get_db


router = APIRouter(prefix="/unidades/{unidade_id}/cardapio", tags=["Cardapio"])

PERFIS_GESTAO = [PerfilUsuario.ADMIN, PerfilUsuario.GERENTE]


@router.get(
    "",
    response_model=list[CardapioItemResponse],
    summary="Lista o cardapio de uma unidade",
    dependencies=[Depends(get_usuario_atual)],
)
def listar(
    unidade_id: int,
    somente_disponiveis: bool = Query(False),
    db: Session = Depends(get_db),
):
    return cardapio_service.listar_cardapio(db, unidade_id, somente_disponiveis)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Adiciona um produto ao cardapio da unidade",
    dependencies=[Depends(exigir_perfis(*PERFIS_GESTAO))],
)
def adicionar(unidade_id: int, dados: CardapioCreate, db: Session = Depends(get_db)):
    item = cardapio_service.adicionar_ao_cardapio(db, unidade_id, dados)
    return {
        "unidade_id": item.unidade_id,
        "produto_id": item.produto_id,
        "preco_local": item.preco_local,
        "disponivel": item.disponivel,
    }


@router.put(
    "/{produto_id}",
    summary="Atualiza disponibilidade ou preco local de um item do cardapio",
    dependencies=[Depends(exigir_perfis(*PERFIS_GESTAO))],
)
def atualizar(
    unidade_id: int,
    produto_id: int,
    dados: CardapioUpdate,
    db: Session = Depends(get_db),
):
    item = cardapio_service.atualizar_item_cardapio(db, unidade_id, produto_id, dados)
    return {
        "unidade_id": item.unidade_id,
        "produto_id": item.produto_id,
        "preco_local": item.preco_local,
        "disponivel": item.disponivel,
    }


@router.delete(
    "/{produto_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove um produto do cardapio da unidade",
    dependencies=[Depends(exigir_perfis(*PERFIS_GESTAO))],
)
def remover(unidade_id: int, produto_id: int, db: Session = Depends(get_db)):
    cardapio_service.remover_do_cardapio(db, unidade_id, produto_id)
    return None
