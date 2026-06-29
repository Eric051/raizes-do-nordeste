"""
Rotas do recurso /produtos.

Permissoes:
- GET sao acessiveis a qualquer usuario autenticado.
- POST/PUT/DELETE sao restritos a ADMIN e GERENTE.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import exigir_perfis, get_usuario_atual
from app.api.schemas.comuns import PageMeta
from app.api.schemas.produto import (
    ProdutoCreate,
    ProdutoListResponse,
    ProdutoResponse,
    ProdutoUpdate,
)
from app.application.services import produto_service
from app.domain.entities.enums import CategoriaProduto, PerfilUsuario
from app.infrastructure.database.connection import get_db


router = APIRouter(prefix="/produtos", tags=["Produtos"])

PERFIS_GESTAO = [PerfilUsuario.ADMIN, PerfilUsuario.GERENTE]


@router.get(
    "",
    response_model=ProdutoListResponse,
    summary="Lista produtos do catalogo",
    dependencies=[Depends(get_usuario_atual)],
)
def listar(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    categoria: Optional[CategoriaProduto] = Query(None),
    busca: Optional[str] = Query(None, description="Busca parcial pelo nome (case-insensitive)"),
    somente_ativos: bool = Query(False),
    db: Session = Depends(get_db),
):
    items, total = produto_service.listar(
        db,
        page=page,
        limit=limit,
        categoria=categoria,
        busca=busca,
        somente_ativos=somente_ativos,
    )
    return ProdutoListResponse(
        items=[ProdutoResponse.model_validate(p) for p in items],
        meta=PageMeta.calcular(page, limit, total),
    )


@router.post(
    "",
    response_model=ProdutoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra um produto no catalogo",
    dependencies=[Depends(exigir_perfis(*PERFIS_GESTAO))],
)
def criar(dados: ProdutoCreate, db: Session = Depends(get_db)):
    return ProdutoResponse.model_validate(produto_service.criar(db, dados))


@router.get(
    "/{produto_id}",
    response_model=ProdutoResponse,
    summary="Detalhes de um produto",
    dependencies=[Depends(get_usuario_atual)],
)
def detalhes(produto_id: int, db: Session = Depends(get_db)):
    return ProdutoResponse.model_validate(produto_service.buscar(db, produto_id))


@router.put(
    "/{produto_id}",
    response_model=ProdutoResponse,
    summary="Atualiza um produto",
    dependencies=[Depends(exigir_perfis(*PERFIS_GESTAO))],
)
def atualizar(produto_id: int, dados: ProdutoUpdate, db: Session = Depends(get_db)):
    return ProdutoResponse.model_validate(produto_service.atualizar(db, produto_id, dados))


@router.delete(
    "/{produto_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Desativa um produto (soft delete)",
    dependencies=[Depends(exigir_perfis(*PERFIS_GESTAO))],
)
def desativar(produto_id: int, db: Session = Depends(get_db)):
    produto_service.desativar(db, produto_id)
    return None
