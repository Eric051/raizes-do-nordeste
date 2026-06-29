"""
Rotas do recurso /unidades.

Permissoes:
- GET sao acessiveis a qualquer usuario autenticado.
- POST, PUT e DELETE sao restritos a ADMIN e GERENTE.
"""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import exigir_perfis, get_usuario_atual
from app.api.schemas.comuns import PageMeta
from app.api.schemas.unidade import (
    UnidadeCreate,
    UnidadeListResponse,
    UnidadeResponse,
    UnidadeUpdate,
)
from app.application.services import unidade_service
from app.domain.entities.enums import PerfilUsuario
from app.infrastructure.database.connection import get_db


router = APIRouter(prefix="/unidades", tags=["Unidades"])

# perfis com permissao de escrita
PERFIS_GESTAO = [PerfilUsuario.ADMIN, PerfilUsuario.GERENTE]


@router.get(
    "",
    response_model=UnidadeListResponse,
    summary="Lista unidades da rede",
    dependencies=[Depends(get_usuario_atual)],
)
def listar(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    somente_ativas: bool = Query(False),
    db: Session = Depends(get_db),
):
    items, total = unidade_service.listar(
        db, page=page, limit=limit, somente_ativas=somente_ativas
    )
    return UnidadeListResponse(
        items=[UnidadeResponse.model_validate(u) for u in items],
        meta=PageMeta.calcular(page, limit, total),
    )


@router.post(
    "",
    response_model=UnidadeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra uma nova unidade",
    dependencies=[Depends(exigir_perfis(*PERFIS_GESTAO))],
)
def criar(dados: UnidadeCreate, db: Session = Depends(get_db)):
    unidade = unidade_service.criar(db, dados)
    return UnidadeResponse.model_validate(unidade)


@router.get(
    "/{unidade_id}",
    response_model=UnidadeResponse,
    summary="Detalhes de uma unidade",
    dependencies=[Depends(get_usuario_atual)],
)
def detalhes(unidade_id: int, db: Session = Depends(get_db)):
    return UnidadeResponse.model_validate(unidade_service.buscar(db, unidade_id))


@router.put(
    "/{unidade_id}",
    response_model=UnidadeResponse,
    summary="Atualiza uma unidade",
    dependencies=[Depends(exigir_perfis(*PERFIS_GESTAO))],
)
def atualizar(unidade_id: int, dados: UnidadeUpdate, db: Session = Depends(get_db)):
    return UnidadeResponse.model_validate(unidade_service.atualizar(db, unidade_id, dados))


@router.delete(
    "/{unidade_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Desativa uma unidade (soft delete)",
    dependencies=[Depends(exigir_perfis(PerfilUsuario.ADMIN))],
)
def desativar(unidade_id: int, db: Session = Depends(get_db)):
    unidade_service.desativar(db, unidade_id)
    return None
